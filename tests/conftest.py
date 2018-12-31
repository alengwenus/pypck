"""Core testing functionality."""

import asyncio
from unittest.mock import Mock

import pytest

from pypck.connection import PchkConnectionManager
from pypck.pck_commands import PckGenerator

IP_ADDRESS = '127.0.0.1'
PORT = 4114
USERNAME = 'lcn_username'
PASSWORD = 'lcn_password'


def encode_pck(pck):
    """Encode the given PCK string as PCK binary string."""
    return (pck + PckGenerator.TERMINATION).encode()


@pytest.fixture
def loop():
    """Set up an event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def pchk_connection_manager(monkeypatch, loop):
    """Set up a PchkConnectionManager instace."""
    pchk_connection_manager = PchkConnectionManager(loop,
                                                    IP_ADDRESS,
                                                    PORT,
                                                    USERNAME,
                                                    PASSWORD)

    transport = Mock()
    transport.get_extra_info = Mock(return_value=(IP_ADDRESS,
                                                  PORT))

    def mock_connect():
        """Mock the connection_made method."""
        pchk_connection_manager.connection_made(transport)

    monkeypatch.setattr(pchk_connection_manager, 'connect', mock_connect)
    monkeypatch.setattr(pchk_connection_manager, 'send_command', Mock())

    yield pchk_connection_manager

    loop.run_until_complete(pchk_connection_manager.async_close())


@pytest.fixture
def connection_is_ready(pchk_connection_manager):
    """Set the PchkConnectionManager connection to fully established."""
    pchk_connection_manager.socket_connected.set_result(True)
    pchk_connection_manager.lcn_connected.set_result(True)
    pchk_connection_manager.segment_scan_completed.set_result(True)
