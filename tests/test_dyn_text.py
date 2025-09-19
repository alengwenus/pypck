"""Module connection tests."""

import pytest
from pypck.lcn_addr import LcnAddr

from .conftest import MockPchkConnectionManager

TEST_VECTORS = {
    # empty
    "": (b"", b"", b"", b"", b""),
    # pure ascii
    **{"a" * n: (b"a" * n, b"", b"", b"", b"") for n in (1, 7, 11, 12)},
    **{"a" * (12 + n): (b"a" * 12, b"a" * n, b"", b"", b"") for n in (1, 7, 11, 12)},
    **{
        "a" * (48 + n): (b"a" * 12, b"a" * 12, b"a" * 12, b"a" * 12, b"a" * n)
        for n in (1, 7, 11, 12)
    },
    # only two-byte UTF-8
    **{"ü" * n: (b"\xc3\xbc" * n, b"", b"", b"", b"") for n in (1, 5, 6)},
    **{
        "ü" * (6 + n): (b"\xc3\xbc" * 6, b"\xc3\xbc" * n, b"", b"", b"")
        for n in (1, 5, 6)
    },
    **{
        "ü" * (24 + n): (
            b"\xc3\xbc" * 6,
            b"\xc3\xbc" * 6,
            b"\xc3\xbc" * 6,
            b"\xc3\xbc" * 6,
            b"\xc3\xbc" * n,
        )
        for n in (1, 5, 6)
    },
    # only three-byte utf-8
    **{"\u20ac" * n: (b"\xe2\x82\xac" * n, b"", b"", b"", b"") for n in (1, 4)},
    **{
        "\u20ac" * (4 + n): (b"\xe2\x82\xac" * 4, b"\xe2\x82\xac" * n, b"", b"", b"")
        for n in (1, 4)
    },
    **{
        "\u20ac" * (16 + n): (
            b"\xe2\x82\xac" * 4,
            b"\xe2\x82\xac" * 4,
            b"\xe2\x82\xac" * 4,
            b"\xe2\x82\xac" * 4,
            b"\xe2\x82\xac" * n,
        )
        for n in (1, 4)
    },
    # boundary-crossing utf-8
    "12345678123\u00fc4567": (b"12345678123\xc3", b"\xbc4567", b"", b"", b""),
    "12345678123\u20ac4567": (b"12345678123\xe2", b"\x82\xac4567", b"", b"", b""),
    "1234567812\u20ac34567": (b"1234567812\xe2\x82", b"\xac34567", b"", b"", b""),
}


@pytest.mark.parametrize("text, parts", TEST_VECTORS.items())
async def test_dyn_text(
    pypck_client: MockPchkConnectionManager,
    text: str,
    parts: tuple[bytes, bytes, bytes, bytes, bytes],
) -> None:
    """Tests for dynamic text."""
    module = pypck_client.get_device_connection(LcnAddr(0, 10, False))

    await module.dyn_text(3, text)

    module.send_command.assert_awaited()  # type: ignore[attr-defined]
    await_args = (call.args for call in module.send_command.await_args_list)  # type: ignore[attr-defined]
    _, commands = zip(*await_args)

    for i, part in enumerate(parts):
        assert f"GTDT4{i + 1:d}".encode() + part in commands
