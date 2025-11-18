"""Core testing functionality."""

import asyncio
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
from pypck.connection import PchkConnectionManager
from pypck.device import DeviceConnection
from pypck.lcn_addr import LcnAddr
from pypck.pck_commands import PckGenerator

import pypck

HOST = "127.0.0.1"
PORT = 4114
USERNAME = "lcn"
PASSWORD = "lcn"


async def wait_until_called(
    mock: AsyncMock,
    *expected_args: Any,
    timeout: float = 1.0,
    **expected_kwargs: Any,
) -> None:
    """Wait that AsyncMock gets called with given arguments."""
    event = asyncio.Event()

    async def side_effect(*args: Any, **kwargs: Any) -> None:
        """Set the event when the mock is called."""
        if (len(expected_args) == 0 or args == expected_args) and (
            len(expected_kwargs) == 0 or kwargs == expected_kwargs
        ):
            event.set()

    mock.side_effect = side_effect

    await asyncio.wait_for(event.wait(), timeout=timeout)


class MockDeviceConnection(DeviceConnection):
    """Fake a LCN device connection."""

    send_command = AsyncMock(return_value=True)


class MockPchkConnectionManager(PchkConnectionManager):
    """Fake connection handler."""

    is_lcn_connected: Any

    async def async_connect(self, timeout: float = 30) -> None:
        """Mock establishing a connection to PCHK."""
        self.authentication_completed_future.set_result(True)
        self.license_error_future.set_result(True)
        self.segment_scan_completed_event.set()

    async def async_close(self) -> None:
        """Mock closing a connection to PCHK."""

    @patch.object(pypck.connection, "DeviceConnection", MockDeviceConnection)
    def get_device_connection(self, addr: LcnAddr) -> DeviceConnection:
        """Get LCN device connection."""
        return super().get_device_connection(addr)

    scan_modules = AsyncMock()
    send_command = AsyncMock()


def encode_pck(pck: str) -> bytes:
    """Encode the given PCK string as PCK binary string."""
    return (pck + PckGenerator.TERMINATION).encode()


@pytest.fixture
async def pypck_client() -> MockPchkConnectionManager:
    """Create a mock PCHK connection manager."""
    return MockPchkConnectionManager(HOST, PORT, USERNAME, PASSWORD)


@pytest.fixture
async def module10(
    pypck_client: MockPchkConnectionManager,
) -> MockDeviceConnection:
    """Create test module with addr_id 10."""
    lcn_addr = LcnAddr(0, 10, False)
    with patch.object(
        MockDeviceConnection, "_request_device_properties"
    ) as mock_request_device_properties:
        module = cast(
            MockDeviceConnection, pypck_client.get_device_connection(lcn_addr)
        )
        await wait_until_called(cast(AsyncMock, mock_request_device_properties))

    module.send_command.reset_mock()
    return module
