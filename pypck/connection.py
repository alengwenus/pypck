'''
Copyright (c) 2006-2018 by the respective copyright holders.

All rights reserved. This program and the accompanying materials
are made available under the terms of the Eclipse Public License v1.0
which accompanies this distribution, and is available at
http://www.eclipse.org/legal/epl-v10.html

Contributors:
  Andre Lengwenus - port to Python and further improvements
  Tobias Juettner - initial LCN binding for openHAB (Java)
'''

import logging

import asyncio
from pypck import lcn_defs
from pypck.inputs import InputParser
from pypck.lcn_addr import LcnAddr
from pypck.module import GroupConnection, ModuleConnection
from pypck.pck_commands import PckGenerator
from pypck.timeout_retry import TimeoutRetryHandler

_LOGGER = logging.getLogger(__name__)


class PchkConnection(asyncio.Protocol):
    """Provides a socket connection to LCN-PCHK server.

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
        """Constructor.
        """
        self.loop = loop
        self.server_addr = server_addr
        self.port = port
        self.connection_id = connection_id
        self.client = None
        self.transport = None
        self.address = None

        self.buffer = b''

    def connect(self):
        """Establish a connection to PCHK at the given socket.
        """
        coro = self.loop.create_connection(lambda: self, self.server_addr,
                                           self.port)
        self.client = self.loop.create_task(coro)

    def connection_made(self, transport):
        self.transport = transport
        self.address = transport.get_extra_info('peername')
        _LOGGER.debug('{} server connected at {}:{}'.format(
            self.connection_id, *self.address))

    def connection_lost(self, exc):
        self.transport = None
        if exc:
            _LOGGER.error('Error')
        else:
            _LOGGER.debug('{} connection lost.'.format(self.connection_id))
        super().connection_lost(exc)

    @property
    def is_socket_connected(self):
        """Connection status to PCHK.

        :return:       Connection status to PCHK.
        :rtype:        bool
        """
        return self.transport is not None

    def data_received(self, data):
        self.buffer += data
        data_chunks = self.buffer.split(PckGenerator.TERMINATION.encode())
        self.buffer = data_chunks.pop()

        for data_chunk in data_chunks:
            self.process_message(data_chunk.decode())

    def send_command(self, pck):
        """Sends a PCK command to the PCHK server.

        :param    str    pck:    PCK command
        """
        self.loop.create_task(self.send_command_async(pck))

    async def send_command_async(self, pck):
        """Coroutine: Sends a PCK command to the PCHK server.

        :param    str    pck:    PCK command
        """
        _LOGGER.debug('to {}: {}'.format(self.connection_id, pck))
        self.transport.write((pck + PckGenerator.TERMINATION).encode())

    def process_message(self, message):
        """Is called if a new text message is received from the PCHK server.
        This class should be reimplemented in any subclass which evaluates
        recieved messages.

        :param    str    input:    Input text message
        """

    def close(self):
        """Closes the active connection.
        """
        if self.transport is not None:
            self.transport.close()


class PchkConnectionManager(PchkConnection):
    """Has the following tasks:
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
        """Constructor.
        """
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

        self._is_lcn_connected = False
        self.local_seg_id = -1

        # Futures for connection status handling.
        self.socket_connected = self.loop.create_future()
        self.lcn_connected = self.loop.create_future()
        self.segment_scan_completed = self.loop.create_future()

        # All modules/groups from or to a communication occurs are represented
        # by a unique ModuleConnection or GroupConnection object.
        # All ModuleConnection and GroupConnection objects are stored in this
        # dictionary.
        self.address_conns = {}

        self.status_segment_scan = \
            TimeoutRetryHandler(loop, self.settings['SK_NUM_TRIES'])
        self.ping = TimeoutRetryHandler(loop, -1,
                                        self.settings['PING_TIMEOUT'])
        self.ping.set_timeout_callback(self.ping_timeout)

    def connection_made(self, transport):
        super().connection_made(transport)
        self.socket_connected.set_result(True)

    def connection_lost(self, exc):
        super().connection_lost(exc)

        self.status_segment_scan.cancel()
        self.ping.cancel()
        for module_conn in self.address_conns.values():
            module_conn.cancel_timeout_retries()

    def on_successful_login(self):
        """Is called after connection to LCN bus system is established.
        """
        _LOGGER.debug('{} login successful.'.format(self.connection_id))
        self.set_lcn_connected(True)
        self.ping.activate()

    def on_auth_ok(self):
        """Is called after successful authentication.
        """
        _LOGGER.debug('{} authorization successful!'.format(
            self.connection_id))

    def get_lcn_connected(self):
        """Connection status to the LCN bus.

        :return:       Connection status to LCN bus.
        :rtype:        bool
        """
        return self.lcn_connected.done()

    def set_lcn_connected(self, is_lcn_connected):
        """
        Sets the current connection state to the LCN bus.

        :param    bool    is_lcn_connected: Current connection status
        """
        # self._is_lcn_connected = is_lcn_connected
        if is_lcn_connected:
            self.lcn_connected.set_result(True)
            self.status_segment_scan.activate(self.segment_scan_timeout)
        else:
            # Repeat segment scan on next connect
            self.local_seg_id = -1
            self.status_segment_scan.cancel()
            # While we are disconnected we will miss all status messages.
            # Clearing our runtime data will give us a fresh start.
            self.address_conns.clear()

    async def async_connect(self, timeout=30):
        """Establishes a connection to PCHK at the given socket, ensures that
        the LCN bus is present and authorizes at PCHK.
        Raises a :class:`TimeoutError`, if connection could not be established
        within the given timeout.

        :param    int    timeout:    Timeout in seconds
        """
        self.connect()
        done_pending = await asyncio.wait([self.socket_connected,
                                           self.lcn_connected,
                                           self.segment_scan_completed],
                                          timeout=timeout)
        pending = done_pending[1]
        if pending:
            raise TimeoutError('No server listening. Aborting.')

    def set_local_seg_id(self, local_seg_id):
        """Sets the local segment id.

        :param    int    local_seg_id:    The local segment_id.
        """
        old_local_seg_id = self.local_seg_id

        self.local_seg_id = local_seg_id
        # replace all address_conns with current local_seg_id with new
        # local_seg_id
        for addr in list(self.address_conns):
            if addr.seg_id in [0, old_local_seg_id]:
                address_conn = self.address_conns.pop(addr)
                address_conn.seg_id = self.local_seg_id
                self.address_conns[LcnAddr(self.local_seg_id, addr.id,
                                           addr.is_group())] = address_conn

        if not self.segment_scan_completed.done():
            self.segment_scan_completed.set_result(True)

    def physical_to_logical(self, addr):
        """Converts the physical segment id of an address to the logical one.

        :param    addr:    The module's/group's address
        :type     addr:    :class:`~LcnAddrMod` or :class:`~LcnAddrGrp`

        :returns:    The module's/group's address
        :rtype:      :class:`~LcnAddrMod` or :class:`~LcnAddrGrp`
        """
        return LcnAddr(self.local_seg_id if addr.get_seg_id() == 0
                       else addr.get_seg_id(), addr.get_id(), addr.is_group())

    def is_ready(self):
        """Retrieves the overall connection state.
        Nothing should be sent before this is signaled.

        :returns:    True if everything is set-up, False otherwise
        :rtype:      bool
        """
        return self.socket_connected.done() and self.lcn_connected.done()\
            and self.segment_scan_completed.done()

    def get_address_conn(self, addr):
        """Creates and/or returns cached data for the given LCN module or
        group. The LCN module/group object is used for further communication
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

    def segment_scan_timeout(self, failed):
        """Gets called if no response from segment coupler was received.

        :param    bool    failed:    True if caller failed to fulfill request
                                     otherwise False
        """
        if failed:
            _LOGGER.debug('{}: No segment coupler found.'.format(
                self.connection_id))
            self.set_local_seg_id(0)
        else:
            self.send_command(PckGenerator.generate_address_header(
                LcnAddr(3, 3, True), self.local_seg_id, False) +
                              PckGenerator.segment_coupler_scan())

    def ping_timeout(self, failed):
        """Send a ping command to keep the connection to LCN-PCHK alive.
        (default is every 10 minutes)"""
        self.send_command('^ping{:d}'.format(self.ping_counter))
        self.ping_counter += 1

    def process_message(self, message):
        _LOGGER.debug('from {}: {}'.format(self.connection_id, message))
        commands = InputParser.parse(message)
        for command in commands:
            command.process(self)

    async def close(self):
        for address_conn in self.address_conns.values():
            if isinstance(address_conn, ModuleConnection):
                await address_conn.cancel_timeout_retries()
        await self.ping.cancel()
        await self.status_segment_scan.cancel()
        super().close()
