"""Segment coupler tests"""

import pytest


@pytest.mark.asyncio
async def test_segment_coupler_search(pchk_server, pypck_client):
    """Test segment coupler search."""
    await pypck_client.async_connect()
    await pypck_client.scan_segment_couplers(3, 0)

    assert await pchk_server.received(b">G003003.SK")
    assert await pchk_server.received(b">G003003.SK")
    assert await pchk_server.received(b">G003003.SK")
