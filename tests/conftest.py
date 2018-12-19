import asyncio
from unittest.mock import Mock

import pytest

from pypck.connection import PchkConnectionManager
from pypck.pck_commands import PckGenerator, PckParser

ip_address = '127.0.0.1'
port = 4114
username = 'lcn_username'
password = 'lcn_password'


def encode_pck(pck):
    """Encodes the given PCK string as PCK binary string.
    """
    return (pck + PckGenerator.TERMINATION).encode()


@pytest.fixture
def loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def pchk_connection_manager(monkeypatch, loop):
    pchk_connection_manager = PchkConnectionManager(loop,
                                                    ip_address,
                                                    port,
                                                    username,
                                                    password)

    transport = Mock()
    transport.get_extra_info = Mock(return_value=(ip_address,
                                                  port))

    def mock_connect():
        pchk_connection_manager.connection_made(transport)

    monkeypatch.setattr(pchk_connection_manager, 'connect', mock_connect)
    monkeypatch.setattr(pchk_connection_manager, 'send_command', Mock())

    yield pchk_connection_manager

    loop.run_until_complete(pchk_connection_manager.close())


@pytest.fixture
def connection_is_ready(pchk_connection_manager):
    pchk_connection_manager.socket_connected.set_result(True)
    pchk_connection_manager.lcn_connected.set_result(True)
    pchk_connection_manager.segment_scan_completed.set_result(True)
