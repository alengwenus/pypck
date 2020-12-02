"""Test the data flow for Input objects."""
import sys
from unittest.mock import patch

import pytest
from pypck.inputs import Input

if sys.version_info.minor >= 8:
    from unittest.mock import AsyncMock
else:
    from asynctest.mock import CoroutineMock as AsyncMock


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
