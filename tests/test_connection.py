"""Connection tests."""
# from unittest.mock import Mock

import asyncio

import pytest
from pypck.connection import (
    PchkAuthenticationError,
    PchkConnectionManager,
    PchkLicenseError
)

from .conftest import HOST, PASSWORD, PORT, USERNAME


@pytest.mark.asyncio
async def test_close_without_connect():
    """Test closing of PchkConnectionManager without connecting."""
    loop = None
    pcm = PchkConnectionManager(
        loop, HOST, PORT, USERNAME, PASSWORD,
        settings={'SK_NUM_TRIES': 0})
    await pcm.async_close()


@pytest.mark.asyncio
async def test_authenticate(pchk_server):
    """Test authentication procedure."""
    loop = None
    pcm = PchkConnectionManager(
        loop, HOST, PORT, USERNAME, PASSWORD,
        settings={'SK_NUM_TRIES': 0})
    await pcm.async_connect()
    await pcm.async_close()


@pytest.mark.asyncio
async def test_authentication_error(pchk_server):
    """Test wrong login credentials."""
    loop = None
    pcm = PchkConnectionManager(
        loop, HOST, PORT, USERNAME, 'wrong_password',
        settings={'SK_NUM_TRIES': 0})
    with pytest.raises(PchkAuthenticationError):
        await pcm.async_connect()
    await pcm.async_close()


@pytest.mark.asyncio
async def test_license_error(pchk_server, pypck_client):
    """Test license error."""
    pchk_server.set_license_error(True)

    with pytest.raises(PchkLicenseError):
        await pypck_client.async_connect()


@pytest.mark.asyncio
async def test_segment_coupler_search(pchk_server, pypck_client):
    """Test license error."""
    await pypck_client.async_connect()
    await pypck_client.scan_segment_couplers(3, 0)

    assert await pchk_server.received(b'>G003003.SK')
    assert await pchk_server.received(b'>G003003.SK')
    assert await pchk_server.received(b'>G003003.SK')


# @pytest.mark.asyncio
# async def test_authenticate(pchk_server, pypck_client):
#     await pypck_client.async_connect()
