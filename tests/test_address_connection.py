'''
Test:
  - Setup of address_connections
  - Receive segment_id info from modules (address_connections)
    - within the same segment
    - within foreign segments
  - Test firmware differences (behaviours)
'''

import pytest

from conftest import encode_pck
from pypck.lcn_addr import LcnAddr
from pypck.module import ModuleConnection


@pytest.fixture
def patch_get_module_sw(monkeypatch):

    async def mock_get_module_sw(self):
        pass

    monkeypatch.setattr(ModuleConnection, 'get_module_sw', mock_get_module_sw)

# Test setup of address_connection and handling


@pytest.mark.usefixtures("patch_get_module_sw")
def test_manual_setup_of_address_connection(pchk_connection_manager):
    """By manual setup."""
    addr_05 = LcnAddr(0, 5, False)
    addr_07 = LcnAddr(0, 7, False)
    module_05 = pchk_connection_manager.get_address_conn(addr_05)
    module_07 = pchk_connection_manager.get_address_conn(addr_07)

    assert module_05 in pchk_connection_manager.address_conns
    assert module_07 in pchk_connection_manager.address_conns

    assert module_05 is pchk_connection_manager.get_address_conn(addr_05)
    assert module_05 is pchk_connection_manager.get_address_conn(module_05)


@pytest.mark.usefixtures("patch_get_module_sw")
def test_dynamical_setup_of_address_conn_not_ready(pchk_connection_manager):
    """PCK command is received from module. PchkConnectionManager is not
    completely connected (is_ready() == False).
    No address_connection should be added."""
    pck = '=M005007.SN1945134DAF00FW1B0513HW0'
    pchk_connection_manager.data_received(encode_pck(pck))

    assert len(pchk_connection_manager.address_conns) == 0


@pytest.mark.usefixtures("connection_is_ready", "patch_get_module_sw")
def test_dynamical_setup_of_address_conn_ready(pchk_connection_manager):
    """PCK command is received from module. PchkConnectionManager is
    completely connected (is_ready() == True).
    An address_connection should be added."""
    pck = '=M005007.SN1945134DAF00FW1B0513HW0'
    pchk_connection_manager.data_received(encode_pck(pck))

    assert len(pchk_connection_manager.address_conns) == 1

    module = list(pchk_connection_manager.address_conns.values())[0]

    assert module.addr_id == 7
    assert module.seg_id == 5
    assert module.get_sw_age() == 0x1B0513

# Test setting local segment id


def test_post_set_local_seg_id(pchk_connection_manager):
    """Test if local segment id was set correctly on previously defined
    address_connections.
    """
    pass


def test_pre_set_local_seg_id(pchk_connection_manager):
    """Test if local segment id is set correctly on post defined
    address_connections.
    """
    pass
