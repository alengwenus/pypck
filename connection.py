import asyncio
import logging

from pypck.pck_commands import PckGenerator 

class PchkConnection(asyncio.Protocol):
    def __init__(self, loop, server_addr, port, username, password):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.loop = loop
        self.username = username
        self.password = password
        self.transport = None
        self.version = None
        
        self.ping_interval = 10     # seconds
        self.ping_counter = 0

        self.buffer = b''
        self.write_buffer = b''
        self.read_buffer = b''
    
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
    
    def on_successful_login(self):
        coro = self.loop.create_task(self.send_ping())
        
    async def send_ping(self):
        # Send a ping command to keep the connection to LCN-PCHK alive.
        # (default is every 10 minutes)
        while not self.transport.is_closing():
            self.send_command('^ping{:d}'.format(self.ping_counter))
            self.ping_counter += 1
            asyncio.sleep(self.ping_interval)
    
    def queue_plain_text(self, plain_text):
        text = plain_text + PckGenerator.TERMINATION
        self.write_buffer.append(text.encoded())
    
    def queue_pck(self, addr, wants_ack, pck):
        #if (!addr.isGroup() & wants_ack):
        #    self.update_module_data(addr).queue_pck_with_ack(data, self, self.sets.get_timeout(), time.time())
        self.write_buffer.append()
    
    
    
    def data_received(self, data):
        self.buffer += data
        commands = self.buffer.split(b'\n')
        self.buffer = commands.pop()

        for command in commands:
            self.process_command(command.decode())
    
    def send_command(self, command):
        self.transport.write(command.encode() + b'\n')
    
    def process_command(self, command):
        if self.version == None:
            self.version = command
            self.logger.info(self.version)
        elif command == 'Username:':
            self.send_command(self.username)
        elif command == 'Password:':
            self.send_command(self.password)
            self.logger.info('Login in with username "{}" and password "{}"'.format(self.username, self.password))
        elif command == 'Authentification failed.':
            self.logger.info(command)
        elif command == b'$io:#LCN:connected\n':
            self.logger.info('Login succesful.')
            self.on_successful_login()
        else:
            print(command)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    coupler = LcnPchkCoupler(loop, '10.1.2.3', 4114, 'lcn', 'lcn')
    loop.run_forever()
loop.close()