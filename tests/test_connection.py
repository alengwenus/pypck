"""Connection tests."""

import asyncio

import asynctest
import pytest
from pypck.connection import PchkAuthenticationError, PchkLicenseError
from pypck.lcn_addr import LcnAddr
from pypck.module import ModuleConnection


@pytest.mark.asyncio
async def test_close_without_connect(pypck_client):
    """Test closing of PchkConnectionManager without connecting."""
    await pypck_client.async_close()


@pytest.mark.asyncio
async def test_authenticate(pchk_server, pypck_client):
    """Test authentication procedure."""
    await pypck_client.async_connect()
    assert pypck_client.is_ready()


@pytest.mark.asyncio
async def test_port_error(pchk_server, pypck_client):
    """Test wrong port."""
    pypck_client.port = 55555
    with pytest.raises(ConnectionRefusedError):
        await pypck_client.async_connect()


@pytest.mark.asyncio
async def test_authentication_error(pchk_server, pypck_client):
    """Test wrong login credentials."""
    pypck_client.password = "wrong_password"
    with pytest.raises(PchkAuthenticationError):
        await pypck_client.async_connect()


@pytest.mark.asyncio
async def test_license_error(pchk_server, pypck_client):
    """Test license error."""
    pchk_server.set_license_error(True)

    with pytest.raises(PchkLicenseError):
        await pypck_client.async_connect()


@pytest.mark.asyncio
async def test_timeout_error(pchk_server, pypck_client):
    """Test timeout when connecting."""
    with pytest.raises(TimeoutError):
        await pypck_client.async_connect(timeout=0)


@pytest.mark.asyncio
async def test_lcn_connected(pchk_server, pypck_client):
    """Test lcn disconnected event."""
    pypck_client.event_handler = asynctest.CoroutineMock()
    await pypck_client.async_connect()
    await pchk_server.send_message("$io:#LCN:connected")
    await pypck_client.received("$io:#LCN:connected")

    pypck_client.event_handler.assert_has_awaits(
        [
            asynctest.mock.call("lcn-connection-status-changed"),
            asynctest.mock.call("lcn-connected"),
        ]
    )


@pytest.mark.asyncio
async def test_lcn_disconnected(pchk_server, pypck_client):
    """Test lcn disconnected event."""
    pypck_client.event_handler = asynctest.CoroutineMock()
    await pypck_client.async_connect()
    await pchk_server.send_message("$io:#LCN:disconnected")
    await pypck_client.received("$io:#LCN:disconnected")

    pypck_client.event_handler.assert_has_awaits(
        [
            asynctest.mock.call("lcn-connection-status-changed"),
            asynctest.mock.call("lcn-disconnected"),
        ]
    )


@pytest.mark.asyncio
async def test_connection_lost(pchk_server, pypck_client):
    """Test pchk server connection close."""
    pypck_client.event_handler = asynctest.CoroutineMock()
    await pypck_client.async_connect()

    await pchk_server.stop()
    # ensure that pypck_client is about to be closed
    await pypck_client.wait_closed()

    pypck_client.event_handler.assert_has_awaits(
        [asynctest.mock.call("connection-lost")]
    )


@pytest.mark.asyncio
async def test_segment_coupler_search(pchk_server, pypck_client):
    """Test segment coupler search."""
    await pypck_client.async_connect()
    await pypck_client.scan_segment_couplers(3, 0)

    assert await pchk_server.received(">G003003.SK")
    assert await pchk_server.received(">G003003.SK")
    assert await pchk_server.received(">G003003.SK")

    assert pypck_client.is_ready()


@pytest.mark.asyncio
async def test_segment_coupler_response(pchk_server, pypck_client):
    """Test segment coupler response."""
    await pypck_client.async_connect()

    assert pypck_client.local_seg_id == 0

    await pchk_server.send_message("=M000005.SK020")
    await pchk_server.send_message("=M021021.SK021")
    await pchk_server.send_message("=M022010.SK022")
    assert await pypck_client.received("=M000005.SK020")
    assert await pypck_client.received("=M021021.SK021")
    assert await pypck_client.received("=M022010.SK022")

    assert pypck_client.local_seg_id == 20
    assert set(pypck_client.segment_coupler_ids) == {20, 21, 22}


