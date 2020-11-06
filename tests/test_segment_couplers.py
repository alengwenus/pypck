"""Segment coupler tests"""

import asyncio

import pytest


@pytest.mark.asyncio
async def test_segment_coupler_search(pchk_server, pypck_client):
    """Test segment coupler search."""
    await pypck_client.async_connect()
    await pypck_client.scan_segment_couplers(3, 0)

    assert await pchk_server.received(b">G003003.SK")
    assert await pchk_server.received(b">G003003.SK")
    assert await pchk_server.received(b">G003003.SK")


@pytest.mark.asyncio
async def test_segment_coupler_response(pchk_server, pypck_client):
    """Test segment coupler response."""
    await pypck_client.async_connect()

    assert pypck_client.local_seg_id == 0

    await pchk_server.send_message("=M000005.SK020")
    assert await pypck_client.received("=M000005.SK020")

    assert pypck_client.local_seg_id == 20
