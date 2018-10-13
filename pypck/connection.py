import asyncio
import logging
 
from pypck.pck_commands import PckGenerator
from pypck import lcn_defs
from pypck.input import InputParser
from pypck.lcn_addr import LcnAddrMod, LcnAddrGrp
from pypck.module import ModuleConnection
from pypck.timeout_retry import TimeoutRetryHandler


class PchkConnection(asyncio.Protocol):
    """Provides a socket connection to LCN-PCHK server.
    
    :param           loop:        Asyncio event loop
    :param    str    server_addr: Server IP address formatted as xxx.xxx.xxx.xxx
    :param    int    port:        Server port
    
    :Note:
    
    :class:`PchkConnection` does only open a port to the
    PCHK server and allows to send and receive plain text. Use
    :func:`~PchkConnection.send_command` and :func:`~PchkConnection.process_input`
    callback to send and receive text messages. 
    
    For login logic or communication with modules use
    :class:`~PchkConnectionManager`.
    """
    def __init__(self, loop, server_addr, port):
        '''Constructor.
        '''
        self.logger = logging.getLogger(self.__class__.__name__)
        self.loop = loop
        self.server_addr = server_addr
        self.port = port
        self.transport = None
 
        self.buffer = b''
   
    def connect(self):
        """Establish a connection to PCHK at the given socket.
        """
        coro = self.loop.create_connection(lambda: self, self.server_addr, self.port)
        self.client = self.loop.create_task(coro)
       
    def connection_made(self, transport):
        self.transport = transport
        self.address = transport.get_extra_info('peername')
        self.logger.info('PCHK server connected at {}:{}'.format(*self.address))
   
    def connection_lost(self, error):
        self.transport = None
        if error:
            self.logger.info('Error')
        else:
            self.logger.info('Connection lost.')
        super().connection_lost(error)
   
    @property
    def is_socket_connected(self):
        """Connection status to PCHK.
        
        :return:       Connection status to PCHK.
        :rtype:        bool
        """
        return self.transport != None
   
    def data_received(self, data):
        self.buffer += data
        inputs = self.buffer.split(PckGenerator.TERMINATION.encode())
        self.buffer = inputs.pop()
 
        for input in inputs:
            self.process_input(input.decode())
   
    def send_command(self, pck):
        """Sends a PCK command to the PCHK server.
        
        :param    str    pck:    PCK command
        """        
        self.loop.create_task(self.send_command_async(pck))
   
    async def send_command_async(self, pck):
        """Coroutine: Sends a PCK command to the PCHK server.
        
        :param    str    pck:    PCK command
        """
        self.logger.info('to PCHK: {}'.format(pck))
        self.transport.write((pck + PckGenerator.TERMINATION).encode())
   
    def process_input(self, input_text):
        """Is called if a new text message is received from the PCHK server.
        Thias class should be reimplemented in any subclass which evaluates recieved
        messages.
        
        :param    str    input:    Input text message
        """
        pass
 
    def close(self):
        """Closes the active connection.
        """
        if self.transport != None:
            self.transport.close()
 
 
