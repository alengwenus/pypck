"""Fake PCHK server used for testing"""

import asyncio

HOST = "127.0.0.1"
PORT = 4114
USERNAME = "lcn_username"
PASSWORD = "lcn_password"

READ_TIMEOUT = -1
SOCKET_CLOSED = -2
SEPARATOR = b"\n"


async def readuntil_timeout(reader, separator, timeout):
    """Read from socket with timeout."""
    try:
        data = await asyncio.wait_for(reader.readuntil(separator), timeout)
        data = data.split(separator)[0]
        data = data.split(b"\r")[0]  # remove CR if present
    except asyncio.TimeoutError:
        data = READ_TIMEOUT
    except asyncio.IncompleteReadError:
        data = SOCKET_CLOSED
    return data


class PchkServer:
    def __init__(self, host=HOST, port=PORT, username=USERNAME, password=PASSWORD):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.separator = SEPARATOR
        self.license_error = False
        self.data_received = []
        self.server = None
        self.reader = None
        self.writer = None

    async def run(self):
        self.server = await asyncio.start_server(
            self.client_connected, host=self.host, port=self.port
        )

    async def stop(self):
        if self.server and self.server.is_serving():
            self.server.close()
            await self.server.wait_closed()

    async def client_connected(self, reader, writer):
        # Accept only one connection.
        if self.reader or self.writer:
            return

        self.reader = reader
        self.writer = writer

        auth_ok = await self.authentication()
        if not auth_ok:
            return

        await self.main_loop()

    def set_license_error(self, license_error=False):
        self.license_error = license_error

    async def authentication(self):
        self.writer.write(b"LCN-PCK/IP 1.0" + self.separator)
        await self.writer.drain()

        # Ask for username
        self.writer.write(b"Username:" + self.separator)
        await self.writer.drain()

        # Read username input
        data = await readuntil_timeout(self.reader, self.separator, 60)
        if data in [READ_TIMEOUT, SOCKET_CLOSED]:
            return False

        login_username = data.decode()

        # Ask for password
        self.writer.write(b"Password:" + self.separator)
        await self.writer.drain()

        # Read password input
        data = await readuntil_timeout(self.reader, self.separator, 60)
        if data in [READ_TIMEOUT, SOCKET_CLOSED]:
            return False

        login_password = data.decode()
        if login_username == self.username and login_password == self.password:
            self.writer.write(b"OK" + self.separator)
            await self.writer.drain()
        else:
            self.writer.write(b"Authentification failed." + self.separator)
            await self.writer.drain()
            return False

        if self.license_error:
            self.writer.write(b"$err:(license?)" + self.separator)
            return False

        return True

    async def main_loop(self):
        """Main loop"""
        while True:
            # Read data from socket
            data = await readuntil_timeout(self.reader, self.separator, 1.0)
            if data == READ_TIMEOUT:
                continue
            if data == SOCKET_CLOSED:
                break
            await self.process_data(data)

    async def process_data(self, data):
        self.data_received.append(data)
        if data == b"!CHD":
            self.writer.write(b"(dec-mode)" + self.separator)
            await self.writer.drain()

    async def send_message(self, message):
        self.writer.write(message.encode() + self.separator)

    async def received(self, message, timeout=5, remove=True):
        async def receive_loop(data, remove):
            while data not in self.data_received:
                await asyncio.sleep(0.05)
            if remove:
                self.data_received.remove(data)

        try:
            await asyncio.wait_for(receive_loop(message, remove), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
