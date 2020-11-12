"""Tests for output status messages."""

import asynctest
import pytest
from pypck.inputs import InputParser, ModStatusOutput, ModStatusOutputNative

# Unit tests


def test_input_parser():
    """Test parsing of command."""
    message = ":M000010A1050"
    inp = InputParser.parse(message)
    assert isinstance(inp[0], ModStatusOutput)

    message = ":M000010O1050"
    inp = InputParser.parse(message)
    assert isinstance(inp[0], ModStatusOutputNative)


@pytest.mark.parametrize(
    "pck, expected",
    [
        ("A1000", (0, 0.0)),
        ("A2050", (1, 50.0)),
        ("A3075", (2, 75.0)),
        ("A4100", (3, 100.0)),
    ],
)
def test_parse_message_percent(pck, expected):
    """Parse output in percent status message."""
    message = f":M000010{pck}"
    inp = ModStatusOutput.try_parse(message)[0]
    assert inp.get_output_id() == expected[0]
    assert inp.get_percent() == expected[1]


@pytest.mark.parametrize(
    "pck, expected",
    [("O1000", (0, 0)), ("O2050", (1, 50)), ("O3100", (2, 100)), ("O4200", (3, 200))],
)
def test_parse_message_native(pck, expected):
    """Parse output in native units status message."""
    message = f":M000010{pck}"
    inp = ModStatusOutputNative.try_parse(message)[0]
    assert inp.get_output_id() == expected[0]
    assert inp.get_value() == expected[1]


# Integration tests


@pytest.mark.asyncio
async def test_output_status(pchk_server, pypck_client, module10):
    """Output status command."""
    module10.async_process_input = asynctest.CoroutineMock()
    await pypck_client.async_connect()

    message = ":M000010A1050"
    await pchk_server.send_message(message)
    assert await pypck_client.received(message)

    assert module10.async_process_input.called
    inp = module10.async_process_input.call_args[0][0]
    assert inp.get_output_id() == 0
    assert inp.get_percent() == 50.0
