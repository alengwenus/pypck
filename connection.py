import asyncio
import logging

from pypck.pck_commands import PckGenerator
from pypck import lcn_defs
from pypck.input import InputParser 

class PchkConnection(asyncio.Protocol):
    def __init__(self, loop, server_addr, port, username, password):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.loop = loop
        self.username = username
        self.password = password
        self.transport = None

        self.buffer = b''
    
        coro = self.loop.create_connection(lambda: self, server_addr, port)
        self.client = self.loop.create_task(coro)
        
    def connection_made(self, transport):
        self.transport = transport
        self.address = transport.get_extra_info('peername')
        self.logger.info('PCHK server connected at {}:{}'.format(*self.address))
    
    def connection_lost(self, error):
        if error:
            self.logger.info('Error')
        else:
            self.logger.info('Connection lost.')
        super().connection_lost(error)
    
    def data_received(self, data):
        self.buffer += data
        inputs = self.buffer.split(b'\n')
        self.buffer = inputs.pop()

        for input in inputs:
            self.process_input(input.decode())
    
    def send_command(self, command):
        self.transport.write((command + PckGenerator.TERMINATION).encode())
    
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
        
    def on_successful_login(self):
        self.ping_task = self.loop.create_task(self.send_ping())

    def on_auth_ok(self):
        self.logger.info('Authorization successful!')

    async def send_ping(self):
        # Send a ping command to keep the connection to LCN-PCHK alive.
        # (default is every 10 minutes)
        while not self.transport.is_closing():
            self.send_command('^ping{:d}'.format(self.ping_counter))
            self.ping_counter += 1
            await asyncio.sleep(self.ping_interval)

    def process_input(self, input):
        command = InputParser.parse(input)
        self.logger.info('from PCHK: {}'.format(input))
        command.process(self)
        

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    connection = PchkConnectionManager(loop, '10.1.2.3', 4114, 'lcn', 'lcn')
    loop.run_forever()
    loop.close()