import asyncio
import logging
 
from pypck.pck_commands import PckGenerator
from pypck import lcn_defs
from pypck.input import InputParser
from pypck.lcn_addr import LcnAddrMod, LcnAddrGrp
from pypck.module import ModuleConnection
from pypck.timeout_retry import TimeoutRetryHandler, DEFAULT_TIMEOUT_MSEC


class PchkConnection(asyncio.Protocol):
    def __init__(self, loop, server_addr, port, username, password):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.loop = loop
        self.server_addr = server_addr
        self.port = port
        self.username = username
        self.password = password
        self.transport = None
 
        self.buffer = b''
   
    def connect(self):
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
        return self.transport != None
   
    def data_received(self, data):
        self.buffer += data
        inputs = self.buffer.split(b'\n')
        self.buffer = inputs.pop()
 
        for input in inputs:
            self.process_input(input.decode())
   
    def send_command(self, pck):
        self.logger.info('to PCHK: {}'.format(pck))
        self.transport.write((pck + PckGenerator.TERMINATION).encode())
   
    def process_input(self, input):
        pass
 
 
class PchkConnectionManager(PchkConnection):
    """
    Has the following tasks:
    - Initiates login procedure.
    - Ping PCHK.
    - Parse incoming commands and create input objects.
    - Calls input object's process method.
    - Updates seg_id of ModuleConnections if segment scan finishes. 
    """
    def __init__(self, loop, server_addr, port, username, password):
        super().__init__(loop, server_addr, port, username, password)
       
        self.ping_interval = 60 * 10     # seconds
        self.ping_counter = 0
       
        self.dim_mode = lcn_defs.output_port_dim_mode.STEPS50
        self.status_mode = lcn_defs.output_port_status_mode.PERCENT
 
        self.is_lcn_connected = False
        self.local_seg_id = -1
       
        # All modules from or to a communication occurs are represented by a unique ModuleConnection object.
        # All ModuleConnection objects are stored in this dictionary.
        self.module_conns = {}
        
        self.status_segment_scan = TimeoutRetryHandler(loop, 3, DEFAULT_TIMEOUT_MSEC)
       
    def on_successful_login(self):
        self.ping_task = self.loop.create_task(self.send_ping())
 
    def on_auth_ok(self):
        self.logger.info('Authorization successful!')
        self.set_lcn_connected(True)
 
    def set_lcn_connected(self, is_lcn_connected):
        """
        Sets the current connection state.
        """
        self.is_lcn_connected = is_lcn_connected
        if is_lcn_connected:
            self.status_segment_scan.activate(self.segment_scan_timeout)
        else:
            # Repeat segment scan on next connect
            self.local_seg_id = -1
            self.status_segment_scan.reset()
            # While we are disconnected we will miss all status messages.
            # Clearing our runtime data will give us a fresh start.
            self.module_conns.clear()

    def set_local_seg_id(self, local_seg_id):
        """
        Sets the local segment id.
        """
        old_local_seg_id = self.local_seg_id

        self.local_seg_id = local_seg_id
        # replace all module_conns with current local_seg_id with new local_seg_id
        for addr in self.module_conns:
            if addr.seg_id == old_local_seg_id:
                module_conn = self.module_conns.pop(addr)
                module_conn.seg_id = self.local_seg_id
                self.module_conns[LcnAddrMod(self.local_seg_id, addr.mod_id)] = module_conn
                
        # self.status_segment_scan.cancel()
 
    def physical_to_logical(self, addr):
        return LcnAddrMod(self.local_seg_id if addr.get_seg_id() == 0 else addr.get_seg_id(), addr.get_mod_id())

    def is_ready(self):
        """
        Retrieves the completion state.
        Nothing should be sent before this is signaled.

        @return true if everything is set-up        
        """
        return self.is_socket_connected and self.is_lcn_connected and (self.local_seg_id != -1)
 
    def get_module_conn(self, addr):
        module_conn = self.module_conns.get(addr, None)
        return module_conn
     
    def update_module_conn(self, addr):
        """
        Creates and/or returns cached data for the given LCN module.
        @param addr the module's address
        @return the data (never null)       
        """
        module_conn = self.module_conns.get(addr, None)
        if module_conn is None:
            module_conn = ModuleConnection(loop, self, addr.seg_id, addr.mod_id)
            self.module_conns[addr] = module_conn
            
            # Check if segment scan has finished and activate module's request handlers immediately (good for manually added module_conns).
            # Otherwise module's request handlers will be started, if segment scan finishes.  
            if self.is_ready():
                module_conn.activate_status_request_handlers()
        return module_conn
    
    def segment_scan_timeout(self, failed):
        """
        Gets called if no response from segment coupler was received.
        """
        if failed:
            self.logger.info('No segment coupler found.')
            self.set_local_seg_id(0)
            for module_conn in self.module_conns.values():
                module_conn.activate_status_request_handlers()
        else:
            self.send_module_command(LcnAddrGrp(3, 3), False, PckGenerator.segment_coupler_scan())
 
    async def send_ping(self):
        # Send a ping command to keep the connection to LCN-PCHK alive.
        # (default is every 10 minutes)
        while not self.transport.is_closing():
            self.send_command('^ping{:d}'.format(self.ping_counter))
            self.ping_counter += 1
            await asyncio.sleep(self.ping_interval)
 
    def send_module_command(self, addr, wants_ack, pck):
        """
        Sends a command to the specified module or group.
        """
        if (not addr.is_group()) and wants_ack:
            self.update_module_conn(addr).schedule_command_with_ack(pck, self, DEFAULT_TIMEOUT_MSEC)
        else:
            self.send_command(PckGenerator.generate_address_header(addr, self.local_seg_id, wants_ack) + pck)
 
    def process_input(self, input):
        command = InputParser.parse(input)
        self.logger.info('from PCHK: {}'.format(input))
        command.process(self)
    
 
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
 
    loop = asyncio.get_event_loop()
    connection = PchkConnectionManager(loop, '10.1.2.3', 4114, 'lcn', 'lcn')
    connection.update_module_conn(LcnAddrMod(0, 7))
    connection.connect()
    loop.run_forever()
    loop.close()