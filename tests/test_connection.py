"""Connection tests."""
# from unittest.mock import Mock

import pytest
from pypck.connection import PchkAuthenticationError, PchkLicenseError


@pytest.mark.asyncio
async def test_close_without_connect(pypck_client):
    """Test closing of PchkConnectionManager without connecting."""
    await pypck_client.async_close()


@pytest.mark.asyncio
async def test_authenticate(pchk_server, pypck_client):
    """Test authentication procedure."""
    await pypck_client.async_connect()


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
