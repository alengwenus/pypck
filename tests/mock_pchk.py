"""Fake PCHK server used for testing."""

from __future__ import annotations

import asyncio

HOST = "127.0.0.1"
PORT = 4114
USERNAME = "lcn_username"
PASSWORD = "lcn_password"

READ_TIMEOUT = -1
SOCKET_CLOSED = -2
SEPARATOR = b"\n"


async def readuntil_timeout(
    reader: asyncio.StreamReader, separator: bytes, timeout: float
) -> bytes | int:
    """Read from socket with timeout."""
    try:
        data = await asyncio.wait_for(reader.readuntil(separator), timeout)
        data = data.split(separator)[0]
        data = data.split(b"\r")[0]  # remove CR if present
        return data
    except asyncio.TimeoutError:
        return READ_TIMEOUT
    except asyncio.IncompleteReadError:
        return SOCKET_CLOSED


class MockPchkServer:
    """Mock PCHK server for integration tests."""

    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
        username: str = USERNAME,
        password: str = PASSWORD,
    ):
        """Construct PchkServer."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.separator = SEPARATOR
        self.license_error = False
        self.data_received: list[bytes] = []
        self.server: asyncio.AbstractServer | None = None
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None

    async def run(self) -> None:
        """Start the server."""
        self.server = await asyncio.start_server(
            self.client_connected, host=self.host, port=self.port
        )

    async def stop(self) -> None:
        """Stop the server and close connection."""
        if self.server and self.server.is_serving():
            if not (self.writer is None or self.writer.is_closing()):
                self.writer.close()
                await self.writer.wait_closed()
            self.server.close()
            await self.server.wait_closed()

    async def client_connected(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Client connected callback."""
        # Accept only one connection.
        if self.reader or self.writer:
            return

        self.reader = reader
        self.writer = writer

        auth_ok = await self.authentication()
        if not auth_ok:
            return

        await self.main_loop()

    def set_license_error(self, license_error: bool = False) -> None:
        """Raise a license error during authentication."""
        self.license_error = license_error

    async def authentication(self) -> bool:
        """Run authentication procedure."""
        assert self.writer is not None
        assert self.reader is not None

        self.writer.write(b"LCN-PCK/IP 1.0" + self.separator)
        await self.writer.drain()

        # Ask for username
        self.writer.write(b"Username:" + self.separator)
        await self.writer.drain()

        # Read username input
        data = await readuntil_timeout(self.reader, self.separator, 60)
        if data in [READ_TIMEOUT, SOCKET_CLOSED]:
            return False

        assert isinstance(data, bytes)
        login_username = data.decode()

        # Ask for password
        self.writer.write(b"Password:" + self.separator)
        await self.writer.drain()

        # Read password input
        data = await readuntil_timeout(self.reader, self.separator, 60)
        if data in [READ_TIMEOUT, SOCKET_CLOSED]:
            return False

        assert isinstance(data, bytes)

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

    async def main_loop(self) -> None:
        """Query the socket."""
        assert self.reader is not None
        while True:
            # Read data from socket
            data = await readuntil_timeout(self.reader, self.separator, 1.0)
            if data == READ_TIMEOUT:
                continue
            if data == SOCKET_CLOSED:
                break
            assert isinstance(data, bytes)
            await self.process_data(data)

    async def process_data(self, data: bytes) -> None:
        """Process incoming data."""
        assert self.writer is not None
        self.data_received.append(data)
        if data == b"!CHD":
            self.writer.write(b"(dec-mode)" + self.separator)
            await self.writer.drain()

    async def send_message(self, message: str) -> None:
        """Send the given message to the socket."""
        assert self.writer is not None
        self.writer.write(message.encode() + self.separator)

    async def received(
        self, message: bytes | str, timeout: int = 5, remove: bool = True
    ) -> bool:
        """Return if given message was received."""
        assert self.writer is not None

        async def receive_loop(data: bytes, remove: bool) -> None:
            while data not in self.data_received:
                await asyncio.sleep(0.05)
            if remove:
                self.data_received.remove(data)

        if isinstance(message, str):
            data = message.encode()
        else:
            data = message

        try:
            await asyncio.wait_for(receive_loop(data, remove), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
