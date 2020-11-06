"""Core testing functionality."""

import asyncio

import asynctest
import pypck
import pytest
from pypck.connection import PchkConnection, PchkConnectionManager
from pypck.pck_commands import PckGenerator

from .fake_pchk import PchkServer

# from unittest.mock import Mock


HOST = "127.0.0.1"
PORT = 4114
USERNAME = "lcn_username"
PASSWORD = "lcn_password"


def encode_pck(pck):
    """Encode the given PCK string as PCK binary string."""
    return (pck + PckGenerator.TERMINATION).encode()


@pytest.fixture
async def pchk_server():
    """Create a fake PchkServer and run."""
    ps = PchkServer(host=HOST, port=PORT, username=USERNAME, password=PASSWORD)
    await ps.run()
    yield ps
    await ps.stop()


@pytest.fixture
async def pypck_client():
    """Create a PchkConnectionManager for testing.

    Create a PchkConnection Manager for testing. Add a received coroutine method
    which returns if the specified message was received (and processed).
    """
    data_received = []

    async def patched_process_message(self, message):
        """Patched version of process_message which buffers incoming messages."""
        data_received.append(message)

    async def received(self, message, timeout=5, remove=True):
        """Await the specified message."""

        async def receive_loop(data, remove):
            while data not in data_received:
                await asyncio.sleep(0.05)
            if remove:
                data_received.remove(data)

        try:
            await asyncio.wait_for(receive_loop(message, remove), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    loop = None
    PchkConnectionManager.received = None
    pcm = PchkConnectionManager(
        loop, HOST, PORT, USERNAME, PASSWORD, settings={"SK_NUM_TRIES": 0}
    )

    with asynctest.patch.object(
        PchkConnection, "process_message", patched_process_message
    ):
        with asynctest.patch.object(PchkConnectionManager, "received", received):
            yield pcm
    await pcm.async_close()
