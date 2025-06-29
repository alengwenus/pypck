"""Tests for output status messages."""

from unittest.mock import patch

import pytest

from pypck.inputs import InputParser, ModStatusOutput, ModStatusOutputNative
from pypck.module import ModuleConnection

from ..conftest import MockPchkConnectionManager
from ..mock_pchk import MockPchkServer

# Unit tests


def test_input_parser() -> None:
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
def test_parse_message_percent(pck: str, expected: tuple[int, float]) -> None:
    """Parse output in percent status message."""
    message = f":M000010{pck}"
    inp = InputParser.parse(message)[0]
    assert isinstance(inp, ModStatusOutput)
    assert inp.get_output_id() == expected[0]
    assert inp.get_percent() == expected[1]


@pytest.mark.parametrize(
    "pck, expected",
    [("O1000", (0, 0)), ("O2050", (1, 50)), ("O3100", (2, 100)), ("O4200", (3, 200))],
)
def test_parse_message_native(pck: str, expected: tuple[int, int]) -> None:
    """Parse output in native units status message."""
    message = f":M000010{pck}"
    inp = InputParser.parse(message)[0]
    assert isinstance(inp, ModStatusOutputNative)
    assert inp.get_output_id() == expected[0]
    assert inp.get_value() == expected[1]


# Integration tests


@pytest.mark.asyncio
async def test_output_status(
    pchk_server: MockPchkServer,
    pypck_client: MockPchkConnectionManager,
    module10: ModuleConnection,
) -> None:
    """Output status command."""
    with patch.object(module10, "async_process_input") as module10_process_input:
        await pypck_client.async_connect()

        message = ":M000010A1050"
        await pchk_server.send_message(message)
        assert await pypck_client.received(message)

        assert module10_process_input.called
        inp = module10_process_input.call_args[0][0]
        assert inp.get_output_id() == 0
        assert inp.get_percent() == 50.0
