"""Copyright (c) 2006-2020 by the respective copyright holders.

See the NOTICE file(s) distributed with this work for additional
information.

This program and the accompanying materials are made available under the
terms of the Eclipse Public License 2.0 which is available at
http://www.eclipse.org/legal/epl-2.0

SPDX-License-Identifier: EPL-2.0

Contributors:
  Andre Lengwenus - port to Python and further improvements
  Tobias Juettner - initial LCN binding for openHAB (Java)
"""

import asyncio
import logging
from types import TracebackType
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Type,
    Union,
)

from pypck import inputs, lcn_defs
from pypck.helpers import TaskRegistry
from pypck.lcn_addr import LcnAddr
from pypck.module import AbstractConnection, GroupConnection, ModuleConnection
from pypck.pck_commands import PckGenerator

_LOGGER = logging.getLogger(__name__)

READ_TIMEOUT = -1
SOCKET_CLOSED = -2


class PchkLicenseError(Exception):
    """Exception which is raised if a license error occurred."""

    def __init__(self, message: Optional[str] = None):
        """Initialize instance."""
        if message is None:
            message = (
                "Maximum number of connections was reached. An "
                "additional license key is required."
            )
        super().__init__(message)


class PchkAuthenticationError(Exception):
    """Exception which is raised if authentication failed."""

    def __init__(self, message: Optional[str] = None):
        """Initialize instance."""
        if message is None:
            message = "Authentication failed."
        super().__init__(message)


class PchkLcnNotConnectedError(Exception):
    """Exception which is raised if there is no connection to the LCN bus."""

    def __init__(self, message: Optional[str] = None):
        """Initialize instance."""
        if message is None:
            message = "LCN not connected."
        super().__init__(message)


class PchkConnection:
    """Socket connection to LCN-PCHK server.

    :param    str    host:        Server IP address formatted as
                                  xxx.xxx.xxx.xxx
    :param    int    port:        Server port

    :Note:

    :class:`PchkConnection` does only open a port to the
    PCHK server and allows to send and receive plain text. Use
    :func:`~PchkConnection.send_command` and
    :func:`~PchkConnection.process_input` callback to send and receive
    text messages.

    For login logic or communication with modules use
    :class:`~PchkConnectionManager`.
    """

    def __init__(self, host: str, port: int, connection_id: str = "PCHK"):
        """Construct PchkConnection."""
        self.task_registry = TaskRegistry()
        self.host = host
        self.port = port
        self.connection_id = connection_id
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.event_handler: Callable[
            [str], Awaitable[None]
        ] = self.default_event_handler

    async def async_connect(self) -> None:
        """Connect to a PCHK server (no authentication or license error check)."""
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        address = self.writer.get_extra_info("peername")
        _LOGGER.debug("%s server connected at %s:%d", self.connection_id, *address)

        # main read loop
        self.task_registry.create_task(self.read_data_loop())

    def connect(self) -> None:
        """Create a task to connect to a PCHK server concurrently."""
        self.task_registry.create_task(self.async_connect())

    async def read_data_loop(self) -> None:
        """Is called when some data is received."""
        assert self.reader is not None
        assert self.writer is not None
        while not self.writer.is_closing():
            try:
                data = await self.reader.readuntil(PckGenerator.TERMINATION.encode())
            except asyncio.IncompleteReadError:
                _LOGGER.debug("Connection to %s lost", self.connection_id)
                await self.event_handler("connection-lost")
                await self.async_close()
                break
            except asyncio.CancelledError:
                break

            try:
                message = data.decode().split(PckGenerator.TERMINATION)[0]
            except UnicodeDecodeError as err:
                _LOGGER.warning(
                    "PCK decoding error: %s - skipping received PCK message", err
                )
                continue
            await self.process_message(message)

    async def send_command(self, pck: Union[bytes, str], **kwargs: Any) -> bool:
        """Send a PCK command to the PCHK server.

        :param    str    pck:    PCK command
        """
        assert self.writer is not None
        if not self.writer.is_closing():
            _LOGGER.debug("to %s: %s", self.connection_id, pck)
            if isinstance(pck, str):
                data = (pck + PckGenerator.TERMINATION).encode()
            else:
                data = pck + PckGenerator.TERMINATION.encode()
            self.writer.write(data)
            await self.writer.drain()
            return True
        return False

    async def process_message(self, message: str) -> None:
        """Is called when a new text message is received from the PCHK server.

        This class should be reimplemented in any subclass which evaluates
        received messages.

        :param    str    input:    Input text message
        """
        _LOGGER.debug("from %s: %s", self.connection_id, message)

    async def async_close(self) -> None:
        """Close the active connection."""
        await self.task_registry.cancel_all_tasks()
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    def set_event_handler(self, coro: Callable[[str], Awaitable[None]]) -> None:
        """Set the event handler for specific LCN events."""
        if coro is None:
            self.event_handler = self.default_event_handler
        else:
            self.event_handler = coro

    async def default_event_handler(self, event: str) -> None:
        """Handle events for specific LCN events."""

    async def wait_closed(self) -> None:
        """Wait until connection to PCHK server is closed."""
        if self.writer is not None:
            await self.writer.wait_closed()


