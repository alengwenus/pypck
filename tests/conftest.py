"""Core testing functionality."""

import asyncio

import pytest
from pypck.connection import PchkConnectionManager
from pypck.pck_commands import PckGenerator

from .fake_pchk import PchkServer

# from unittest.mock import Mock


HOST = '127.0.0.1'
PORT = 4114
USERNAME = 'lcn_username'
PASSWORD = 'lcn_password'


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
    """Create a PchkConnectionManager for testing."""
    loop = None
    pcm = PchkConnectionManager(
        loop, HOST, PORT, USERNAME, PASSWORD,
        settings={'SK_NUM_TRIES': 0})
    yield pcm
    await pcm.async_close()
