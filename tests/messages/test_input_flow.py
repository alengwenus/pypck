"""Test the data flow for Input objects."""
from unittest.mock import AsyncMock, patch

import pytest
from pypck.inputs import Input, ModInput
from pypck.lcn_addr import LcnAddr


@pytest.mark.asyncio
async def test_message_to_input(pypck_client):
    """Test data flow from message to input."""
    inp = Input()
    message = "dummy_message"
    pypck_client.async_process_input = AsyncMock()
    with patch("pypck.inputs.InputParser.parse", return_value=[inp]) as inp_parse:
        await pypck_client.process_message(message)

    inp_parse.assert_called_with(message)
    pypck_client.async_process_input.assert_awaited_with(inp)


@pytest.mark.asyncio
async def test_physical_to_logical_segment_id(pypck_client):
    """Test conversion from logical to physical segment id."""
    pypck_client.local_seg_id = 20
    module = pypck_client.get_address_conn(LcnAddr(20, 7, False))
    module.async_process_input = AsyncMock()

    with patch("tests.conftest.MockPchkConnectionManager.is_ready", result=True):
        inp = ModInput(LcnAddr(20, 7, False))
        await pypck_client.async_process_input(inp)

        inp = ModInput(LcnAddr(0, 7, False))
        await pypck_client.async_process_input(inp)

        inp = ModInput(LcnAddr(4, 7, False))
        await pypck_client.async_process_input(inp)

        assert module.async_process_input.await_count == 3
