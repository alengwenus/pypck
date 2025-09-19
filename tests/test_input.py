"""Test the data flow for Input objects."""

from unittest.mock import patch

from pypck.inputs import Input, ModInput
from pypck.lcn_addr import LcnAddr

from .conftest import MockPchkConnectionManager


async def test_message_to_input(pypck_client: MockPchkConnectionManager) -> None:
    """Test data flow from message to input."""
    inp = Input()
    message = "dummy_message"
    with patch.object(
        pypck_client, "async_process_input"
    ) as pypck_client_process_input:
        with patch("pypck.inputs.InputParser.parse", return_value=[inp]) as inp_parse:
            await pypck_client.process_message(message)

        inp_parse.assert_called_with(message)
        pypck_client_process_input.assert_awaited_with(inp)


async def test_physical_to_logical_segment_id(
    pypck_client: MockPchkConnectionManager,
) -> None:
    """Test conversion from logical to physical segment id."""
    pypck_client.local_seg_id = 20
    module = pypck_client.get_device_connection(LcnAddr(20, 7, False))
    assert module.is_group is False
    with (
        patch("tests.conftest.MockPchkConnectionManager.is_ready", return_value=True),
        patch.object(module, "async_process_input") as module_process_input,
    ):
        inp = ModInput(LcnAddr(20, 7, False))
        await pypck_client.async_process_input(inp)

        inp = ModInput(LcnAddr(0, 7, False))
        await pypck_client.async_process_input(inp)

        inp = ModInput(LcnAddr(4, 7, False))
        await pypck_client.async_process_input(inp)

        assert module_process_input.await_count == 3
