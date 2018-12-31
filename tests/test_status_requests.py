"""StatusRequestHandler tests."""

import asyncio
from unittest.mock import Mock

import pytest

from pypck import lcn_defs
from pypck.module import ModuleConnection


class MockPchkConnectionManager(Mock):
    """Mocking class for the PchkCOnnectionManager."""

    def __init__(self):
        """Intitialize MockPchkConnectionManager."""
        super().__init__()
        self.settings = lcn_defs.default_connection_settings
        self.socket_connected = asyncio.Future()
        self.lcn_connected = asyncio.Future()
        self.segment_scan_completed = asyncio.Future()

        self.socket_connected.set_result(True)
        self.lcn_connected.set_result(True)
        self.segment_scan_completed.set_result(True)


@pytest.fixture
def pchk_connection_manager():
    """Fixture function for mocking PchkConnectionManager."""
    pchk_connection_manager = MockPchkConnectionManager()
    return pchk_connection_manager


@pytest.fixture
def module_connection(monkeypatch, loop, pchk_connection_manager):
    """Fixture function for setting up and closing a module_connection."""
    module_connection = ModuleConnection(loop, pchk_connection_manager,
                                         0, 7, sw_age=0x170206)
    monkeypatch.setattr(module_connection, 'send_command', Mock())

    yield module_connection
    loop.run_until_complete(module_connection.cancel_status_request_handlers())


def test_activate_status_outputs(loop, module_connection):
    """Test the activation of status outputs handlers.

    Test workflow:
    activate status_request_handler(item) --> send appropriate command
    """
    for item in lcn_defs.OutputPort:
        loop.run_until_complete(
            module_connection.activate_status_request_handler(item))
        module_connection.send_command.assert_called_with(
            False, 'SMA{:d}'.format(item.value + 1))
        module_connection.send_command.reset_mock()
        loop.run_until_complete(
            module_connection.cancel_status_request_handler(item))


def test_activate_status_relays(loop, module_connection):
    """Test the activation of status relays handlers.

    Test workflow:
    activate status_request_handler(item) --> send appropriate command
    """
    for item in lcn_defs.RelayPort:
        loop.run_until_complete(
            module_connection.activate_status_request_handler(item))
        module_connection.send_command.assert_called_with(False, 'SMR')
        module_connection.send_command.reset_mock()
        loop.run_until_complete(
            module_connection.cancel_status_request_handler(item))


def test_activate_status_motor_ports(loop, module_connection):
    """Test the activation of status motor ports handlers.

    Test workflow:
    activate status_request_handler(item) --> send appropriate command
    """
    for item in lcn_defs.MotorPort:
        loop.run_until_complete(
            module_connection.activate_status_request_handler(item))
        module_connection.send_command.assert_called_with(False, 'SMR')
        module_connection.send_command.reset_mock()
        loop.run_until_complete(
            module_connection.cancel_status_request_handler(item))


def test_activate_status_bin_sensor_ports(loop, module_connection):
    """Test the activation of status binary sensor ports handlers.

    Test workflow:
    activate status_request_handler(item) --> send appropriate command
    """
    for item in lcn_defs.BinSensorPort:
        loop.run_until_complete(
            module_connection.activate_status_request_handler(item))
        module_connection.send_command.assert_called_with(False, 'SMB')
        module_connection.send_command.reset_mock()
        loop.run_until_complete(
            module_connection.cancel_status_request_handler(item))


def test_activate_status_led_ports(loop, module_connection):
    """Test the activation of status led ports handlers.

    Test workflow:
    activate status_request_handler(item) --> send appropriate command
    """
    for item in lcn_defs.LedPort:
        loop.run_until_complete(
            module_connection.activate_status_request_handler(item))

        module_connection.send_command.assert_called_with(False, 'SMT')
        module_connection.send_command.reset_mock()
        loop.run_until_complete(
            module_connection.cancel_status_request_handler(item))


def test_activate_status_keys(loop, module_connection):
    """Test the activation of status keys handlers.

    Test workflow:
    activate status_request_handler(item) --> send appropriate command
    """
    for item in lcn_defs.Key:
        loop.run_until_complete(
            module_connection.activate_status_request_handler(item))
        module_connection.send_command.assert_called_with(False, 'STX')
        module_connection.send_command.reset_mock()
        loop.run_until_complete(
            module_connection.cancel_status_request_handler(item))
