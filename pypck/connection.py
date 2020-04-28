"""Copyright (c) 2006-2018 by the respective copyright holders.

All rights reserved. This program and the accompanying materials
are made available under the terms of the Eclipse Public License v1.0
which accompanies this distribution, and is available at
http://www.eclipse.org/legal/epl-v10.html

Contributors:
  Andre Lengwenus - port to Python and further improvements
  Tobias Juettner - initial LCN binding for openHAB (Java)
"""

import asyncio
import logging

from pypck import inputs, lcn_defs
from pypck.lcn_addr import LcnAddr
from pypck.module import GroupConnection, ModuleConnection
from pypck.pck_commands import PckGenerator
from pypck.timeout_retry import DEFAULT_TIMEOUT_MSEC, TimeoutRetryHandler

_LOGGER = logging.getLogger(__name__)

READ_TIMEOUT = -1
SOCKET_CLOSED = -2


async def cancel(task):
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


class PchkLicenseError(Exception):
    def __init__(self, message=None):
        if message is None:
            message = ('Maximum number of connections was reached. An '
                       'additional license key is required.')
        super().__init__(message)


class PchkAuthenticationError(Exception):
    def __init__(self, message=None):
        if message is None:
            message = ('Authentication failed.')
        super().__init__(message)


class PchkLcnNotConnectedError(Exception):
    def __init__(self, message=None):
        if message is None:
            message = ('LCN not connected.')
        super().__init__(message)


