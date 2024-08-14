"""Module connection tests."""

from unittest.mock import patch

import pytest
from pypck.lcn_addr import LcnAddr
from pypck.module import ModuleConnection

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


@pytest.mark.asyncio
@pytest.mark.parametrize("text, parts", TEST_VECTORS.items())
async def test_dyn_text(pypck_client, text, parts):
    """dyn_text."""
    # await pypck_client.async_connect()
    module = pypck_client.get_address_conn(LcnAddr(0, 10, False))

    with patch.object(ModuleConnection, "send_command") as send_command:
        await module.dyn_text(3, text)

    send_command.assert_awaited()
    await_args = (call.args for call in send_command.await_args_list)
    _, commands = zip(*await_args)

    for i, part in enumerate(parts):
        assert f"GTDT4{i+1:d}".encode() + part in commands