class PchkConnectionManager(PchkConnection):
    """Has the following tasks:
    - Initiates login procedure.
    - Ping PCHK.
    - Parse incoming commands and create input objects.
    - Calls input object's process method.
    - Updates seg_id of ModuleConnections if segment scan finishes. 
    
    :param           loop:        Asyncio event loop
    :param    str    server_addr: Server IP address formatted as xxx.xxx.xxx.xxx
    :param    int    port:        Server port
    :param    str    username:    usernam for login.
    :param    str    password:    Password for login.
    
    An example how to setup a proper connection to PCHK including login and
    (automatic) segment coupler scan is shown below.
    
    :Example:
    
    >>> import asyncio
    >>> loop = asyncio.get_event_loop()
    >>> connection = PchkConnectionManager(loop, '10.1.2.3', 4114, 'lcn', 'lcn')
    >>> connection.connect()
    >>> loop.run_forever()
    >>> loop.close()
    """
    def __init__(self, loop, server_addr, port, username, password, settings = {}):
        """Constructor.
        """
        super().__init__(loop, server_addr, port)
       
        self.username = username
        self.password = password

        self.settings = lcn_defs.default_connection_settings
        self.settings.update(settings)
       
        self.ping_interval = 60 * 10     # seconds
        self.ping_counter = 0
       
        self.dim_mode = lcn_defs.OutputPortDimMode.STEPS50
        self.status_mode = lcn_defs.OutputPortStatusMode.PERCENT
 
        self._is_lcn_connected = False
        self.local_seg_id = -1
       
        # Futures for connection status handling.
        self.socket_connected = asyncio.Future()
        self.lcn_connected = asyncio.Future()
        self.segment_scan_completed = asyncio.Future()

        # All modules from or to a communication occurs are represented by a unique ModuleConnection object.
        # All ModuleConnection objects are stored in this dictionary.
        self.module_conns = {}
        
        self.status_segment_scan = TimeoutRetryHandler(loop, self.settings['SK_NUM_TRIES'])
        self.ping = TimeoutRetryHandler(loop, -1, self.settings['PING_TIMEOUT'])
        self.ping.set_timeout_callback(self.ping_timeout)

    def connection_made(self, transport):
        super().connection_made(transport)
        self.socket_connected.set_result(True)

    def connection_lost(self, error):
        super().connection_lost(error)
        
        self.status_segment_scan.cancel()
        self.ping.cancel()
        for module_conn in self.module_conns.values():
            module_conn.cancel_timeout_retries()
       
    def on_successful_login(self):
        self.logger.info('PCHK login successful.')
        self.set_lcn_connected(True)
        self.ping.activate()
 
    def on_auth_ok(self):
        self.logger.info('Authorization successful!')
 
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
        #self._is_lcn_connected = is_lcn_connected
        if is_lcn_connected:
            self.lcn_connected.set_result(True)
            self.status_segment_scan.activate(self.segment_scan_timeout)
        else:
            # Repeat segment scan on next connect
            self.local_seg_id = -1
            self.status_segment_scan.reset()
            # While we are disconnected we will miss all status messages.
            # Clearing our runtime data will give us a fresh start.
            self.module_conns.clear()

    async def connect(self, timeout = 30):
        """Establishes a connection to PCHK at the given socket, ensures that the LCN bus is present and authorizes at PCHK.
        Raises a :class:`TimeoutError`, if connection could not be established within the given timeout. 
        
        :param    int    timeout:    Timeout in seconds
        """
        super().connect()
        done, pending = await asyncio.wait([self.socket_connected, self.lcn_connected, self.segment_scan_completed], timeout = timeout)
        if len(pending) > 0:
            raise TimeoutError('No server listening. Aborting.')
        
    def set_local_seg_id(self, local_seg_id):
        """Sets the local segment id.
        
        :param    int    local_seg_id:    The local segment_id.
        """
        old_local_seg_id = self.local_seg_id

        self.local_seg_id = local_seg_id
        # replace all module_conns with current local_seg_id with new local_seg_id
        for addr in self.module_conns:
            if addr.seg_id == old_local_seg_id:
                module_conn = self.module_conns.pop(addr)
                module_conn.seg_id = self.local_seg_id
                self.module_conns[LcnAddrMod(self.local_seg_id, addr.mod_id)] = module_conn

        self.segment_scan_completed.set_result(True)                
 
    def physical_to_logical(self, addr):
        return LcnAddrMod(self.local_seg_id if addr.get_seg_id() == 0 else addr.get_seg_id(), addr.get_mod_id())

    def is_ready(self):
        """Retrieves the overall connection state.
        Nothing should be sent before this is signaled.

        :returns:    True if everything is set-up, False otherwise
        :rtype:      bool
        """
        return self.socket_connected.done() and self.lcn_connected.done() and self.segment_scan_completed.done()
 
    def get_module_conn(self, addr):
        """Creates and/or returns cached data for the given LCN module.
        The LCN module object is used for further communication with the module (e.g. sending commands). 
        
        :param    addr:    The module's address
        :type     addr:    :class:`~LcnAddrMod`
        
        :returns: The module connection object (never null)
        :rtype: `~ModuleConnection`
        """
        if addr.is_group():
            raise ValueError('Address has to be a module.')
        module_conn = self.module_conns.get(addr, None)
        if module_conn is None:
            module_conn = ModuleConnection(self.loop, self, addr.seg_id, addr.mod_id)
            self.module_conns[addr] = module_conn
            
        return module_conn
    
    def segment_scan_timeout(self, failed):
        """Gets called if no response from segment coupler was received.
        
        :param    bool    failed:    True if caller failed to fulfill request otherwise False
        """
        if failed:
            self.logger.info('No segment coupler found.')
            self.set_local_seg_id(0)
        else:
            self.send_command(PckGenerator.generate_address_header(LcnAddrGrp(3, 3), self.local_seg_id, False) + PckGenerator.segment_coupler_scan())
 
    def ping_timeout(self, failed):
        """Send a ping command to keep the connection to LCN-PCHK alive.
        (default is every 10 minutes)"""
        self.send_command('^ping{:d}'.format(self.ping_counter))
        self.ping_counter += 1
 
    def process_input(self, input):
        self.logger.info('from PCHK: {}'.format(input))
        commands = InputParser.parse(input)
        for command in commands:
            command.process(self)
