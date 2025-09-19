"""Status requester."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pypck import inputs

if TYPE_CHECKING:
    from pypck.device import DeviceConnection

_LOGGER = logging.getLogger(__name__)


@dataclass(unsafe_hash=True)
class StatusRequest:
    """Data class for status requests."""

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
        device_connection: DeviceConnection,
    ) -> None:
        """Initialize the context."""
        self.device_connection = device_connection
        self.last_requests: set[StatusRequest] = set()
        self.unregister_inputs = self.device_connection.register_for_inputs(
            self.input_callback
        )
        self.max_response_age = self.device_connection.conn.settings["MAX_RESPONSE_AGE"]
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
        requests = [
            request
            for request in self.get_status_requests(type(inp))
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
        response_type: type[inputs.Input],
        request_pck: str,
        request_acknowledge: bool = False,
        max_age: int = 0,  # -1: no age limit / infinite age
        **request_kwargs: Any,
    ) -> inputs.Input | None:
        """Execute a status request and wait for the response."""
        parameters = frozenset(request_kwargs.items())

        # check if we already have a received response for the current request
        if requests := self.get_status_requests(response_type, parameters, max_age):
            try:
                async with asyncio.timeout(
                    self.device_connection.conn.settings["DEFAULT_TIMEOUT"]
                ):
                    return await requests[0].response
            except asyncio.TimeoutError:
                return None
            except asyncio.CancelledError:
                return None

        # no stored request or forced request: set up a new request
        request = StatusRequest(
            response_type,
            frozenset(request_kwargs.items()),
            -1,
            asyncio.get_running_loop().create_future(),
        )

        self.last_requests.discard(request)
        self.last_requests.add(request)
        result = None
        # send the request up to NUM_TRIES and wait for response future completion
        for _ in range(self.device_connection.conn.settings["NUM_TRIES"]):
            await self.device_connection.send_command(request_acknowledge, request_pck)

            try:
                async with asyncio.timeout(
                    self.device_connection.conn.settings["DEFAULT_TIMEOUT"]
                ):
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
