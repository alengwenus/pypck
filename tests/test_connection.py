"""Connection tests."""

import asyncio
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from pypck.connection import (
    PchkAuthenticationError,
    PchkConnectionFailedError,
    PchkConnectionManager,
    PchkConnectionRefusedError,
    PchkLicenseError,
)
from pypck.lcn_addr import LcnAddr
from pypck.lcn_defs import AcknowledgeErrorCode, LcnEvent
from pypck.pck_commands import PckGenerator

from pypck import inputs

from .conftest import HOST, PASSWORD, PORT, USERNAME, MockPchkConnectionManager


async def test_close_without_connect(pypck_client: MockPchkConnectionManager) -> None:
    """Test closing of PchkConnectionManager without connecting."""
    await pypck_client.async_close()


@patch.object(PchkConnectionManager, "open_connection")
@patch.object(PchkConnectionManager, "scan_segment_couplers")
async def test_async_connect(
    mock_scan_segment_couplers: AsyncMock,
    mock_open_connection: AsyncMock,
) -> None:
    """Test successful connection."""
    pypck_client = PchkConnectionManager(HOST, PORT, USERNAME, PASSWORD)
    connect_task = asyncio.create_task(pypck_client.async_connect())
    await asyncio.sleep(0)

    pypck_client.license_error_future.set_result(True)
    pypck_client.authentication_completed_future.set_result(True)
    pypck_client.segment_scan_completed_event.set()

    await connect_task

    mock_scan_segment_couplers.assert_awaited()
    mock_open_connection.assert_awaited()
    assert pypck_client.is_ready()


@patch.object(PchkConnectionManager, "ping")
@patch.object(PchkConnectionManager, "open_connection")
@patch.object(PchkConnectionManager, "scan_segment_couplers")
@patch.object(PchkConnectionManager, "send_command")
async def test_successful_connection_procedure(
    mock_send_command: AsyncMock,
    mock_scan_segment_couplers: AsyncMock,
    mock_open_connection: AsyncMock,
    mock_ping: AsyncMock,
) -> None:
    """Test successful connection procedure."""
    pypck_client = PchkConnectionManager(HOST, PORT, USERNAME, PASSWORD)
    connect_task = asyncio.create_task(pypck_client.async_connect())
    await asyncio.sleep(0)

    await pypck_client.async_process_input(inputs.AuthUsername())
    mock_send_command.assert_awaited_with(USERNAME, to_host=True)

    await pypck_client.async_process_input(inputs.AuthPassword())
    mock_send_command.assert_awaited_with(PASSWORD, to_host=True)

    await pypck_client.async_process_input(inputs.AuthOk())
    mock_send_command.assert_awaited_with(PckGenerator.set_dec_mode(), to_host=True)
    assert pypck_client.authentication_completed_future.result()

    await pypck_client.async_process_input(inputs.DecModeSet())
    mock_send_command.assert_awaited_with(
        PckGenerator.set_operation_mode(
            pypck_client.dim_mode, pypck_client.status_mode
        ),
        to_host=True,
    )
    assert pypck_client.license_error_future.result()

    await connect_task

    mock_open_connection.assert_awaited()
    mock_scan_segment_couplers.assert_awaited()
    mock_ping.assert_awaited()


@pytest.mark.parametrize("side_effect", [ConnectionRefusedError, OSError])
async def test_connection_error(side_effect: ConnectionRefusedError | OSError) -> None:
    """Test connection error."""
    with (
        patch.object(PchkConnectionManager, "open_connection", side_effect=side_effect),
        pytest.raises(PchkConnectionRefusedError),
    ):
        pypck_client = PchkConnectionManager(HOST, PORT, USERNAME, PASSWORD)
        await pypck_client.async_connect()


@patch.object(PchkConnectionManager, "open_connection")
async def test_authentication_error(mock_open_connection: AsyncMock) -> None:
    """Test wrong login credentials."""
    pypck_client = PchkConnectionManager(HOST, PORT, USERNAME, PASSWORD)
    connect_task = asyncio.create_task(pypck_client.async_connect())
    await asyncio.sleep(0)
    await pypck_client.async_process_input(inputs.AuthFailed())

    with (
        pytest.raises(PchkAuthenticationError),
    ):
        await connect_task


@patch.object(PchkConnectionManager, "open_connection")
async def test_license_error(mock_open_connection: AsyncMock) -> None:
    """Test wrong login credentials."""
    pypck_client = PchkConnectionManager(HOST, PORT, USERNAME, PASSWORD)
    connect_task = asyncio.create_task(pypck_client.async_connect())
    await asyncio.sleep(0)
    await pypck_client.async_process_input(inputs.LicenseError())

    with (
        pytest.raises(PchkLicenseError),
    ):
        await connect_task


@patch.object(PchkConnectionManager, "open_connection")
async def test_timeout_error(mock_open_connection: AsyncMock) -> None:
    """Test timeout when connecting."""
    with pytest.raises(PchkConnectionFailedError):
        pypck_client = PchkConnectionManager(HOST, PORT, USERNAME, PASSWORD)
        await pypck_client.async_connect(timeout=0)


async def test_lcn_connected(pypck_client: MockPchkConnectionManager) -> None:
    """Test lcn connected events."""
    event_callback = Mock()
    pypck_client.register_for_events(event_callback)
    await pypck_client.async_connect()

    # bus disconnected
    await pypck_client.async_process_input(inputs.LcnConnState(is_lcn_connected=False))
    assert not pypck_client.is_lcn_connected
    event_callback.assert_has_calls(
        (call(LcnEvent.BUS_CONNECTION_STATUS_CHANGED), call(LcnEvent.BUS_DISCONNECTED))
    )

    # bus connected
    await pypck_client.async_process_input(inputs.LcnConnState(is_lcn_connected=True))
    assert pypck_client.is_lcn_connected
    event_callback.assert_has_calls(
        (call(LcnEvent.BUS_CONNECTION_STATUS_CHANGED), call(LcnEvent.BUS_CONNECTED))
    )


async def test_new_module_on_input(
    pypck_client: MockPchkConnectionManager,
) -> None:
    """Test new module detection on serial input."""
    await pypck_client.async_connect()
    address = LcnAddr(0, 7, False)
    assert address not in pypck_client.device_connections.keys()

    await pypck_client.async_process_input(
        inputs.ModAck(address, AcknowledgeErrorCode.OK)
    )

    assert address in pypck_client.device_connections.keys()
