"""Test the data flow for Input objects."""

from unittest.mock import patch

import asynctest
import pytest
from pypck.inputs import Input


@pytest.mark.asyncio
async def test_message_to_input(pypck_client):
    """Test data flow from message to input."""
    inp = Input()
    message = "dummy_message"
    pypck_client.async_process_input = asynctest.CoroutineMock()
    with patch("pypck.inputs.InputParser.parse", return_value=[inp]) as inp_parse:
        await pypck_client.process_message(message)

    inp_parse.assert_called_with(message)
    pypck_client.async_process_input.assert_awaited_with(inp)