@pytest.mark.asyncio
async def test_module_scan(pchk_server, pypck_client):
    """Test module scan."""
    await pypck_client.async_connect()
    await pypck_client.scan_modules(3, 0)

    assert await pchk_server.received(">G000003!LEER")
    assert await pchk_server.received(">G000003!LEER")
    assert await pchk_server.received(">G000003!LEER")


@pytest.mark.asyncio
async def test_module_sn_response(pchk_server, pypck_client):
    """Test module scan."""
    await pypck_client.async_connect()
    module = pypck_client.get_address_conn(LcnAddr(0, 7, False))

    message = "=M000007.SN1AB20A123401FW190B11HW015"
    await pchk_server.send_message(message)
    assert await pypck_client.received(message)

    assert await module.serial_known
    assert module.hardware_serial == 0x1AB20A1234
    assert module.manu == 1
    assert module.software_serial == 0x190B11
    assert module.hardware_type.value == 15


@pytest.mark.asyncio
async def test_send_command_to_server(pchk_server, pypck_client):
    """Test sending a command to the PCHK server."""
    await pypck_client.async_connect()
    message = ">M000007.PIN003"
    await pypck_client.send_command(message)
    assert await pchk_server.received(message)


@pytest.mark.asyncio
async def test_ping(pchk_server, pypck_client):
    """Test if pings are send."""
    await pypck_client.async_connect()
    assert await pchk_server.received("^ping0")


@pytest.mark.asyncio
async def test_add_address_connections(pypck_client):
    """Test if new address connections are added on request."""
    lcn_addr = LcnAddr(0, 10, False)
    assert lcn_addr not in pypck_client.address_conns

    addr_conn = pypck_client.get_address_conn(lcn_addr)
    assert isinstance(addr_conn, ModuleConnection)

    assert lcn_addr in pypck_client.address_conns


@pytest.mark.asyncio
async def test_add_address_connections_by_message(pchk_server, pypck_client):
    """Test if new address connections are added by received message."""
    await pypck_client.async_connect()
    lcn_addr = LcnAddr(0, 10, False)
    assert lcn_addr not in pypck_client.address_conns

    message = ":M000010A1050"
    await pchk_server.send_message(message)
    assert await pypck_client.received(message)

    assert lcn_addr in pypck_client.address_conns


@pytest.mark.asyncio
async def test_groups_static_membership_discovery(pchk_server, pypck_client):
    """Test module scan."""
    await pypck_client.async_connect()
    module = pypck_client.get_address_conn(LcnAddr(0, 10, False))

    task = asyncio.create_task(module.request_static_groups())
    assert await pchk_server.received(">M000010.GP")
    await pchk_server.send_message("=M000010.GP012011200051")
    assert await task == {
        LcnAddr(0, 11, True),
        LcnAddr(0, 200, True),
        LcnAddr(0, 51, True),
    }


@pytest.mark.asyncio
async def test_groups_dynamic_membership_discovery(pchk_server, pypck_client):
    """Test module scan."""
    await pypck_client.async_connect()
    module = pypck_client.get_address_conn(LcnAddr(0, 10, False))

    task = asyncio.create_task(module.request_dynamic_groups())
    assert await pchk_server.received(">M000010.GD")
    await pchk_server.send_message("=M000010.GD008011200051")
    assert await task == {
        LcnAddr(0, 11, True),
        LcnAddr(0, 200, True),
        LcnAddr(0, 51, True),
    }


@pytest.mark.asyncio
async def test_groups_membership_discovery(pchk_server, pypck_client):
    """Test module scan."""
    await pypck_client.async_connect()
    module = pypck_client.get_address_conn(LcnAddr(0, 10, False))

    task = asyncio.create_task(module.request_groups())
    assert await pchk_server.received(">M000010.GP")
    assert await pchk_server.received(">M000010.GD")
    await pchk_server.send_message("=M000010.GP012011200051")
    await pchk_server.send_message("=M000010.GD008015100052")
    assert await task == {
        LcnAddr(0, 11, True),
        LcnAddr(0, 200, True),
        LcnAddr(0, 51, True),
        LcnAddr(0, 15, True),
        LcnAddr(0, 100, True),
        LcnAddr(0, 52, True),
    }
