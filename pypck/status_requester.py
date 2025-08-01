"""Status Requester for LCN modules."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pypck import inputs
from pypck.lcn_addr import LcnAddr

if TYPE_CHECKING:
    from pypck.connection import PchkConnectionManager


@dataclass(unsafe_hash=True)
class StatusRequest:
    """Data class for status requests."""

    address: LcnAddr | None  # Address of the module or group
    type: type[inputs.Input]  # Type of the input expected as response
    parameters: frozenset[tuple[str, Any]]  # {(parameter_name, parameter_value)}
    timestamp: float = field(
        compare=False
    )  # timestamp the response was received; -1=no timestamp
    response: asyncio.Future[inputs.Input] = field(
        compare=False
    )  # Future to hold the response input object


class StatusRequester:
    """Handling of status requests."""

    def __init__(
        self,
        conn: PchkConnectionManager,
    ) -> None:
        """Initialize the context."""
        self.conn = conn
        self.last_requests: set[StatusRequest] = set()
        self.unregister_inputs = self.conn.register_for_inputs(self.input_callback)
        self.max_response_age = self.conn.settings["MAX_RESPONSE_AGE"]
        self.request_semaphore = asyncio.Semaphore(
            self.conn.settings["MAX_PARALLEL_REQUESTS"]
        )
        # asyncio.get_running_loop().create_task(self.prune_loop())

    async def prune_loop(self) -> None:
        """Periodically prune old status requests."""
        while True:
            await asyncio.sleep(self.max_response_age)
            self.prune_status_requests()

    def prune_status_requests(self) -> None:
        """Prune old status requests."""
        entries_to_remove = {
            request
            for request in self.last_requests
            if asyncio.get_running_loop().time() - request.timestamp
            > self.max_response_age
        }
        for entry in entries_to_remove:
            entry.response.cancel()
        self.last_requests.difference_update(entries_to_remove)

    def get_status_requests(
        self,
        address: LcnAddr,
        request_type: type[inputs.Input],
        parameters: frozenset[tuple[str, Any]] | None = None,
        max_age: int = 0,
    ) -> list[StatusRequest]:
        """Get the status requests for the given type and parameters."""
        if parameters is None:
            parameters = frozenset()
        loop = asyncio.get_running_loop()
        results = [
            request
            for request in self.last_requests
            if request.type == request_type
            and request.address == address
            and parameters.issubset(request.parameters)
            and (
                (request.timestamp == -1)
                or (max_age == -1)
                or (loop.time() - request.timestamp < max_age)
            )
        ]
        results.sort(key=lambda request: request.timestamp, reverse=True)
        return results

    def input_callback(self, inp: inputs.Input) -> None:
        """Handle incoming inputs and set the result for the corresponding requests."""
        if not isinstance(inp, inputs.ModInput):
            return

        requests = [
            request
            for request in self.get_status_requests(inp.physical_source_addr, type(inp))
            if all(
                getattr(inp, parameter_name) == parameter_value
                for parameter_name, parameter_value in request.parameters
            )
        ]
        for request in requests:
            if request.response.done() or request.response.cancelled():
                continue
            request.timestamp = asyncio.get_running_loop().time()
            request.response.set_result(inp)

    async def request(
        self,
        address: LcnAddr,
        response_type: type[inputs.Input],
        request_pck: str,
        request_acknowledge: bool = False,
        max_age: int = 0,  # -1: no age limit / infinite age
        **request_kwargs: Any,
    ) -> inputs.Input | None:
        """Execute a status request and wait for the response."""
        async with self.request_semaphore:
            parameters = frozenset(request_kwargs.items())

            # check if we already have a received response for the current request
            if requests := self.get_status_requests(
                address, response_type, parameters, max_age
            ):
                try:
                    async with asyncio.timeout(self.conn.settings["DEFAULT_TIMEOUT"]):
                        return await requests[0].response
                except asyncio.TimeoutError:
                    return None
                except asyncio.CancelledError:
                    return None

            # no stored request or forced request: set up a new request
            request = StatusRequest(
                address,
                response_type,
                frozenset(request_kwargs.items()),
                -1,
                asyncio.get_running_loop().create_future(),
            )

            self.last_requests.discard(request)
            self.last_requests.add(request)
            result = None
            # send the request up to NUM_TRIES and wait for response future completion
            for _ in range(self.conn.settings["NUM_TRIES"]):
                device_connection = self.conn.get_address_conn(address)
                await device_connection.send_command(request_acknowledge, request_pck)
                try:
                    async with asyncio.timeout(self.conn.settings["DEFAULT_TIMEOUT"]):
                        # Need to shield the future. Otherwise it would get cancelled.
                        result = await asyncio.shield(request.response)
                        break
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break

            # if we got no results, remove the request from the set
            if result is None:
                request.response.cancel()
                self.last_requests.discard(request)
            return result
