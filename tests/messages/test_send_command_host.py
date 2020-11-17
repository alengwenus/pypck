"""Tests for send command host."""

import asynctest
import pytest
from pypck.inputs import InputParser, ModSendCommandHost

# Unit tests


def test_input_parser():
    """Test parsing of command."""
    message = "+M004000010.SKH001002"
    inp = InputParser.parse(message)
    assert isinstance(inp[0], ModSendCommandHost)

    message = "+M004000010.SKH001002003004005006"
    inp = InputParser.parse(message)
    assert isinstance(inp[0], ModSendCommandHost)

    message = "+M004000010.SKH001002003004005006007008009010011012013014"
    inp = InputParser.parse(message)
    assert isinstance(inp[0], ModSendCommandHost)


@pytest.mark.parametrize(
    "pck, expected",
    [
        ("SKH001002", (1, 2)),
        ("SKH001002003004005006", (1, 2, 3, 4, 5, 6)),
        (
            "SKH001002003004005006007008009010011012013014",
            (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14),
        ),
        ("SKH001002003", (1, 2)),
        ("SKH001002003004", (1, 2)),
    ],
)
def test_parse_message_percent(pck, expected):
    """Parse output in percent status message."""
    message = f"+M004000010.{pck}"
    inp = ModSendCommandHost.try_parse(message)[0]
    assert inp.get_parameters() == expected


# Integration tests


@pytest.mark.asyncio
async def test_send_command_host(pchk_server, pypck_client, module10):
    """Send command host message."""
    module10.async_process_input = asynctest.CoroutineMock()
    await pypck_client.async_connect()

    message = "+M004000010.SKH001002"
    await pchk_server.send_message(message)
    assert await pypck_client.received(message)

    assert module10.async_process_input.called
    inp = module10.async_process_input.call_args[0][0]
    assert inp.get_parameters() == (1, 2)
