"""Status requester."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from pypck import inputs

if TYPE_CHECKING:
    from pypck.device import DeviceConnection

_LOGGER = logging.getLogger(__name__)

ResponseT = TypeVar("ResponseT", bound=inputs.Input)


@dataclass(unsafe_hash=True)
class StatusRequest(Generic[ResponseT]):
    """Data class for status requests."""

    type: type[ResponseT]  # Type of the input expected as response
    parameters: frozenset[tuple[str, Any]]  # {(parameter_name, parameter_value)}
    timestamp: float = field(
        compare=False
    )  # timestamp the response was received; -1=no timestamp
    response: asyncio.Future[ResponseT] = field(
        compare=False
    )  # the response input object


class StatusRequester:
    """Handling of status requests."""

    current_request: StatusRequest[inputs.Input] | None

    def __init__(
        self,
        device_connection: DeviceConnection,
    ) -> None:
        """Initialize the context."""
        self.device_connection = device_connection
        self.current_request = None
        self.request_cache: set[StatusRequest[inputs.Input]] = set()
        self.max_response_age = self.device_connection.conn.settings["MAX_RESPONSE_AGE"]
        self.request_lock = asyncio.Lock()

        self.unregister_inputs = self.device_connection.register_for_inputs(
            self.input_callback
        )

    def get_status_requests(
        self,
        request_type: type[ResponseT],
        parameters: frozenset[tuple[str, Any]] | None = None,
        max_age: int = 0,
    ) -> list[StatusRequest[ResponseT]]:
        """Get the status requests for the given type and parameters."""
        if parameters is None:
            parameters = frozenset()
        results = [
            request
            for request in self.request_cache
            if request.type == request_type
            and parameters.issubset(request.parameters)
            and (
                (request.timestamp == -1)
                or (max_age == -1)
                or (asyncio.get_running_loop().time() - request.timestamp < max_age)
            )
        ]
        results.sort(key=lambda request: request.timestamp, reverse=True)
        return cast(list[StatusRequest[ResponseT]], results)

    def input_callback(self, inp: inputs.Input) -> None:
        """Handle incoming inputs and set the result for the corresponding requests."""
        # Update current request (if it exists)
        if (
            self.current_request is not None
            and not self.current_request.response.done()
        ):
            if isinstance(inp, self.current_request.type) and all(
                getattr(inp, parameter_name) == parameter_value
                for parameter_name, parameter_value in self.current_request.parameters
            ):
                self.current_request.timestamp = asyncio.get_running_loop().time()
                self.current_request.response.set_result(inp)

        # Update cached requests
        for request in self.get_status_requests(type(inp)):
            if all(
                getattr(inp, parameter_name) == parameter_value
                for parameter_name, parameter_value in request.parameters
            ):
                request.timestamp = asyncio.get_running_loop().time()
                request.response = asyncio.get_running_loop().create_future()
                request.response.set_result(inp)

    async def request(
        self,
        response_type: type[ResponseT],
        request_pck: str,
        request_acknowledge: bool = False,
        max_age: int = 0,  # -1: no age limit / infinite age
        **request_kwargs: Any,
    ) -> ResponseT | None:
        """Execute a status request and wait for the response."""
        async with self.request_lock:
            # check for matching request in cache
            if requests := self.get_status_requests(
                response_type,
                frozenset(request_kwargs.items()),
                max_age,
            ):
                _LOGGER.debug(
                    "from %s: %s (cached)",
                    self.device_connection.conn.connection_id,
                    requests[0].response.result().pck,
                )
                return requests[0].response.result()

            # no matching request in cache
            self.current_request = StatusRequest(
                response_type,
                frozenset(request_kwargs.items()),
                -1,
                asyncio.get_running_loop().create_future(),
            )

            result = None
            # send the request up to NUM_TRIES and wait for response future completion
            for _ in range(self.device_connection.conn.settings["NUM_TRIES"]):
                await self.device_connection.send_command(
                    request_acknowledge, request_pck
                )

                try:
                    async with asyncio.timeout(
                        self.device_connection.conn.settings["DEFAULT_TIMEOUT"]
                    ):
                        # Need to shield the future. Otherwise it would get cancelled.
                        result = await asyncio.shield(self.current_request.response)
                        break
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break

            if result is not None:  # add request to cache
                self.request_cache.discard(self.current_request)
                self.request_cache.add(self.current_request)

            return cast(ResponseT | None, result)