class PchkConnectionManager(PchkConnection):
    """Connection to LCN-PCHK.

    Has the following tasks:
    - Initiates login procedure.
    - Ping PCHK.
    - Parse incoming commands and create input objects.
    - Calls input object's process method.
    - Updates seg_id of ModuleConnections if segment scan finishes.

    :param    str    host:        Server IP address formatted as
                                  xxx.xxx.xxx.xxx
    :param    int    port:        Server port
    :param    str    username:    usernam for login.
    :param    str    password:    Password for login.

    An example how to setup a proper connection to PCHK including login and
    (automatic) segment coupler scan is shown below.

    :Example:

    >>> import asyncio
    >>> loop = asyncio.get_event_loop()
    >>> connection = PchkConnectionManager(loop, '10.1.2.3', 4114,
                                           'lcn', 'lcn')
    >>> await connection.async_connect()
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        settings: Optional[Dict[str, Any]] = None,
        connection_id: str = "PCHK",
    ):
        """Construct PchkConnectionManager."""
        super().__init__(host, port, connection_id)

        self.username = username
        self.password = password

        if settings is None:
            settings = {}
        self.settings = lcn_defs.default_connection_settings
        self.settings.update(settings)

        self.ping_timeout = self.settings["PING_TIMEOUT"] / 1000  # seconds
        self.ping_counter = 0

        self.dim_mode = self.settings["DIM_MODE"]
        self.status_mode = lcn_defs.OutputPortStatusMode.PERCENT

        self.is_lcn_connected = True
        self.local_seg_id = 0

        # Events, Futures, Locks for synchronization
        self.segment_scan_completed_event = asyncio.Event()
        self.authentication_completed_future: "asyncio.Future[bool]" = asyncio.Future()
        self.license_error_future: "asyncio.Future[bool]" = asyncio.Future()
        self.module_serial_number_received = asyncio.Lock()
        self.segment_coupler_response_received = asyncio.Lock()

        # All modules from or to a communication occurs are represented by a
        # unique ModuleConnection object.  All ModuleConnection objects are
        # stored in this dictionary.  Communication to groups is handled by
        # GroupConnection object that are created on the fly and not stored
        # permanently.
        self.address_conns: Dict[LcnAddr, ModuleConnection] = {}
        self.segment_coupler_ids: List[int] = []

        self.input_callbacks: Set[Callable[[inputs.Input], None]] = set()

    async def __aenter__(self) -> "PchkConnectionManager":
        """Context manager enter method."""
        await self.async_connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ) -> None:
        """Context manager exit method."""
        await self.async_close()
        return None

    async def send_command(
        self, pck: Union[bytes, str], to_host: bool = False, **kwargs: Any
    ) -> bool:
        """Send a PCK command to the PCHK server.

        :param    str    pck:    PCK command
        """
        if not self.is_lcn_connected and not to_host:
            return False
        return await super().send_command(pck)

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
        """Set the current connection state to the LCN bus.

        :param    bool    is_lcn_connected: Current connection status
        """
        self.is_lcn_connected = is_lcn_connected
        self.task_registry.create_task(
            self.event_handler("lcn-connection-status-changed")
        )
        if is_lcn_connected:
            _LOGGER.debug("%s: LCN is connected.", self.connection_id)
            self.task_registry.create_task(self.event_handler("lcn-connected"))
        else:
            _LOGGER.debug("%s: LCN is not connected.", self.connection_id)
            self.task_registry.create_task(self.event_handler("lcn-disconnected"))

    async def async_connect(self, timeout: int = 30) -> None:
        """Establish a connection to PCHK at the given socket.

        Ensures that the LCN bus is present and authorizes at PCHK.
        Raise a :class:`TimeoutError`, if connection could not be established
        within the given timeout.

        :param    int    timeout:    Timeout in seconds
        """
        done: Iterable["asyncio.Future[Any]"]
        pending: Iterable["asyncio.Future[Any]"]
        done, pending = await asyncio.wait(
            (
                super().async_connect(),
                self.authentication_completed_future,
                self.license_error_future,
            ),
            timeout=timeout,
            return_when=asyncio.FIRST_EXCEPTION,
        )

        # Raise any exception which occurs
        # (ConnectionRefusedError, PchkAuthenticationError, PchkLicenseError)
        for awaitable in done:
            if awaitable.exception():
                raise awaitable.exception()  # type: ignore

        if pending:
            for task in pending:
                task.cancel()
            raise TimeoutError(
                f"Timeout error while connecting to {self.connection_id}."
            )

        # start segment scan
        await self.scan_segment_couplers(
            self.settings["SK_NUM_TRIES"], self.settings["DEFAULT_TIMEOUT_MSEC"]
        )

    async def async_close(self) -> None:
        """Close the active connection."""
        await self.cancel_requests()
        await super().async_close()
        _LOGGER.debug("Connection to %s closed.", self.connection_id)

    def set_local_seg_id(self, local_seg_id: int) -> None:
        """Set the local segment id.

        :param    int    local_seg_id:    The local segment_id.
        """
        old_local_seg_id = self.local_seg_id

        self.local_seg_id = local_seg_id
        # replace all address_conns with current local_seg_id with new
        # local_seg_id
        for addr in list(self.address_conns):
            if addr.seg_id == old_local_seg_id:
                address_conn = self.address_conns.pop(addr)
                address_conn.addr = LcnAddr(
                    self.local_seg_id, addr.addr_id, addr.is_group
                )
                self.address_conns[address_conn.addr] = address_conn

    def physical_to_logical(self, addr: LcnAddr) -> LcnAddr:
        """Convert the physical segment id of an address to the logical one.

        :param    addr:    The module's/group's address
        :type     addr:    :class:`~LcnAddr`

        :returns:    The module's/group's address
        :rtype:      :class:`~LcnAddr`
        """
        return LcnAddr(
            self.local_seg_id if addr.seg_id in (0, 4) else addr.seg_id,
            addr.addr_id,
            addr.is_group,
        )

    def is_ready(self) -> bool:
        """Retrieve the overall connection state.

        Nothing should be sent before this is signaled.

        :returns:    True if everything is set-up, False otherwise
        :rtype:      bool
        """
        return self.segment_scan_completed_event.is_set()

    def get_module_conn(
        self, addr: LcnAddr, request_serials: bool = True
    ) -> ModuleConnection:
        """Create and/or return the given LCN module.

        The ModuleConnection object is used for further communication
        with the module (e.g. sending commands).

        :param    addr:    The module's address
        :type     addr:    :class:`~LcnAddr`

        :returns: The address connection object (never null)
        :rtype: `~ModuleConnection`

        :Example:

        >>> address = LcnAddr(0, 7, False)
        >>> module = pchk_connection.get_module_conn(address)
        >>> module.toggle_output(0, 5)
        """
        assert not addr.is_group
        if addr.seg_id == 0 and self.local_seg_id != -1:
            addr = LcnAddr(self.local_seg_id, addr.addr_id, addr.is_group)
        address_conn = self.address_conns.get(addr, None)
        if address_conn is None:
            address_conn = ModuleConnection(self, addr)
            if request_serials:
                self.task_registry.create_task(address_conn.request_serials())
            self.address_conns[addr] = address_conn

        return address_conn

    def get_group_conn(self, addr: LcnAddr) -> GroupConnection:
        """Create and return the GroupConnection for the given group.

        The GroupConnection can be used for sending commands to all
        modules that are static or dynamic members of the group.

        :param    addr:    The group's address
        :type     addr:    :class:`~LcnAddr`

        :returns: The address connection object (never null)
        :rtype: `~GroupConnection`

        :Example:

        >>> address = LcnAddr(0, 7, True)
        >>> group = pchk_connection.get_group_conn(address)
        >>> group.toggle_output(0, 5)
        """
        assert addr.is_group
        if addr.seg_id == 0 and self.local_seg_id != -1:
            addr = LcnAddr(self.local_seg_id, addr.addr_id, addr.is_group)
        return GroupConnection(self, addr)

    def get_address_conn(
        self, addr: LcnAddr, request_serials: bool = True
    ) -> AbstractConnection:
        """Create and/or return an AbstractConnection to the given module or group.

        The LCN module/group object is used for further communication
        with the module/group (e.g. sending commands).

        :param    addr:    The module's/group's address
        :type     addr:    :class:`~LcnAddr`

        :returns: The address connection object (never null)
        :rtype: `~AbstractConnection`

        :Example:

        >>> address = LcnAddr(0, 7, False)
        >>> target = pchk_connection.get_address_conn(address)
        >>> target.toggle_output(0, 5)
        """
        if addr.is_group:
            return self.get_group_conn(addr)
        return self.get_module_conn(addr, request_serials)

    def dump_modules(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Dump all modules and information about them in a JSON serializable dict."""
        dump: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for address_conn in self.address_conns.values():
            seg = f"{address_conn.addr.seg_id:d}"
            addr = f"{address_conn.addr.addr_id}"
            if seg not in dump:
                dump[seg] = {}
            dump[seg][addr] = address_conn.dump_details()
        return dump

    async def scan_modules(self, num_tries: int = 3, timeout_msec: int = 3000) -> None:
        """Scan for modules on the bus.

        This is a convenience coroutine which handles all the logic when
        scanning modules on the bus. Because of heavy bus traffic, not all
        modules might respond to a scan command immediately.
        The coroutine will make 'num_tries' attempts to send a scan command
        and waits 'timeout_msec' after the last module response before
        proceeding to the next try.

        :param      int     num_tries:      Scan attempts (default=3)
        :param      int     timeout_msec:   Timeout in msec for each try
                                            (default=3000)
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
                        timeout_msec / 1000,
                    )
                except asyncio.TimeoutError:
                    break

    async def scan_segment_couplers(
        self, num_tries: int = 3, timeout_msec: int = 1500
    ) -> None:
        """Scan for segment couplers on the bus.

        This is a convenience coroutine which handles all the logic when
        scanning segment couplers on the bus. Because of heavy bus traffic,
        not all segment couplers might respond to a scan command immediately.
        The coroutine will make 'num_tries' attempts to send a scan command
        and waits 'timeout_msec' after the last segment coupler response
        before proceeding to the next try.

        :param      int     num_tries:      Scan attempts (default=3)
        :param      int     timeout_msec:   Timeout in msec for each try
                                            (default=3000)
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
                        timeout_msec / 1000,
                    )
                except asyncio.TimeoutError:
                    break

        # No segment coupler expected (num_tries=0)
        if len(self.segment_coupler_ids) == 0:
            _LOGGER.debug("%s: No segment coupler found.", self.connection_id)

        self.segment_scan_completed_event.set()

    async def ping(self) -> None:
        """Send pings."""
        assert self.writer is not None
        while not self.writer.is_closing():
            await self.send_command(f"^ping{self.ping_counter:d}", to_host=True)
            self.ping_counter += 1
            await asyncio.sleep(self.ping_timeout)

    async def process_message(self, message: str) -> None:
        """Is called when a new text message is received from the PCHK server.

        This class should be reimplemented in any subclass which evaluates
        received messages.

        :param    str    input:    Input text message
        """
        await super().process_message(message)
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
                    module_conn = self.get_module_conn(logical_source_addr)
                    if isinstance(inp, inputs.ModSn):
                        # used to extend scan_modules() timeout
                        if self.module_serial_number_received.locked():
                            self.module_serial_number_received.release()

                    await module_conn.async_process_input(inp)

            # Forward all known inputs to callback listeners.
            for input_callback in self.input_callbacks:
                input_callback(inp)

    async def cancel_requests(self) -> None:
        """Cancel all TimeoutRetryHandlers."""
        cancel_coros = [
            address_conn.cancel_requests()
            for address_conn in self.address_conns.values()
            if isinstance(address_conn, ModuleConnection)
        ]

        if cancel_coros:
            await asyncio.wait(cancel_coros)

    def register_for_inputs(
        self, callback: Callable[[inputs.Input], None]
    ) -> Callable[..., None]:
        """Register a function for callback on PCK message received.

        Returns a function to unregister the callback.
        """
        self.input_callbacks.add(callback)
        return lambda callback=callback: self.input_callbacks.remove(callback)

    def set_event_handler(self, coro: Callable[[str], Awaitable[None]]) -> None:
        """Set the event handler for specific LCN events."""
        if coro is None:
            self.event_handler = self.default_event_handler
        else:
            self.event_handler = coro

    async def default_event_handler(self, event: str) -> None:
        """Handle events for specific LCN events."""
        if event == "lcn-connected":
            pass
        elif event == "lcn-disconnected":
            pass
        elif event == "lcn-connection-status-changed":
            pass
        elif event == "connection-lost":
            pass
