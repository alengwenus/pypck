"""Connection tests."""
# from unittest.mock import Mock

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
    await pchk_server.send_message(b"$io:#LCN:connected")
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
    await pchk_server.send_message(b"$io:#LCN:disconnected")
    await pypck_client.received("$io:#LCN:disconnected")

    pypck_client.event_handler.assert_has_awaits(
        [
            asynctest.mock.call("lcn-connection-status-changed"),
            asynctest.mock.call("lcn-disconnected"),
        ]
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

    await pchk_server.send_message(b"=M000005.SK020")
    await pchk_server.send_message(b"=M021021.SK021")
    await pchk_server.send_message(b"=M022010.SK022")
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

    message = "=M000007.SN1AB20A123401FW190B11HW015"
    await pchk_server.send_message(message.encode())
    assert await pypck_client.received(message)

    module = pypck_client.get_address_conn(LcnAddr(0, 7, False))

    # assert await module.serial_known
    assert module.hardware_serial == 0x1AB20A1234
    assert module.manu == 1
    assert module.software_serial == 0x190B11
    assert module.hw_type == 15

