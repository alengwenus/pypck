"""Tests for send command host."""

from unittest.mock import patch

import pytest

from pypck.inputs import InputParser, ModSendCommandHost
from pypck.module import ModuleConnection

from ..conftest import MockPchkConnectionManager
from ..mock_pchk import MockPchkServer

# Unit tests


def test_input_parser() -> None:
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
def test_parse_message_percent(pck: str, expected: tuple[int, ...]) -> None:
    """Parse output in percent status message."""
    message = f"+M004000010.{pck}"
    inp = InputParser.parse(message)[0]
    assert isinstance(inp, ModSendCommandHost)
    assert inp.get_parameters() == expected


# Integration tests


@pytest.mark.asyncio
async def test_send_command_host(
    pchk_server: MockPchkServer,
    pypck_client: MockPchkConnectionManager,
    module10: ModuleConnection,
) -> None:
    """Send command host message."""
    with patch.object(module10, "async_process_input") as module10_process_input:
        await pypck_client.async_connect()

        message = "+M004000010.SKH001002"
        await pchk_server.send_message(message)
        assert await pypck_client.received(message)

        assert module10_process_input.called
        inp = module10_process_input.call_args[0][0]
        assert inp.get_parameters() == (1, 2)
