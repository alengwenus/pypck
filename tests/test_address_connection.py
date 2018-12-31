"""Test for address_connection."""

import pytest

from pypck.lcn_addr import LcnAddr
from pypck.module import ModuleConnection
from tests.conftest import encode_pck


@pytest.fixture
def patch_get_module_sw(monkeypatch):
    """Patch the get_module_sw method."""
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
    """Test receiving PCK command form module.

    PCK command is received from module. PchkConnectionManager is not
    completely connected (is_ready() == False).
    No address_connection should be added.
    """
    pck = '=M005007.SN1945134DAF00FW1B0513HW0'
    pchk_connection_manager.data_received(encode_pck(pck))

    assert not pchk_connection_manager.address_conns


@pytest.mark.usefixtures("connection_is_ready", "patch_get_module_sw")
def test_dynamical_setup_of_address_conn_ready(pchk_connection_manager):
    """Test receiving PCK command form module.

    PCK command is received from module. PchkConnectionManager is
    completely connected (is_ready() == True).
    An address_connection should be added.
    """
    pck = '=M005007.SN1945134DAF00FW1B0513HW0'
    pchk_connection_manager.data_received(encode_pck(pck))

    assert len(pchk_connection_manager.address_conns) == 1

    module = list(pchk_connection_manager.address_conns.values())[0]

    assert module.addr_id == 7
    assert module.seg_id == 5
    assert module.get_sw_age() == 0x1B0513

# Test setting local segment id


@pytest.mark.usefixtures("patch_get_module_sw")
def test_post_set_local_seg_id(pchk_connection_manager):
    """Test if local segment id was set correctly.

    Address_connection was previously defined.
    """
    assert pchk_connection_manager.local_seg_id == -1

    addr_05 = LcnAddr(0, 5, False)
    addr_06 = LcnAddr(7, 6, False)
    addr_07 = LcnAddr(6, 7, False)
    module_05 = pchk_connection_manager.get_address_conn(addr_05)
    module_06 = pchk_connection_manager.get_address_conn(addr_06)
    module_07 = pchk_connection_manager.get_address_conn(addr_07)
    assert module_05.get_seg_id() == 0
    assert module_06.get_seg_id() == 7
    assert module_07.get_seg_id() == 6

    # This should only affect module_05
    pchk_connection_manager.set_local_seg_id(7)

    assert module_05.get_seg_id() == 7
    assert module_06.get_seg_id() == 7
    assert module_07.get_seg_id() == 6

    # Now, this should affect module_05 and module_06
    pchk_connection_manager.set_local_seg_id(6)
    assert module_05.get_seg_id() == 6
    assert module_06.get_seg_id() == 6
    assert module_07.get_seg_id() == 6

    # Now, this should affect all defined modules
    pchk_connection_manager.set_local_seg_id(8)
    assert module_05.get_seg_id() == 8
    assert module_06.get_seg_id() == 8
    assert module_07.get_seg_id() == 8


@pytest.mark.usefixtures("patch_get_module_sw")
def test_pre_set_local_seg_id(pchk_connection_manager):
    """Test if local segment id is set correctly.

    Address_connection is defined afterwards.
    """
    assert pchk_connection_manager.local_seg_id == -1

    pchk_connection_manager.set_local_seg_id(7)

    addr_05 = LcnAddr(0, 5, False)
    addr_06 = LcnAddr(7, 6, False)
    addr_07 = LcnAddr(6, 7, False)
    module_05 = pchk_connection_manager.get_address_conn(addr_05)
    module_06 = pchk_connection_manager.get_address_conn(addr_06)
    module_07 = pchk_connection_manager.get_address_conn(addr_07)

    assert module_05.get_seg_id() == 7
    assert module_06.get_seg_id() == 7
    assert module_07.get_seg_id() == 6
