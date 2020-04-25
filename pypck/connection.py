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


class PchkLicenseError(Exception):
    def __init__(self, message=None):
        if message is None:
            message = ('Maximum number of onnections was reached. An '
                       'additional license key is required.')
        super().__init__(message)

class PchkConnection(asyncio.Protocol):
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
        self.client = None
        self.transport = None
        self.address = None

        self.buffer = b''

    def connect(self):
        """Establish a connection to PCHK at the given socket."""
        coro = self.loop.create_connection(lambda: self, self.server_addr,
                                           self.port)
        self.client = self.loop.create_task(coro)

    def connection_made(self, transport):
        """Is called when a connection is made."""
        self.transport = transport
        self.address = transport.get_extra_info('peername')
        _LOGGER.debug('{} server connected at {}:{}'.format(
            self.connection_id, *self.address))

    def connection_lost(self, exc):
        """Is called when the connection is lost or closed."""
        self.transport = None
        if exc:
            _LOGGER.error('Error')
        else:
            _LOGGER.debug('{} connection lost.'.format(self.connection_id))
        super().connection_lost(exc)

    @property
    def is_socket_connected(self):
        """Get the connection status to PCHK.

        :return:       Connection status to PCHK.
        :rtype:        bool
        """
        return self.transport is not None

    def data_received(self, data):
        """Is called when some data is received."""
        self.buffer += data
        data_chunks = self.buffer.split(PckGenerator.TERMINATION.encode())
        self.buffer = data_chunks.pop()

        for data_chunk in data_chunks:
            self.process_message(data_chunk.decode())

    def send_command(self, pck):
        """Send a PCK command to the PCHK server.

        :param    str    pck:    PCK command
        """
        self.loop.create_task(self.send_command_async(pck))

    async def send_command_async(self, pck):
        """Send a PCK command to the PCHK server.

        :param    str    pck:    PCK command
        """
        _LOGGER.debug('to {}: {}'.format(self.connection_id, pck))
        self.transport.write((pck + PckGenerator.TERMINATION).encode())

    def process_message(self, message):
        """Is called when a new text message is received from the PCHK server.

        This class should be reimplemented in any subclass which evaluates
        recieved messages.

        :param    str    input:    Input text message
        """

    def close(self):
        """Close the active connection."""
        if self.transport is not None:
            self.transport.close()


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

        # self.dim_mode = lcn_defs.OutputPortDimMode.STEPS50
        self.dim_mode = self.settings['DIM_MODE']
        self.status_mode = lcn_defs.OutputPortStatusMode.PERCENT

        self.is_lcn_connected = False
        self.local_seg_id = -1

        # Futures for connection status handling.
        self.socket_connected = self.loop.create_future()
        self.lcn_connected = self.loop.create_future()
        self.license_status = self.loop.create_future()
        self.segment_scan_completed = self.loop.create_future()

        # All modules/groups from or to a communication occurs are represented
        # by a unique ModuleConnection or GroupConnection object.
        # All ModuleConnection and GroupConnection objects are stored in this
        # dictionary.
        self.address_conns = {}
        self.segment_coupler_ids = []

        # self.status_segment_scan = \
        #     TimeoutRetryHandler(loop, self.settings['SK_NUM_TRIES'])
        # self.status_segment_scan.set_timeout_callback(
        #     self.segment_scan_timeout)

        self.ping = TimeoutRetryHandler(loop, -1,
                                        self.settings['PING_TIMEOUT'])
        self.ping.set_timeout_callback(self.ping_timeout)

    def connection_made(self, transport):
        """Is called when a connection is made."""
        super().connection_made(transport)
        self.socket_connected.set_result(True)

    def connection_lost(self, exc):
        """Is called when the connection is lost or closed."""
        super().connection_lost(exc)
        if exc is not None:  # Connection closed by other side
            self.loop.create_task(self.cancel_timeout_retries())

    def send_command(self, pck, to_host=False):
        if not self.is_lcn_connected and not to_host:
            return

        super().send_command(pck)

    def on_successful_login(self):
        """Is called after connection to LCN bus system is established."""
        _LOGGER.debug('{} login successful.'.format(self.connection_id))
        self.send_command(PckGenerator.set_operation_mode(
            self.dim_mode, self.status_mode), to_host=True)
        self.ping.activate()

    def on_license_error(self):
        """Is called if a license error occurs during connection."""
        _LOGGER.debug('{}: License Error.'.format(self.connection_id))
        self.license_status.set_exception(PchkLicenseError)

    def on_auth_ok(self):
        """Is called after successful authentication."""
        _LOGGER.debug('{} authorization successful!'.format(
            self.connection_id))

    def get_lcn_connected(self):
        """Get the connection status to the LCN bus.

        :return:       Connection status to LCN bus.
        :rtype:        bool
        """
        #return self.lcn_connected.done()
        return self.is_lcn_connected

    def set_lcn_connected(self, is_lcn_connected):
        """Set the current connection state to the LCN bus.

        :param    bool    is_lcn_connected: Current connection status
        """
        self.is_lcn_connected = is_lcn_connected
        if is_lcn_connected and not self.lcn_connected.done():
            self.license_status.set_result(True)
            self.lcn_connected.set_result(True)
            self.loop.create_task(
                self.scan_segment_couplers(self.settings['SK_NUM_TRIES'],
                                           DEFAULT_TIMEOUT_MSEC))
            return

        # else:
        #     # TODO:
        #     # Repeat segment scan on next connect
        #     self.local_seg_id = -1
        #     self.status_segment_scan.cancel()
        #     # While we are disconnected we will miss all status messages.
        #     # Clearing our runtime data will give us a fresh start.
        #     self.address_conns.clear()

    async def async_connect(self, timeout=30):
        """Establish a connection to PCHK at the given socket.

        Ensures that the LCN bus is present and authorizes at PCHK.
        Raise a :class:`TimeoutError`, if connection could not be established
        within the given timeout.

        :param    int    timeout:    Timeout in seconds
        """
        self.connect()
        done_pending = await asyncio.wait([self.socket_connected,
                                           self.lcn_connected,
                                           self.license_status,
                                           self.segment_scan_completed],
                                          timeout=timeout,
                                          return_when=asyncio.FIRST_EXCEPTION)

        if self.license_status.exception():
            raise self.license_status.exception()

        pending = done_pending[1]
        if pending:
            raise TimeoutError('No server listening. Aborting.')

    async def async_close(self):
        """Close the active connection."""
        super().close()
        await self.cancel_timeout_retries()

    def set_local_seg_id(self, local_seg_id):
        """Set the local segment id.

        :param    int    local_seg_id:    The local segment_id.
        """
        old_local_seg_id = self.local_seg_id

        self.local_seg_id = local_seg_id
        # replace all address_conns with current local_seg_id with new
        # local_seg_id
        for addr in list(self.address_conns):
            if addr.get_seg_id() in [0, old_local_seg_id]:
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
        return (self.socket_connected.done() and
                self.lcn_connected.done() and
                self.license_status.done() and
                self.segment_scan_completed.done())

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
        await self.segment_scan_completed
        for idx in range(num_tries):
            if idx:
                await asyncio.sleep(timeout_msec / 1000)
            for segment_id in self.segment_coupler_ids:
                if segment_id == self.local_seg_id:
                    segment_id = 0
                self.loop.create_task(self.send_command_async(
                    '>G{:03d}003!LEER'.format(segment_id)))

    async def scan_segment_couplers(self, num_tries=3, timeout_msec=1500):
        await self.lcn_connected
        for idx in range(num_tries):
            self.send_command(PckGenerator.generate_address_header(
                LcnAddr(3, 3, True), self.local_seg_id, False) +
                            PckGenerator.segment_coupler_scan())
            await asyncio.sleep(timeout_msec/1000)

        # No segment coupler expected (num_tries=0)
        if len(self.segment_coupler_ids) == 0 and self.local_seg_id == -1:
            _LOGGER.debug('{}: No segment coupler found.'.format(
                self.connection_id))
            self.segment_coupler_ids.append(0)
            self.set_local_seg_id(0)

        if not self.segment_scan_completed.done():
            self.segment_scan_completed.set_result(True)

    def ping_timeout(self, failed):
        """Send a ping command to keep the connection to LCN-PCHK alive.

        Default is every 10 minutes.
        """
        self.send_command('^ping{:d}'.format(self.ping_counter), to_host=True)
        self.ping_counter += 1

    def process_message(self, message):
        """Is called when a new text message is received from the PCHK server.

        This class should be reimplemented in any subclass which evaluates
        recieved messages.

        :param    str    input:    Input text message
        """
        _LOGGER.debug('from {}: {}'.format(self.connection_id, message))
        inps = inputs.InputParser.parse(message)

        for inp in inps:
            self.process_input(inp)

    def process_input(self, inp):
        self.loop.create_task(self.async_process_input(inp))

    async def async_process_input(self, inp):
        """Process an input command."""
        # Inputs from Host
        if isinstance(inp, inputs.AuthUsername):
            self.send_command(self.username, to_host=True)
        elif isinstance(inp, inputs.AuthPassword):
            self.send_command(self.password, to_host=True)
        elif isinstance(inp, inputs.AuthOk):
            self.on_auth_ok()
        elif isinstance(inp, inputs.LcnConnState):
            if inp.is_lcn_connected:
                _LOGGER.debug(
                    '{}: LCN is connected.'.format(self.connection_id))
                self.set_lcn_connected(True)
                self.on_successful_login()
            else:
                _LOGGER.debug(
                    '{}: LCN is not connected.'.format(self.connection_id))
                self.set_lcn_connected(False)
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
                module_conn.process_input(inp)
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
                module_conn.process_input(inp)
            else:
                module_conn.process_input(inp)

    async def cancel_timeout_retries(self):
        """Cancel all TimeoutRetryHandlers."""
        cancel_coros = [self.ping.cancel()] + \
            [address_conn.cancel_timeout_retries()
             for address_conn in self.address_conns.values()]

        await asyncio.wait(cancel_coros)
