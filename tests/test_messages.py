"""Tests for input message parsing for bus messages."""

import pytest
from pypck.inputs import (
    InputParser,
    ModAck,
    ModNameComment,
    ModSendCommandHost,
    ModSk,
    ModSn,
    ModStatusBinSensors,
    ModStatusGroups,
    ModStatusKeyLocks,
    ModStatusLedsAndLogicOps,
    ModStatusOutput,
    ModStatusOutputNative,
    ModStatusRelays,
    ModStatusVar,
)
from pypck.lcn_addr import LcnAddr
from pypck.lcn_defs import (
    HardwareType,
    LedStatus,
    LogicOpStatus,
    OutputPort,
    Var,
    VarValue,
)

MESSAGES = {
    # Ack
    "-M000010!": (ModAck, -1),
    "-M000010005": (ModAck, 5),
    # SK
    "=M000010.SK007": (ModSk, 7),
    # SN
    "=M000010.SN1AB20A123401FW190B11HW015": (
        ModSn,
        0x1AB20A1234,
        0x1,
        0x190B11,
        HardwareType.SH_PLUS,
    ),
    "=M000010.SN1234567890AFFW190011HW011": (
        ModSn,
        0x1234567890,
        0xAF,
        0x190011,
        HardwareType.UPP,
    ),
    # Name
    "=M000010.N1EG HWR Hau": (ModNameComment, "N", 0, "EG HWR Hau"),
    "=M000010.N2EG HWR Hau": (ModNameComment, "N", 1, "EG HWR Hau"),
    # Comment
    "=M000010.K1EG HWR Hau": (ModNameComment, "K", 0, "EG HWR Hau"),
    "=M000010.K2EG HWR Hau": (ModNameComment, "K", 1, "EG HWR Hau"),
    "=M000010.K3EG HWR Hau": (ModNameComment, "K", 2, "EG HWR Hau"),
    # Oem
    "=M000010.O1EG HWR Hau": (ModNameComment, "O", 0, "EG HWR Hau"),
    "=M000010.O2EG HWR Hau": (ModNameComment, "O", 1, "EG HWR Hau"),
    "=M000010.O3EG HWR Hau": (ModNameComment, "O", 2, "EG HWR Hau"),
    "=M000010.O4EG HWR Hau": (ModNameComment, "O", 3, "EG HWR Hau"),
    # Groups
    "=M000010.GP012005040": (
        ModStatusGroups,
        False,
        12,
        [LcnAddr(0, 5, True), LcnAddr(0, 40, True)],
    ),
    "=M000010.GD008005040": (
        ModStatusGroups,
        True,
        8,
        [LcnAddr(0, 5, True), LcnAddr(0, 40, True)],
    ),
    "=M000010.GD010005040030020010100200150099201": (
        ModStatusGroups,
        True,
        10,
        [
            LcnAddr(0, 5, True),
            LcnAddr(0, 40, True),
            LcnAddr(0, 30, True),
            LcnAddr(0, 20, True),
            LcnAddr(0, 10, True),
            LcnAddr(0, 100, True),
            LcnAddr(0, 200, True),
            LcnAddr(0, 150, True),
            LcnAddr(0, 99, True),
            LcnAddr(0, 201, True),
        ],
    ),
    # Status Output
    ":M000010A1050": (ModStatusOutput, OutputPort.OUTPUT1.value, 50.0),
    # Status Output Native
    ":M000010O1050": (ModStatusOutputNative, OutputPort.OUTPUT1.value, 50),
    # Status Relays
    ":M000010Rx204": (
        ModStatusRelays,
        [False, False, True, True, False, False, True, True],
    ),
    # Status BinSensors
    ":M000010Bx204": (
        ModStatusBinSensors,
        [False, False, True, True, False, False, True, True],
    ),
    # Status Var
    "%M000010.A00301200": (ModStatusVar, Var.VAR3, VarValue(1200)),
    "%M000010.01200": (ModStatusVar, Var.UNKNOWN, VarValue(1200)),
    "%M000010.S101200": (ModStatusVar, Var.R1VARSETPOINT, VarValue(1200)),
    "%M000010.T1100050": (ModStatusVar, Var.THRS1, VarValue(50)),
    "%M000010.T3400050": (ModStatusVar, Var.THRS3_4, VarValue(50)),
    # Status Leds and LogicOps
    "=M000010.TLAEBFAAAAAAAANTVN": (
        ModStatusLedsAndLogicOps,
        [
            LedStatus.OFF,
            LedStatus.ON,
            LedStatus.BLINK,
            LedStatus.FLICKER,
            LedStatus.OFF,
            LedStatus.OFF,
            LedStatus.OFF,
            LedStatus.OFF,
            LedStatus.OFF,
            LedStatus.OFF,
            LedStatus.OFF,
            LedStatus.OFF,
        ],
        [LogicOpStatus.NONE, LogicOpStatus.SOME, LogicOpStatus.ALL, LogicOpStatus.NONE],
    ),
    # Status Key Locks
    "=M000010.TX255000063204": (
        ModStatusKeyLocks,
        [
            [True, True, True, True, True, True, True, True],
            [False, False, False, False, False, False, False, False],
            [True, True, True, True, True, True, False, False],
            [False, False, True, True, False, False, True, True],
        ],
    ),
    # SKH
    "+M004000010.SKH000001": (ModSendCommandHost, (0, 1)),
    "+M004000010.SKH000001002003004005": (
        ModSendCommandHost,
        tuple(i for i in range(6)),
    ),
    "+M004000010.SKH000001002003004005006007008009010011012013": (
        ModSendCommandHost,
        tuple(i for i in range(14)),
    ),
    # SKH with partially invalid data
    "+M004000010.SKH000001002": (ModSendCommandHost, (0, 1)),
    "+M004000010.SKH000001002003": (ModSendCommandHost, (0, 1)),
    "+M004000010.SKH000001002003004005006": (
        ModSendCommandHost,
        tuple(i for i in range(6)),
    ),
}


@pytest.mark.parametrize("message, expected", MESSAGES.items())
def test_message_parsing_single_mod_input(message, expected):
    """Test if InputMod parses message correctly."""
    exp = (expected[0])(LcnAddr(0, 10, False), *expected[1:])
    inp = InputParser.parse(message)
    assert len(inp) == 1
    assert type(inp[0]) == type(exp)  # pylint: disable=unidiomatic-typecheck
    assert vars(inp[0]) == vars(exp)
