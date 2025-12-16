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

    current_request: StatusRequest

    def __init__(
        self,
        device_connection: DeviceConnection,
    ) -> None:
        """Initialize the context."""
        self.device_connection = device_connection
        self.last_requests: set[StatusRequest] = set()
        self.max_response_age = self.device_connection.conn.settings["MAX_RESPONSE_AGE"]
        self.request_lock = asyncio.Lock()

    def input_callback(self, inp: inputs.Input) -> None:
        """Handle incoming inputs and set the result for the corresponding requests."""
        if (
            self.current_request.response.done()
            or self.current_request.response.cancelled()
        ):
            return

        if isinstance(inp, self.current_request.type) and all(
            getattr(inp, parameter_name) == parameter_value
            for parameter_name, parameter_value in self.current_request.parameters
        ):
            self.current_request.timestamp = asyncio.get_running_loop().time()
            self.current_request.response.set_result(inp)

    async def request(
        self,
        response_type: type[inputs.Input],
        request_pck: str,
        request_acknowledge: bool = False,
        max_age: int = 0,  # -1: no age limit / infinite age
        **request_kwargs: Any,
    ) -> inputs.Input | None:
        """Execute a status request and wait for the response."""
        async with self.request_lock:
            self.current_request = StatusRequest(
                response_type,
                frozenset(request_kwargs.items()),
                -1,
                asyncio.get_running_loop().create_future(),
            )

            unregister_inputs = self.device_connection.register_for_inputs(
                self.input_callback
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

            # if we got no results, remove the request from the set
            if result is None:
                self.current_request.response.cancel()

            unregister_inputs()
            return result
