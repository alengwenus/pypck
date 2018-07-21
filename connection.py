import asyncio
import logging
 
from pypck.pck_commands import PckGenerator
from pypck import lcn_defs
from pypck.input import InputParser
from pypck.lcn_addr import LcnAddrMod, LcnAddrGrp
from pypck.timeout_retry import TimeoutRetryHandler, DEFAULT_TIMEOUT_MSEC
from psutil._common import addr
 


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
    - Ping PCHK.
    - Parse incoming commands and create input objects.
    - Calls input object's process method.
    - If command has a module source, send input object to appropriate modules.
    """
    def __init__(self, loop, server_addr, port, username, password):
        super().__init__(loop, server_addr, port, username, password)
       
        self.ping_interval = 60 * 10     # seconds
        self.ping_counter = 0
       
        self.dim_mode = lcn_defs.output_port_dim_mode.STEPS50
        self.status_mode = lcn_defs.output_port_status_mode.PERCENT
 
        self.is_lcn_connected = False
        self.local_seg_id = -1
       
        self.mod_data = {}
        
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
            self.mod_data.clear()

    def set_local_seg_id(self, local_seg_id):
        """
        Sets the local segment id.
        """
        self.local_seg_id = local_seg_id
        self.status_segment_scan.cancel()
 
    def physical_to_logical(self, addr):
        return LcnAddrMod(self.local_seg_id if addr.get_seg_id() == 0 else addr.get_seg_id(), addr.get_mod_id())

    def on_ack(self, addr, code):
        # TODO:  Continue development in LcnAddrMod 
        info = self.mod_data.get(addr, None)
#        if info is not None:
#            info.on_ack(code)

    def is_ready(self):
        """
        Retrieves the completion state.
        Nothing should be sent before this is signaled.

        @return true if everything is set-up        
        """
        return self.is_socket_conneted & self.is_lcn_connected & (self.local_seg_id != -1)
 
    def get_mod_info(self, addr):
        return self.mod_data.get(addr)
 
# TODO: Has this to be implemented?
#     def update_module_data(self):
#         """
#         Creates and/or returns cached data for the given LCN module.
#         @param addr the module's address
#         @return the data (never null)       
#         """
#         data = self.mod_data.get(addr, None)
#         if data != None:
#             data = ModInfo(addr)
#             self.mod_data[addr] = data
#         return data
    
    async def send_ping(self):
        # Send a ping command to keep the connection to LCN-PCHK alive.
        # (default is every 10 minutes)
        while not self.transport.is_closing():
            self.send_command('^ping{:d}'.format(self.ping_counter))
            self.ping_counter += 1
            await asyncio.sleep(self.ping_interval)

    def segment_scan_timeout(self, num_retry):
        if num_retry == 0:
            self.logger.info('No segment coupler found.')
        else:
            self.send_module_command(LcnAddrGrp(3, 3), False, PckGenerator.segment_coupler_scan())
 
    def send_module_command(self, addr, wants_ack, pck):
        """
        Sends a command to the specified module or group.
        """
        if (not addr.is_group()) & wants_ack:
            self.update_module_data(addr).send_command_with_ack(pck, self, DEFAULT_TIMEOUT_MSEC)
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
    connection.connect()
    loop.run_forever()
    loop.close()