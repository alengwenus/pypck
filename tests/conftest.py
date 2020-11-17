"""Core testing functionality."""

import asyncio

import pytest
from pypck.connection import PchkConnectionManager
from pypck.lcn_addr import LcnAddr
from pypck.pck_commands import PckGenerator

from .fake_pchk import PchkServer

HOST = "127.0.0.1"
PORT = 4114
USERNAME = "lcn_username"
PASSWORD = "lcn_password"


class MockPchkConnectionManager(PchkConnectionManager):
    """Mock the PchkCOnnectionManager."""

    def __init__(self, *args, **kwargs):
        """Construct mock for PchkCOnnectionManager."""
        self.data_received = []
        super().__init__(*args, **kwargs)

    async def process_message(self, message):
        """Process incoming message."""
        await super().process_message(message)
        self.data_received.append(message)

    async def received(self, message, timeout=5, remove=True):
        """Return if given message was received."""

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


def encode_pck(pck):
    """Encode the given PCK string as PCK binary string."""
    return (pck + PckGenerator.TERMINATION).encode()


@pytest.fixture
async def pchk_server():
    """Create a fake PchkServer and run."""
    pchk_server = PchkServer(host=HOST, port=PORT, username=USERNAME, password=PASSWORD)
    await pchk_server.run()
    yield pchk_server
    await pchk_server.stop()


@pytest.fixture
async def pypck_client():
    """Create a PchkConnectionManager for testing.

    Create a PchkConnection Manager for testing. Add a received coroutine method
    which returns if the specified message was received (and processed).
    """
    pcm = MockPchkConnectionManager(
        HOST, PORT, USERNAME, PASSWORD, settings={"SK_NUM_TRIES": 0}
    )
    yield pcm
    await pcm.async_close()


@pytest.fixture
async def module10(pypck_client):
    """Create test module with addr_id 10."""
    lcn_addr = LcnAddr(0, 10, False)
    address_connection = pypck_client.get_address_conn(lcn_addr)
    yield address_connection
    await address_connection.cancel_requests()