class PchkConnection():
    """Socket connection to LCN-PCHK server.

    :param           loop:        Asyncio event loop
    :param    str    server_addr: Server IP address formatted as
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

    def __init__(self, loop, server_addr, port, connection_id='PCHK'):
        """Construct PchkConnection."""
        self.loop = loop
        self.server_addr = server_addr
        self.port = port
        self.connection_id = connection_id

    async def async_connect(self):
        self.reader, self.writer = await asyncio.open_connection(
            self.server_addr, self.port)

        address = self.writer.get_extra_info('peername')
        _LOGGER.debug('{} server connected at {}:{}'.format(
            self.connection_id, *address))

        # main read loop
        self.read_data_loop_task = self.loop.create_task(self.read_data_loop())

    def connect(self):
        self.loop.create_task(self.async_connect())

    async def read_data_loop(self):
        """Is called when some data is received."""
        while not self.writer.is_closing():
            try:
                data = await self.reader.readuntil(
                    PckGenerator.TERMINATION.encode())
            except asyncio.IncompleteReadError:
                _LOGGER.debug('Connection to {} lost'.format(
                    self.connection_id))
                await self.async_close()
                return

            message = data.decode().split(PckGenerator.TERMINATION)[0]
            self.loop.create_task(self.process_message(message))

    def send_command(self, pck, **kwargs):
        self.loop.create_task(self.async_send_command(pck, **kwargs))

    async def async_send_command(self, pck):
        """Send a PCK command to the PCHK server.

        :param    str    pck:    PCK command
        """
        _LOGGER.debug('to {}: {}'.format(self.connection_id, pck))
        self.writer.write((pck + PckGenerator.TERMINATION).encode())
        await self.writer.drain()

    async def process_message(self, message):
        """Is called when a new text message is received from the PCHK server.

        This class should be reimplemented in any subclass which evaluates
        recieved messages.

        :param    str    input:    Input text message
        """
        _LOGGER.debug('from {}: {}'.format(self.connection_id, message))

    async def async_close(self):
        """Close the active connection."""
        await cancel(self.read_data_loop_task)
        self.writer.close()
        await self.writer.wait_closed()


class PchkConnectionManager(PchkConnection):
    """Connection to LCN-PCHK.

    Has the following tasks:
    - Initiates login procedure.
    - Ping PCHK.
    - Parse incoming commands and create input objects.
    - Calls input object's process method.
    - Updates seg_id of ModuleConnections if segment scan finishes.

    :param           loop:        Asyncio event loop
    :param    str    server_addr: Server IP address formatted as
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
    >>> connection.connect()
    >>> loop.run_forever()
    >>> loop.close()
    """

    def __init__(self, loop, server_addr, port, username, password,
                 settings=None, connection_id='PCHK'):
        """Construct PchkConnectionManager."""
        super().__init__(loop, server_addr, port, connection_id)

        self.username = username
        self.password = password

        if settings is None:
            settings = {}
        self.settings = lcn_defs.default_connection_settings
        self.settings.update(settings)

        self.ping_interval = 60 * 10  # seconds
        self.ping_counter = 0

        self.dim_mode = self.settings['DIM_MODE']
        self.status_mode = lcn_defs.OutputPortStatusMode.PERCENT

        self.is_lcn_connected = False
        self.local_seg_id = 0

        # Events
        self.segment_scan_completed_event = asyncio.Event()

        # Futures (for connection procedure and exception handling)
        self.license_error_future = asyncio.Future()
        self.authentication_completed_future = asyncio.Future()
        self.lcn_connected_on_login_future = asyncio.Future()

        # All modules/groups from or to a communication occurs are represented
        # by a unique ModuleConnection or GroupConnection object.
        # All ModuleConnection and GroupConnection objects are stored in this
        # dictionary.
        self.address_conns = {}
        self.segment_coupler_ids = []

    async def async_send_command(self, pck, to_host=False):
        if not self.is_lcn_connected and not to_host:
            return
        await super().async_send_command(pck)

    async def on_auth(self, success):
        """Is called after successful authentication."""
        if success:
            _LOGGER.debug('{} authorization successful!'.format(
                self.connection_id))
            self.authentication_completed_future.set_result(True)
            await self.async_send_command(PckGenerator.set_operation_mode(
                self.dim_mode, self.status_mode), to_host=True)
            self.ping_task = self.loop.create_task(self.ping())
        else:
            _LOGGER.debug('{} authorization failed!'.format(
                self.connection_id))
            self.authentication_completed_future.set_exception(
                PchkAuthenticationError)

    def on_license_error(self):
        """Is called if a license error occurs during connection."""
        _LOGGER.debug('{}: License Error.'.format(self.connection_id))
        self.license_error_future.set_exception(PchkLicenseError())

    def on_successful_login(self):
        """Is called after connection to LCN bus system is established."""
        _LOGGER.debug('{} login successful.'.format(self.connection_id))

    async def lcn_connection_status_changed(self, is_lcn_connected):
        """Set the current connection state to the LCN bus.

        :param    bool    is_lcn_connected: Current connection status
        """
        self.is_lcn_connected = is_lcn_connected
        # only touch future the first time connection status changes (login)
        if not self.lcn_connected_on_login_future.done():
            if is_lcn_connected:
                self.lcn_connected_on_login_future.set_result(True)
            else:
                self.lcn_connected_on_login_future.set_exception(
                    PchkLcnNotConnectedError)

    async def async_connect(self, timeout=30):
        """Establish a connection to PCHK at the given socket.

        Ensures that the LCN bus is present and authorizes at PCHK.
        Raise a :class:`TimeoutError`, if connection could not be established
        within the given timeout.

        :param    int    timeout:    Timeout in seconds
        """
        done, pending = await asyncio.wait(
            [super().async_connect(),
             self.authentication_completed_future,
             self.license_error_future,
             self.lcn_connected_on_login_future
             ],
            timeout=timeout,
            return_when=asyncio.FIRST_EXCEPTION)

        # check if authentication successful
        if (self.authentication_completed_future.done() and
                self.authentication_completed_future.exception()):
            raise self.authentication_completed_future.exception()

        # check if license error occured
        if (self.license_error_future.done() and
                self.license_error_future.exception()):
            raise self.license_error_future.exception()

        # wait for lcn bus connected
        if (self.lcn_connected_on_login_future.done() and
                self.lcn_connected_on_login_future.exception()):
            raise self.lcn_connected_on_login_future.exception()

        if pending:
            for task in pending:
                task.cancel()
            raise TimeoutError('Timeout error while connecting to {}.'
                               .format(self.connection_id))

        # start segment scan
        await self.scan_segment_couplers(
            self.settings['SK_NUM_TRIES'], DEFAULT_TIMEOUT_MSEC)

    async def async_close(self):
        """Close the active connection."""
        await super().async_close()
        await cancel(self.ping_task)
        await self.cancel_requests()
        _LOGGER.debug('Connection to {} closed.'.format(self.connection_id))

    def set_local_seg_id(self, local_seg_id):
        """Set the local segment id.

        :param    int    local_seg_id:    The local segment_id.
        """
        old_local_seg_id = self.local_seg_id

        self.local_seg_id = local_seg_id
        # replace all address_conns with current local_seg_id with new
        # local_seg_id
        for addr in list(self.address_conns):
            if addr.get_seg_id() == old_local_seg_id:
                address_conn = self.address_conns.pop(addr)
                address_conn.seg_id = self.local_seg_id
                self.address_conns[LcnAddr(self.local_seg_id, addr.get_id(),
                                           addr.is_group())] = address_conn

    def physical_to_logical(self, addr):
        """Convert the physical segment id of an address to the logical one.

        :param    addr:    The module's/group's address
        :type     addr:    :class:`~LcnAddrMod` or :class:`~LcnAddrGrp`

        :returns:    The module's/group's address
        :rtype:      :class:`~LcnAddrMod` or :class:`~LcnAddrGrp`
        """
        return LcnAddr(self.local_seg_id if addr.get_seg_id() == 0
                       else addr.get_seg_id(), addr.get_id(), addr.is_group())

    def is_ready(self):
        """Retrieve the overall connection state.

        Nothing should be sent before this is signaled.

        :returns:    True if everything is set-up, False otherwise
        :rtype:      bool
        """
        return self.segment_scan_completed_event.is_set()

    def get_address_conn(self, addr):
        """Create and/or return the given LCN module or group.

        The LCN module/group object is used for further communication
        with the module/group (e.g. sending commands).

        :param    addr:    The module's/group's address
        :type     addr:    :class:`~LcnAddrMod` or :class:`~LcnAddrGrp`

        :returns: The address connection object (never null)
        :rtype: `~ModuleConnection` or `~GroupConnection`

        :Example:

        >>> address = LcnAddr(0, 7, False)
        >>> module = pchk_connection.get_address_conn(address)
        >>> module.toggle_output(0, 5)
        """
        if addr.get_seg_id() == 0 and self.local_seg_id != -1:
            addr.seg_id = self.local_seg_id
        address_conn = self.address_conns.get(addr, None)
        if address_conn is None:
            if addr.is_group():
                address_conn = GroupConnection(self.loop, self, addr.seg_id,
                                               addr.addr_id)
            else:
                address_conn = ModuleConnection(self.loop, self, addr.seg_id,
                                                addr.addr_id)

            self.address_conns[addr] = address_conn

        return address_conn

    async def scan_modules(self, num_tries=3, timeout_msec=1500):
        segment_coupler_ids = self.segment_coupler_ids \
                              if self.segment_coupler_ids else [0]
        for idx in range(num_tries):
            if idx:
                await asyncio.sleep(timeout_msec / 1000)
            for segment_id in segment_coupler_ids:
                if segment_id == self.local_seg_id:
                    segment_id = 0
                await self.async_send_command(
                    '>G{:03d}003!LEER'.format(segment_id))

    async def scan_segment_couplers(self, num_tries=3, timeout_msec=1500):
        if not self.is_lcn_connected:
            raise PchkLcnNotConnectedError()
        for idx in range(num_tries):
            await self.async_send_command(
                PckGenerator.generate_address_header(
                    LcnAddr(3, 3, True), self.local_seg_id, False) +
                PckGenerator.segment_coupler_scan())
            await asyncio.sleep(timeout_msec/1000)

        # No segment coupler expected (num_tries=0)
        if len(self.segment_coupler_ids) == 0:
            _LOGGER.debug('{}: No segment coupler found.'.format(
                self.connection_id))

        self.segment_scan_completed_event.set()

    async def ping(self):
        '''Send pings'''
        while not self.writer.is_closing():
            await self.async_send_command(
                '^ping{:d}'.format(self.ping_counter), to_host=True)
            self.ping_counter += 1
            await asyncio.sleep(self.settings['PING_TIMEOUT'])

    async def process_message(self, message):
        """Is called when a new text message is received from the PCHK server.

        This class should be reimplemented in any subclass which evaluates
        recieved messages.

        :param    str    input:    Input text message
        """
        await super().process_message(message)
        inps = inputs.InputParser.parse(message)

        for inp in inps:
            await self.async_process_input(inp)

    async def async_process_input(self, inp):
        """Process an input command."""
        # Inputs from Host
        if isinstance(inp, inputs.AuthUsername):
            await self.async_send_command(self.username, to_host=True)
        elif isinstance(inp, inputs.AuthPassword):
            await self.async_send_command(self.password, to_host=True)
        elif isinstance(inp, inputs.AuthOk):
            await self.on_auth(True)
        elif isinstance(inp, inputs.AuthFailed):
            await self.on_auth(False)
        elif isinstance(inp, inputs.LcnConnState):
            self.license_error_future.set_result(True)
            if inp.is_lcn_connected:
                _LOGGER.debug(
                    '{}: LCN is connected.'.format(self.connection_id))
                await self.lcn_connection_status_changed(True)
                self.on_successful_login()
            else:
                _LOGGER.debug(
                    '{}: LCN is not connected.'.format(self.connection_id))
                await self.lcn_connection_status_changed(False)
        elif isinstance(inp, inputs.LicenseError):
            self.on_license_error()
        elif isinstance(inp, inputs.CommandError):
            _LOGGER.debug('LCN command error: %s', inp.message)
            for address_conn in self.address_conns.values():
                if not address_conn.is_group():
                    if address_conn.pck_commands_with_ack:
                        address_conn.pck_commands_with_ack.popleft()
                    self.loop.create_task(
                        address_conn.request_curr_pck_command_with_ack.
                        cancel())
        elif isinstance(inp, inputs.ModSk):
            if inp.physical_source_addr.seg_id == 0:
                self.set_local_seg_id(inp.reported_seg_id)
            # store reported segment coupler id
            if inp.reported_seg_id not in self.segment_coupler_ids:
                self.segment_coupler_ids.append(inp.reported_seg_id)
        elif isinstance(inp, inputs.Unknown):
            return

        # Inputs from bus
        elif self.is_ready():
            inp.logical_source_addr = self.physical_to_logical(
                inp.physical_source_addr)
            module_conn = self.get_address_conn(inp.logical_source_addr)
            if isinstance(inp, inputs.ModAck):
                # Skip if we don't have all necessary bus info yet
                self.loop.create_task(module_conn.on_ack(
                    inp.code, DEFAULT_TIMEOUT_MSEC))
            elif isinstance(inp,
                            (inputs.ModStatusOutput,
                             inputs.ModStatusRelays,
                             inputs.ModStatusBinSensors,
                             inputs.ModStatusLedsAndLogicOps,
                             inputs.ModStatusKeyLocks)):
                # Skip if we don't have all necessary bus info yet
                await module_conn.async_process_input(inp)
            elif isinstance(inp, inputs.ModStatusVar):
                # Skip if we don't have all necessary bus info yet
                module_conn = self.get_address_conn(inp.logical_source_addr)
                if inp.orig_var == lcn_defs.Var.UNKNOWN:
                    inp.var = module_conn.\
                        get_last_requested_var_without_type_in_response()
                else:
                    inp.var = inp.orig_var

                if inp.var != lcn_defs.Var.UNKNOWN:
                    if module_conn.\
                        get_last_requested_var_without_type_in_response() == \
                            inp.var:
                        module_conn.\
                            set_last_requested_var_without_type_in_response(
                                lcn_defs.Var.UNKNOWN)  # Reset
                await module_conn.async_process_input(inp)
            else:
                await module_conn.async_process_input(inp)

    async def cancel_requests(self):
        """Cancel all TimeoutRetryHandlers."""
        cancel_coros = \
            [address_conn.cancel_requests()
             for address_conn in self.address_conns.values()
             if not address_conn.is_group()]

        if cancel_coros:
            await asyncio.wait(cancel_coros)
