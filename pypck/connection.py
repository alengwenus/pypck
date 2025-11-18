"""Connection classes for pypck."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable
from types import TracebackType
from typing import Any

from pypck import inputs, lcn_defs
from pypck.device import DeviceConnection
from pypck.helpers import TaskRegistry
from pypck.lcn_addr import LcnAddr
from pypck.lcn_defs import LcnEvent
from pypck.pck_commands import PckGenerator

_LOGGER = logging.getLogger(__name__)


class PchkLicenseError(Exception):
    """Exception which is raised if a license error occurred."""

    def __init__(self, message: str | None = None):
        """Initialize instance."""
        if message is None:
            message = (
                "License Error: Maximum number of connections was reached. An "
                "additional license key is required."
            )
        super().__init__(message)


class PchkAuthenticationError(Exception):
    """Exception which is raised if authentication failed."""

    def __init__(self, message: str | None = None):
        """Initialize instance."""
        if message is None:
            message = "Authentication failed"
        super().__init__(message)


class PchkConnectionRefusedError(Exception):
    """Exception which is raised if connection was refused."""

    def __init__(self, message: str | None = None):
        """Initialize instance."""
        if message is None:
            message = "Connection refused"
        super().__init__(message)


class PchkConnectionFailedError(Exception):
    """Exception which is raised if connection was refused."""

    def __init__(self, message: str | None = None):
        """Initialize instance."""
        if message is None:
            message = "Connection failed"
        super().__init__(message)


class PchkLcnNotConnectedError(Exception):
    """Exception which is raised if there is no connection to the LCN bus."""

    def __init__(self, message: str | None = None):
        """Initialize instance."""
        if message is None:
            message = "LCN not connected."
        super().__init__(message)


class PchkConnectionManager:
    """Connection to LCN-PCHK."""

    last_ping: float
    ping_timeout_handle: asyncio.TimerHandle | None
    authentication_completed_future: asyncio.Future[bool]
    license_error_future: asyncio.Future[bool]

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        settings: dict[str, Any] | None = None,
        connection_id: str = "PCHK",
    ) -> None:
        """Construct PchkConnectionManager."""
        self.task_registry = TaskRegistry()
        self.host = host
        self.port = port
        self.connection_id = connection_id

        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.buffer: asyncio.Queue[bytes] = asyncio.Queue()
        self.last_bus_activity = asyncio.get_running_loop().time()

        self.username = username
        self.password = password

        # Settings
        if settings is None:
            settings = {}
        self.settings = lcn_defs.default_connection_settings
        self.settings.update(settings)

        self.idle_time = self.settings["BUS_IDLE_TIME"]
        self.ping_send_delay = self.settings["PING_SEND_DELAY"]
        self.ping_recv_timeout = self.settings["PING_RECV_TIMEOUT"]
        self.ping_timeout_handle = None
        self.ping_counter = 0
        self.dim_mode = self.settings["DIM_MODE"]
        self.status_mode = lcn_defs.OutputPortStatusMode.PERCENT

        self.is_lcn_connected = True
        self.local_seg_id = 0

        # Events, Futures, Locks for synchronization
        self.segment_scan_completed_event = asyncio.Event()
        self.authentication_completed_future = asyncio.Future()
        self.license_error_future = asyncio.Future()
        self.module_serial_number_received = asyncio.Lock()
        self.segment_coupler_response_received = asyncio.Lock()

        # All modules from or to a communication occurs are represented by a
        # unique ModuleConnection object.  All ModuleConnection objects are
        # stored in this dictionary.  Communication to groups is handled by
        # GroupConnection object that are created on the fly and not stored
        # permanently.
        self.device_connections: dict[LcnAddr, DeviceConnection] = {}
        self.segment_coupler_ids: list[int] = []

        self.input_callbacks: set[Callable[[inputs.Input], None]] = set()
        self.event_callbacks: set[Callable[[LcnEvent], None]] = set()
        self.register_for_events(self.event_callback)

    # Socket read/write

    async def read_data_loop(self) -> None:
        """Processes incoming data."""
        assert self.reader is not None
        assert self.writer is not None
        loop = asyncio.get_running_loop()
        _LOGGER.debug("Read data loop started")
        try:
            while not self.writer.is_closing():
                try:
                    data = await self.reader.readuntil(
                        PckGenerator.TERMINATION.encode()
                    )
                    self.last_bus_activity = loop.time()
                except (
                    asyncio.IncompleteReadError,
                    TimeoutError,
                    OSError,
                ):
                    _LOGGER.debug("Connection to %s lost", self.connection_id)
                    self.fire_event(LcnEvent.CONNECTION_LOST)
                    await self.async_close()
                    break

                try:
                    message = data.decode("utf-8").split(PckGenerator.TERMINATION)[0]
                except UnicodeDecodeError as err:
                    try:
                        message = data.decode("cp1250").split(PckGenerator.TERMINATION)[
                            0
                        ]
                        _LOGGER.warning(
                            "Incorrect PCK encoding detected, possibly caused by LinHK: %s - PCK recovered using cp1250",
                            err,
                        )
                    except UnicodeDecodeError as err2:
                        _LOGGER.warning(
                            "PCK decoding error: %s - skipping received PCK message",
                            err2,
                        )
                        continue
                await self.process_message(message)
        finally:
            _LOGGER.debug("Read data loop closed")

    async def write_data_loop(self) -> None:
        """Processes queue and writes data."""
        assert self.writer is not None
        loop = asyncio.get_running_loop()
        try:
            _LOGGER.debug("Write data loop started")
            while not self.writer.is_closing():
                data = await self.buffer.get()
                while (loop.time() - self.last_bus_activity) < self.idle_time:
                    await asyncio.sleep(self.idle_time)

                _LOGGER.debug(
                    "to %s: %s",
                    self.connection_id,
                    data.decode().rstrip(PckGenerator.TERMINATION),
                )
                self.writer.write(data)
                await self.writer.drain()
                self.last_bus_activity = loop.time()
        finally:
            # empty the queue
            while not self.buffer.empty():
                await self.buffer.get()
            _LOGGER.debug("Write data loop closed")

    # Open/close connection, authentication & setup.

    async def async_connect(self, timeout: float = 30) -> None:
        """Establish a connection to PCHK at the given socket."""
        self.authentication_completed_future = asyncio.Future()
        self.license_error_future = asyncio.Future()

        _LOGGER.debug(
            "Starting connection attempt to %s server at %s:%d",
            self.connection_id,
            self.host,
            self.port,
        )

        done: Iterable[asyncio.Future[Any]]
        pending: Iterable[asyncio.Future[Any]]
        done, pending = await asyncio.wait(
            (
                asyncio.create_task(self.open_connection()),
                self.license_error_future,
                self.authentication_completed_future,
            ),
            timeout=timeout,
            return_when=asyncio.FIRST_EXCEPTION,
        )

        # Raise any exception which occurs
        # (ConnectionRefusedError, PchkAuthenticationError, PchkLicenseError)
        for awaitable in done:
            if not awaitable.cancelled():
                if exc := awaitable.exception():
                    await self.async_close()
                    if isinstance(exc, (ConnectionRefusedError, OSError)):
                        raise PchkConnectionRefusedError()
                    else:
                        raise exc

        if pending:
            for awaitable in pending:
                awaitable.cancel()
            await self.async_close()
            raise PchkConnectionFailedError()

        if not self.is_lcn_connected:
            raise PchkLcnNotConnectedError()

        # start segment scan
        await self.scan_segment_couplers(
            self.settings["SK_NUM_TRIES"], self.settings["DEFAULT_TIMEOUT"]
        )

    async def open_connection(self) -> None:
        """Connect to PCHK server (no authentication or license error check)."""
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

        address = self.writer.get_extra_info("peername")
        _LOGGER.debug("%s server connected at %s:%d", self.connection_id, *address)

        # main write loop
        self.task_registry.create_task(self.write_data_loop())

        # main read loop
        self.task_registry.create_task(self.read_data_loop())

    async def async_close(self) -> None:
        """Close the active connection."""
        if self.ping_timeout_handle is not None:
            self.ping_timeout_handle.cancel()
        await self.task_registry.cancel_all_tasks()
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except OSError:  # occurs when TCP connection is lost
                pass

        _LOGGER.debug("Connection to %s closed.", self.connection_id)

    async def wait_closed(self) -> None:
        """Wait until connection to PCHK server is closed."""
        if self.writer is not None:
            await self.writer.wait_closed()

    async def __aenter__(self) -> "PchkConnectionManager":
        """Context manager enter method."""
        await self.async_connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        """Context manager exit method."""
        await self.async_close()
        return None

    async def on_auth(self, success: bool) -> None:
        """Is called after successful authentication."""
        if success:
            _LOGGER.debug("%s authorization successful!", self.connection_id)
            self.authentication_completed_future.set_result(True)
            # Try to set the PCHK decimal mode
            await self.send_command(PckGenerator.set_dec_mode(), to_host=True)
        else:
            _LOGGER.debug("%s authorization failed!", self.connection_id)
            self.authentication_completed_future.set_exception(PchkAuthenticationError)

    async def on_license_error(self) -> None:
        """Is called if a license error occurs during connection."""
        _LOGGER.debug("%s: License Error.", self.connection_id)
        self.license_error_future.set_exception(PchkLicenseError())

    async def on_successful_login(self) -> None:
        """Is called after connection to LCN bus system is established."""
        _LOGGER.debug("%s login successful.", self.connection_id)
        await self.send_command(
            PckGenerator.set_operation_mode(self.dim_mode, self.status_mode),
            to_host=True,
        )
        self.task_registry.create_task(self.ping())

    async def lcn_connection_status_changed(self, is_lcn_connected: bool) -> None:
        """Set the current connection state to the LCN bus."""
        self.is_lcn_connected = is_lcn_connected
        self.fire_event(LcnEvent.BUS_CONNECTION_STATUS_CHANGED)
        if is_lcn_connected:
            _LOGGER.debug("%s: LCN is connected.", self.connection_id)
            self.fire_event(LcnEvent.BUS_CONNECTED)
        else:
            _LOGGER.debug("%s: LCN is not connected.", self.connection_id)
            self.fire_event(LcnEvent.BUS_DISCONNECTED)

    async def ping_received(self, count: int | None) -> None:
        """Ping was received."""
        if self.ping_timeout_handle is not None:
            self.ping_timeout_handle.cancel()
        self.last_ping = asyncio.get_running_loop().time()

    def is_ready(self) -> bool:
        """Retrieve the overall connection state."""
        return self.segment_scan_completed_event.is_set()

    # Addresses, modules and groups

    def set_local_seg_id(self, local_seg_id: int) -> None:
        """Set the local segment id."""
        old_local_seg_id = self.local_seg_id

        self.local_seg_id = local_seg_id
        # replace all device_connections with current local_seg_id with new
        # local_seg_id
        for addr in list(self.device_connections):
            if addr.seg_id == old_local_seg_id:
                address_conn = self.device_connections.pop(addr)
                address_conn.addr = LcnAddr(
                    self.local_seg_id, addr.addr_id, addr.is_group
                )
                self.device_connections[address_conn.addr] = address_conn

    def physical_to_logical(self, addr: LcnAddr) -> LcnAddr:
        """Convert the physical segment id of an address to the logical one."""
        return LcnAddr(
            self.local_seg_id if addr.seg_id in (0, 4) else addr.seg_id,
            addr.addr_id,
            addr.is_group,
        )

    def get_device_connection(self, addr: LcnAddr) -> DeviceConnection:
        """Create and/or return a connection to the given module or group."""
        if addr.seg_id == 0 and self.local_seg_id != -1:
            addr = LcnAddr(self.local_seg_id, addr.addr_id, addr.is_group)

        device_connection = self.device_connections.get(addr, None)
        if device_connection is None:
            device_connection = DeviceConnection(
                self,
                addr,
                wants_ack=False if addr.is_group else self.settings["ACKNOWLEDGE"],
            )
            self.device_connections[addr] = device_connection

        return device_connection

    # Other

    async def dump_modules(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Dump all modules and information about them in a JSON serializable dict."""
        dump: dict[str, dict[str, dict[str, Any]]] = {}
        for address_conn in self.device_connections.values():
            seg = f"{address_conn.addr.seg_id:d}"
            addr = f"{address_conn.addr.addr_id}"
            if seg not in dump:
                dump[seg] = {}
            dump[seg][addr] = await address_conn.dump_details()
        return dump

    # Command sending / retrieval.

    async def send_command(
        self, pck: bytes | str, to_host: bool = False, **kwargs: Any
    ) -> bool:
        """Send a PCK command to the PCHK server."""
        if not self.is_lcn_connected and not to_host:
            return False

        assert self.writer is not None
        if not self.writer.is_closing():
            if isinstance(pck, str):
                data = (pck + PckGenerator.TERMINATION).encode()
            else:
                data = pck + PckGenerator.TERMINATION.encode()
            await self.buffer.put(data)
            return True
        return False

    async def process_message(self, message: str) -> None:
        """Is called when a new text message is received from the PCHK server."""
        _LOGGER.debug("from %s: %s", self.connection_id, message)
        inps = inputs.InputParser.parse(message)

        if inps is not None:
            for inp in inps:
                await self.async_process_input(inp)

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Process an input command."""
        # Inputs from Host
        if isinstance(inp, inputs.AuthUsername):
            await self.send_command(self.username, to_host=True)
        elif isinstance(inp, inputs.AuthPassword):
            await self.send_command(self.password, to_host=True)
        elif isinstance(inp, inputs.AuthOk):
            await self.on_auth(True)
        elif isinstance(inp, inputs.AuthFailed):
            await self.on_auth(False)
        elif isinstance(inp, inputs.LcnConnState):
            await self.lcn_connection_status_changed(inp.is_lcn_connected)
        elif isinstance(inp, inputs.LicenseError):
            await self.on_license_error()
        elif isinstance(inp, inputs.DecModeSet):
            self.license_error_future.set_result(True)
            await self.on_successful_login()
        elif isinstance(inp, inputs.CommandError):
            _LOGGER.debug("LCN command error: %s", inp.message)
        elif isinstance(inp, inputs.Ping):
            await self.ping_received(inp.count)
        elif isinstance(inp, inputs.ModSk):
            if inp.physical_source_addr.seg_id == 0:
                self.set_local_seg_id(inp.reported_seg_id)
            if self.segment_coupler_response_received.locked():
                self.segment_coupler_response_received.release()
            # store reported segment coupler id
            if inp.reported_seg_id not in self.segment_coupler_ids:
                self.segment_coupler_ids.append(inp.reported_seg_id)
        elif isinstance(inp, inputs.Unknown):
            return

        # Inputs from bus
        elif self.is_ready():
            if isinstance(inp, inputs.ModInput):
                logical_source_addr = self.physical_to_logical(inp.physical_source_addr)
                if not logical_source_addr.is_group:
                    module_conn = self.get_device_connection(logical_source_addr)
                    if isinstance(inp, inputs.ModSn):
                        # used to extend scan_modules() timeout
                        if self.module_serial_number_received.locked():
                            self.module_serial_number_received.release()

                    await module_conn.async_process_input(inp)

            # Forward all known inputs to callback listeners.
            for input_callback in self.input_callbacks:
                input_callback(inp)

    async def ping(self) -> None:
        """Send pings."""
        assert self.writer is not None
        while not self.writer.is_closing():
            await self.send_command(f"^ping{self.ping_counter:d}", to_host=True)
            self.ping_timeout_handle = asyncio.get_running_loop().call_later(
                self.ping_recv_timeout, lambda: self.fire_event(LcnEvent.PING_TIMEOUT)
            )
            self.ping_counter += 1
            await asyncio.sleep(self.ping_send_delay)

    async def scan_modules(self, num_tries: int = 3, timeout: float = 3) -> None:
        """Scan for modules on the bus.

        This is a convenience coroutine which handles all the logic when
        scanning modules on the bus. Because of heavy bus traffic, not all
        modules might respond to a scan command immediately.
        The coroutine will make 'num_tries' attempts to send a scan command
        and waits 'timeout' after the last module response before
        proceeding to the next try.
        """
        segment_coupler_ids = (
            self.segment_coupler_ids if self.segment_coupler_ids else [0]
        )

        for _ in range(num_tries):
            for segment_id in segment_coupler_ids:
                if segment_id == self.local_seg_id:
                    segment_id = 0
                await self.send_command(
                    PckGenerator.generate_address_header(
                        LcnAddr(segment_id, 3, True), self.local_seg_id, True
                    )
                    + PckGenerator.empty()
                )

            # Wait loop which is extended on every serial number received
            while True:
                try:
                    await asyncio.wait_for(
                        self.module_serial_number_received.acquire(),
                        timeout,
                    )
                except asyncio.TimeoutError:
                    break

    async def scan_segment_couplers(
        self, num_tries: int = 3, timeout: float = 1.5
    ) -> None:
        """Scan for segment couplers on the bus.

        This is a convenience coroutine which handles all the logic when
        scanning segment couplers on the bus. Because of heavy bus traffic,
        not all segment couplers might respond to a scan command immediately.
        The coroutine will make 'num_tries' attempts to send a scan command
        and waits 'timeout' after the last segment coupler response
        before proceeding to the next try.
        """
        for _ in range(num_tries):
            await self.send_command(
                PckGenerator.generate_address_header(
                    LcnAddr(3, 3, True), self.local_seg_id, False
                )
                + PckGenerator.segment_coupler_scan()
            )

            # Wait loop which is extended on every segment coupler response
            while True:
                try:
                    await asyncio.wait_for(
                        self.segment_coupler_response_received.acquire(),
                        timeout,
                    )
                except asyncio.TimeoutError:
                    break

        # No segment coupler expected (num_tries=0)
        if len(self.segment_coupler_ids) == 0:
            _LOGGER.debug("%s: No segment coupler found.", self.connection_id)

        self.segment_scan_completed_event.set()

    # Callbacks for inputs and events

    def register_for_inputs(
        self, callback: Callable[[inputs.Input], None]
    ) -> Callable[..., None]:
        """Register a function for callback on PCK message received.

        Returns a function to unregister the callback.
        """
        self.input_callbacks.add(callback)
        return lambda callback=callback: self.input_callbacks.remove(callback)

    def fire_event(self, event: LcnEvent) -> None:
        """Fire event."""
        for event_callback in self.event_callbacks:
            event_callback(event)

    def register_for_events(
        self, callback: Callable[[lcn_defs.LcnEvent], None]
    ) -> Callable[..., None]:
        """Register a function for callback on LCN events.

        Return a function to unregister the callback.
        """
        self.event_callbacks.add(callback)
        return lambda callback=callback: self.event_callbacks.remove(callback)

    def event_callback(self, event: LcnEvent) -> None:
        """Handle events from PchkConnection."""
        _LOGGER.debug("%s: LCN-Event: %s", self.connection_id, event)
