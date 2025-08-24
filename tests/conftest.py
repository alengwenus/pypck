"""Core testing functionality."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

import pypck
from pypck.connection import PchkConnectionManager
from pypck.lcn_addr import LcnAddr
from pypck.module import GroupConnection, ModuleConnection
from pypck.pck_commands import PckGenerator

HOST = "127.0.0.1"
PORT = 4114
USERNAME = "lcn"
PASSWORD = "lcn"


class MockModuleConnection(ModuleConnection):
    """Fake a LCN module connection."""

    status_request_handler = AsyncMock()
    activate_status_request_handler = AsyncMock()
    cancel_status_request_handler = AsyncMock()
    request_name = AsyncMock(return_value="TestModule")
    send_command = AsyncMock(return_value=True)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Construct ModuleConnection instance."""
        super().__init__(*args, **kwargs)
        self.serials_request_handler.serial_known.set()


class MockGroupConnection(GroupConnection):
    """Fake a LCN group connection."""

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

    def get_address_conn(
        self, addr: LcnAddr, request_serials: bool = False
    ) -> ModuleConnection | GroupConnection:
        """Get LCN address connection."""
        return super().get_address_conn(addr, request_serials)

    @patch.object(pypck.connection, "ModuleConnection", MockModuleConnection)
    def get_module_conn(
        self, addr: LcnAddr, request_serials: bool = False
    ) -> ModuleConnection:
        """Get LCN module connection."""
        return super().get_module_conn(addr, request_serials)

    @patch.object(pypck.connection, "GroupConnection", MockGroupConnection)
    def get_group_conn(self, addr: LcnAddr) -> GroupConnection:
        """Get LCN group connection."""
        return super().get_group_conn(addr)

    scan_modules = AsyncMock()
    send_command = AsyncMock()


def encode_pck(pck: str) -> bytes:
    """Encode the given PCK string as PCK binary string."""
    return (pck + PckGenerator.TERMINATION).encode()


@pytest.fixture
async def pypck_client() -> MockPchkConnectionManager:
    """Create a mock PCHK connection manager."""
    return MockPchkConnectionManager(HOST, PORT, USERNAME, PASSWORD)


# @pytest.fixture
# async def module10(
#     pypck_client: PchkConnectionManager,
# ) -> AsyncGenerator[ModuleConnection, None]:
#     """Create test module with addr_id 10."""
#     lcn_addr = LcnAddr(0, 10, False)
#     module = pypck_client.get_module_conn(lcn_addr)
#     yield module
#     await module.cancel_requests()
