"""Definitions and constants for pypck."""

from __future__ import annotations

import math
import re
from enum import Enum, auto
from typing import Any, no_type_check

LCN_ENCODING = "utf-8"
PATTERN_SPLIT_PORT_PIN = re.compile(r"(?P<port>[a-zA-Z]+)(?P<pin>\d+)")


def split_port_pin(portpin: str) -> tuple[str, int]:
    """Split the port and the pin from the given input string.

    :param    str    portpin:    Input string
    """
    res = PATTERN_SPLIT_PORT_PIN.findall(portpin)
    return res[0][0], int(res[0][1])


class OutputPort(Enum):
    """Output port of LCN module."""

    OUTPUT1 = 0
    OUTPUT2 = 1
    OUTPUT3 = 2
    OUTPUT4 = 3

    OUTPUTUP = 0
    OUTPUTDOWN = 1


class RelayPort(Enum):
    """Relay port of LCN module."""

    RELAY1 = 0
    RELAY2 = 1
    RELAY3 = 2
    RELAY4 = 3
    RELAY5 = 4
    RELAY6 = 5
    RELAY7 = 6
    RELAY8 = 7

    MOTORONOFF1 = 0
    MOTORUPDOWN1 = 1
    MOTORONOFF2 = 2
    MOTORUPDOWN2 = 3
    MOTORONOFF3 = 4
    MOTORUPDOWN3 = 5
    MOTORONOFF4 = 6
    MOTORUPDOWN4 = 7


class MotorPort(Enum):
    """Motor ports of LCN module."""

    MOTOR1 = 0
    MOTOR2 = 1
    MOTOR3 = 2
    MOTOR4 = 3
    OUTPUTS = 4


class LedPort(Enum):
    """LED port of LCN module."""

    LED1 = 0
    LED2 = 1
    LED3 = 2
    LED4 = 3
    LED5 = 4
    LED6 = 5
    LED7 = 6
    LED8 = 7
    LED9 = 8
    LED10 = 9
    LED11 = 10
    LED12 = 11


class LogicOpPort(Enum):
    """Logic Operation port of LCN module."""

    LOGICOP1 = 0
    LOGICOP2 = 1
    LOGICOP3 = 2
    LOGICOP4 = 3


class BinSensorPort(Enum):
    """Binary sensor port of LCN module."""

    BINSENSOR1 = 0
    BINSENSOR2 = 1
    BINSENSOR3 = 2
    BINSENSOR4 = 3
    BINSENSOR5 = 4
    BINSENSOR6 = 5
    BINSENSOR7 = 6
    BINSENSOR8 = 7


class Key(Enum):
    """Keys of LCN module."""

    A1 = 0
    A2 = 1
    A3 = 2
    A4 = 3
    A5 = 4
    A6 = 5
    A7 = 6
    A8 = 7

    B1 = 8
    B2 = 9
    B3 = 10
    B4 = 11
    B5 = 12
    B6 = 13
    B7 = 14
    B8 = 15

    C1 = 16
    C2 = 17
    C3 = 18
    C4 = 19
    C5 = 20
    C6 = 21
    C7 = 22
    C8 = 23

    D1 = 24
    D2 = 25
    D3 = 26
    D4 = 27
    D5 = 28
    D6 = 29
    D7 = 30
    D8 = 31


class KeyAction(Enum):
    """Action types for LCN keys."""

    HIT = "hit"
    MAKE = "make"
    BREAK = "break"


class BatteryStatus(Enum):
    """Battery status."""

    WEAK = "weak"
    FULL = "full"


class OutputPortDimMode(Enum):
    """LCN dimming mode.

    If solely modules with firmware 170206 or newer are present, LCN-PRO
    automatically programs STEPS200.
    Otherwise the default is STEPS50.
    Since LCN-PCHK doesn't know the current mode, it must explicitly be set.
    """

    STEPS50 = 0  # 0..50 dimming steps (all LCN module generations)
    STEPS200 = 1  # 0..200 dimming steps (since 170206)


class OutputPortStatusMode(Enum):
    """Tells LCN-PCHK how to format output-port status-messages.

    PERCENT: allows to show the status in half-percent steps (e.g. "10.5").
    NATIVE: is completely backward compatible and there are no restrictions
    concerning the LCN module generations. It requires LCN-PCHK 2.3 or higher
    though.
    """

    PERCENT = "P"  # Default (compatible with all versions of LCN-PCHK)
    NATIVE = "N"  # 0..200 steps (since LCN-PCHK 2.3)


def time_to_ramp_value(time_msec: int) -> int:
    """Convert the given time into an LCN ramp value.

    :param    int    time_msec:    The time in milliseconds.

    :returns: The (LCN-internal) ramp value (0..250).
    :rtype: int
    """
    if time_msec < 250:
        ret = 0
    elif time_msec < 500:
        ret = 1
    elif time_msec < 660:
        ret = 2
    elif time_msec < 1000:
        ret = 3
    elif time_msec < 1400:
        ret = 4
    elif time_msec < 2000:
        ret = 5
    elif time_msec < 3000:
        ret = 6
    elif time_msec < 4000:
        ret = 7
    elif time_msec < 5000:
        ret = 8
    elif time_msec < 6000:
        ret = 9
    else:
        ramp = (time_msec / 1000 - 6) / 2 + 10
        ramp = min(ramp, 250)
        ret = int(ramp)
    return ret


def ramp_value_to_time(ramp_value: int) -> int:
    """Convert the given LCN ramp value into a time.

    :param    int    ramp_value:    The LCN ramp value (0..250).

    :returns: The ramp time in milliseconds.
    :rtype: int
    """
    if not 0 <= ramp_value <= 250:
        raise ValueError("Ramp value has to be in range 0..250")

    if ramp_value < 10:
        times = [0, 250, 500, 660, 1000, 1400, 2000, 3000, 4000, 5000]
        ramp_time = times[ramp_value]
    else:
        ramp_time = int(((ramp_value - 10) * 2 + 6) * 1000)
    return ramp_time


def time_to_native_value(time_msec: int) -> int:
    """Convert time to native LCN time value.

    Scales the given time value in milliseconds to a byte value (0..255).
    Used for RelayTimer.

    :param    int    time_msec:    Duration of timer in milliseconds

    :returns: The duration in native LCN units
    :rtype: int
    """
    if not 0 <= time_msec <= 240960:
        raise ValueError("Time has to be in range 0..240960ms")
    time_scaled = time_msec / (1000 * 0.03 * 32.0) + 1.0

    pre_decimal = int(time_scaled).bit_length() - 1
    decimal = time_scaled / (1 << pre_decimal) - 1

    value = pre_decimal + decimal
    return int(32 * value)


def native_value_to_time(value: int) -> int:
    """Convert native LCN value to time.

    Scales the given byte value (0..255) to a time value in milliseconds.

    :param    int    value:    Duration of timer in native LCN units

    :returns: The duration in milliseconds
    :rtype: int
    """
    if not 0 <= value <= 255:
        raise ValueError("Value has to be in range 0..255")
    pre_decimal = value // 32
    decimal = value / 32 - pre_decimal

    time_scaled = (1 << pre_decimal) * (decimal + 1)

    time_msec = (time_scaled - 1) * 1000 * 0.03 * 32
    return int(time_msec)


def motor_position_time_to_native_value(time_msec: int) -> int:
    """Convert time to native LCN time value.

    Scales the given time value in milliseconds to a two-byte value.

    :param    int    time_msec:    Duration of timer in milliseconds (1001..65535000)

    :returns: The duration in native LCN units
    :rtype: int
    """
    if not 1001 <= time_msec <= 65535000:
        raise ValueError("Time has to be in range 1001..65535000ms")
    value = 0xFFFF * 1000 / time_msec
    return int(value)


def native_value_to_motor_position_time(value: int) -> int:
    """Convert native LCN value to time.

    Scales the given two-byte value (1..65535) to a time value in milliseconds.

    :param    int    value:    Duration of timer in native LCN units

    :returns: The duration in milliseconds
    :rtype: int
    """
    if not 1 <= value <= 0xFFFF:
        raise ValueError("Value has to be in range 1..65535")

    time_msec = 0xFFFF * 1000 / value
    return int(time_msec)


class Var(Enum):
    """LCN variable types."""

    UNKNOWN = -1  # Used if the real type is not known (yet)
    VAR1ORTVAR = 0
    TVAR = 0
    VAR1 = 0
    VAR2ORR1VAR = 1
    R1VAR = 1
    VAR2 = 1
    VAR3ORR2VAR = 2
    R2VAR = 2
    VAR3 = 2
    VAR4 = 3
    VAR5 = 4
    VAR6 = 5
    VAR7 = 6
    VAR8 = 7
    VAR9 = 8
    VAR10 = 9
    VAR11 = 10
    VAR12 = 11  # Since 170206
    R1VARSETPOINT = auto()
    R2VARSETPOINT = auto()  # Set-points for regulators
    THRS1 = auto()
    THRS2 = auto()
    THRS3 = auto()
    THRS4 = auto()
    THRS5 = auto()  # Register 1 (THRS5 only before 170206)
    THRS2_1 = auto()
    THRS2_2 = auto()
    THRS2_3 = auto()
    THRS2_4 = auto()  # Register 2 (since 2012)
    THRS3_1 = auto()
    THRS3_2 = auto()
    THRS3_3 = auto()
    THRS3_4 = auto()  # Register 3 (since 2012)
    THRS4_1 = auto()
    THRS4_2 = auto()
    THRS4_3 = auto()
    THRS4_4 = auto()  # Register 4 (since 2012)
    S0INPUT1 = auto()
    S0INPUT2 = auto()
    S0INPUT3 = auto()
    S0INPUT4 = auto()  # LCN-BU4LJVarValue

    @classmethod
    def variables(cls) -> list[Var]:
        """Return a list of all variable types."""
        return [
            cls.VAR1ORTVAR,
            cls.VAR2ORR1VAR,
            cls.VAR3ORR2VAR,
            cls.VAR4,
            cls.VAR5,
            cls.VAR6,
            cls.VAR7,
            cls.VAR8,
            cls.VAR9,
            cls.VAR10,
            cls.VAR11,
            cls.VAR12,
        ]

    @classmethod
    def variables_new(cls) -> list[Var]:
        """Return a list of all new variable types (firmware >=0x170206)."""
        return cls.variables()

    @classmethod
    def variables_old(cls) -> list[Var]:
        """Return a list of all variable types (firmware <0x170206)."""
        return cls.variables()[:3]

    @classmethod
    def set_points(cls) -> list[Var]:
        """Return a list of all set-point variable types."""
        return [cls.R1VARSETPOINT, cls.R2VARSETPOINT]

    @classmethod
    def thresholds(cls) -> list[list[Var]]:
        """Return a list of all threshold variable types."""
        return [
            [cls.THRS1, cls.THRS2, cls.THRS3, cls.THRS4, cls.THRS5],
            [cls.THRS2_1, cls.THRS2_2, cls.THRS2_3, cls.THRS2_4],
            [cls.THRS3_1, cls.THRS3_2, cls.THRS3_3, cls.THRS3_4],
            [cls.THRS4_1, cls.THRS4_2, cls.THRS4_3, cls.THRS4_4],
        ]

    @classmethod
    def thresholds_new(cls) -> list[list[Var]]:
        """Return a list of all threshold variable types (firmware >=0x170206)."""
        return [cls.thresholds()[0][:4], *cls.thresholds()[1:]]

    @classmethod
    def thresholds_old(cls) -> list[list[Var]]:
        """Return a list of all old threshold variable types (firmware <0x170206)."""
        return [cls.thresholds()[0]]

    @classmethod
    def s0s(cls) -> list[Var]:
        """Return a list of all S0-input variable types."""
        return [cls.S0INPUT1, cls.S0INPUT2, cls.S0INPUT3, cls.S0INPUT4]

    @staticmethod
    def var_id_to_var(var_id: int) -> Var:
        """Translate a given id into a variable type.

        :param    int    varId:    The variable id (0..11)

        :returns: The translated variable enum.
        :rtype: Var
        """
        if (var_id < 0) or (var_id >= len(Var.variables())):
            raise ValueError("Bad var_id.")
        return Var.variables()[var_id]

    @staticmethod
    def set_point_id_to_var(set_point_id: int) -> Var:
        """Translate a given id into a LCN set-point variable type.

        :param     int    set_point_id:    Set-point id 0..1

        :return: The translated var
        :rtype:  Var
        """
        if (set_point_id < 0) or (set_point_id >= len(Var.set_points())):
            raise ValueError("Bad set_point_id.")
        return Var.set_points()[set_point_id]

    @staticmethod
    def thrs_id_to_var(register_id: int, thrs_id: int) -> Var:
        """Translate given ids into a LCN threshold variable type.

        :param    int    register_id:    Register id 0..3
        :param    int    thrs_id:        Threshold id 0..4 for register 0,
                                                      0..3 for registers 1..3

        :return: The translated var
        :rtype:    Var
        """
        if (
            (register_id < 0)
            or (register_id >= len(Var.thresholds()))
            or (thrs_id < 0)
            or (thrs_id >= (5 if (register_id == 0) else 4))
        ):
            raise ValueError("Bad register_id and/or thrs_id.")
        return Var.thresholds()[register_id][thrs_id]

    @staticmethod
    def s0_id_to_var(s0_id: int) -> Var:
        """Translate a given id into a LCN S0-input variable type.

        :param     int    s0_id:     S0 id 0..3

        :return:    The translated var
        :rtype:     Var
        """
        if (s0_id < 0) or (s0_id >= len(Var.s0s())):
            raise ValueError("Bad s0_id.")
        return Var.s0s()[s0_id]

    @staticmethod
    def to_var_id(var: Var) -> int:
        """Translate a given variable type into a variable id.

        :param     Var    var:    The variable type to translate

        :return:     Variable id 0..11 or -1 if wrong type
        :rtype:    int
        """
        if var == Var.VAR1ORTVAR:
            var_id = 0
        elif var == Var.VAR2ORR1VAR:
            var_id = 1
        elif var == Var.VAR3ORR2VAR:
            var_id = 2
        elif var == Var.VAR4:
            var_id = 3
        elif var == Var.VAR5:
            var_id = 4
        elif var == Var.VAR6:
            var_id = 5
        elif var == Var.VAR7:
            var_id = 6
        elif var == Var.VAR8:
            var_id = 7
        elif var == Var.VAR9:
            var_id = 8
        elif var == Var.VAR10:
            var_id = 9
        elif var == Var.VAR11:
            var_id = 10
        elif var == Var.VAR12:
            var_id = 11
        else:
            var_id = -1
        return var_id

    @staticmethod
    def to_set_point_id(var: Var) -> int:
        """Translate a given variable type into a set-point id.

        :param     Var    var:     The variable type to translate

        :return:    Variable id 0..1 or -1 if wrong type
        :rtype:    int
        """
        if var == Var.R1VARSETPOINT:
            set_point_id = 0
        elif var == Var.R2VARSETPOINT:
            set_point_id = 1
        else:
            set_point_id = -1
        return set_point_id

    @staticmethod
    def to_thrs_register_id(var: Var) -> int:
        """Translate a given variable type into a threshold register id.

        :param    Var    var:    The variable type to translate

        :return:    Register id 0..3 or -1 if wrong type
        :rtype:    int
        """
        if var in [Var.THRS1, Var.THRS2, Var.THRS3, Var.THRS4, Var.THRS5]:
            thrs_register_id = 0
        elif var in [Var.THRS2_1, Var.THRS2_2, Var.THRS2_3, Var.THRS2_4]:
            thrs_register_id = 1
        elif var in [Var.THRS3_1, Var.THRS3_2, Var.THRS3_3, Var.THRS3_4]:
            thrs_register_id = 2
        elif var in [Var.THRS4_1, Var.THRS4_2, Var.THRS4_3, Var.THRS4_4]:
            thrs_register_id = 3
        else:
            thrs_register_id = -1
        return thrs_register_id

    @staticmethod
    def to_thrs_id(var: Var) -> int:
        """Translate a given variable type into a threshold id.

        :param    Var    var:    The variable type to translate

        :return:    Threshold id 0..4 or -1 if wrong type
        :rtype:    int
        """
        if var in [Var.THRS1, Var.THRS2_1, Var.THRS3_1, Var.THRS4_1]:
            thrs_id = 0
        elif var in [Var.THRS2, Var.THRS2_2, Var.THRS3_2, Var.THRS4_2]:
            thrs_id = 1
        elif var in [Var.THRS3, Var.THRS2_3, Var.THRS3_3, Var.THRS4_3]:
            thrs_id = 2
        elif var in [Var.THRS4, Var.THRS2_4, Var.THRS3_4, Var.THRS4_4]:
            thrs_id = 3
        elif var == Var.THRS5:
            thrs_id = 4
        else:
            thrs_id = -1
        return thrs_id

    @staticmethod
    def to_s0_id(var: Var) -> int:
        """Translate a given variable type into an S0-input id.

        :param    Var    var:    The variable type to translate

        :return:    S0 id 0..3 or -1 if wrong type
        :rtype:    int
        """
        if var == Var.S0INPUT1:
            s0_id = 0
        elif var == Var.S0INPUT2:
            s0_id = 1
        elif var == Var.S0INPUT3:
            s0_id = 2
        elif var == Var.S0INPUT4:
            s0_id = 3
        else:
            s0_id = -1
        return s0_id

    @staticmethod
    def is_lockable_regulator_source(var: Var) -> bool:
        """Check if the the given variable type is lockable.

        :param    Var    var:    The variable type to check

        :return:    True if lockable, otherwise False
        :rtype:    bool
        """
        return var in [Var.R1VARSETPOINT, Var.R2VARSETPOINT]

    @staticmethod
    def use_lcn_special_values(var: Var) -> bool:
        """Check if the given variable type uses special values.

        Examples for special values: 'No value yet', 'sensor defective' etc.

        :param    Var    var:    The variable type to check

        :return:    True if special values are in use, otherwise False
        :rtype:    bool
        """
        return var not in [Var.S0INPUT1, Var.S0INPUT2, Var.S0INPUT3, Var.S0INPUT4]

    @staticmethod
    def has_type_in_response(var: Var, software_serial: int) -> bool:
        """Module-generation check.

        Check if the given variable type would receive a typed response if
        its status was requested.

        :param    Var    var:    The variable type to check
        :param    int    swAge:  The target LCN-modules firmware version

        :return:    True if a response would contain the variable's type,
                    otherwise False
        :rtype:    bool
        """
        if software_serial < 0x170206:
            if var in [
                Var.VAR1ORTVAR,
                Var.VAR2ORR1VAR,
                Var.VAR3ORR2VAR,
                Var.R1VARSETPOINT,
                Var.R2VARSETPOINT,
            ]:
                return False
        return True

    @staticmethod
    def is_event_based(var: Var, software_serial: int) -> bool:
        """Module-generation check.

        Check if the given variable type automatically sends status-updates
        on value-change. It must be polled otherwise.

        :param    Var    var:    The variable type to check
        :param    int    swAge:  The target LCN-module's firmware version

        :return:    True if the LCN module supports automatic status-messages
                    for this var, otherwise False
        :rtype:    bool
        """
        if (Var.to_set_point_id(var) != -1) or (Var.to_s0_id(var) != -1):
            return True
        return software_serial >= 0x170206

    @staticmethod
    def should_poll_status_after_command(var: Var, is2013: bool) -> bool:
        """Module-generation check.

        Check if the target LCN module would automatically send status-updates
        if the given variable type was changed by command.

        :param    Var    var:    The variable type to check
        :param    bool   is2013: The target module's-generation

        :return:    True if a poll is required to get the new status-value,
                    otherwise False
        :rtype:    bool
        """
        # Regulator set-points will send status-messages on every change
        # (all firmware versions)
        if Var.to_set_point_id(var) != -1:
            return False

        # Thresholds since 170206 will send status-messages on every change
        if is2013 and (Var.to_thrs_register_id(var) != -1):
            return False

        # Others:
        # - Variables before 170206 will never send any status-messages
        # - Variables since 170206 only send status-messages on "big" changes
        # - Thresholds before 170206 will never send any status-messages
        # - S0-inputs only send status-messages on "big" changes
        # (all "big changes" cases force us to poll the status to get faster
        # updates)
        return True

    @staticmethod
    def should_poll_status_after_regulator_lock(
        software_serial: int, lock_state: int
    ) -> bool:
        """Module-generation check.

        Check if the target LCN module would automatically send status-updates
        if the given regulator's lock-state was changed by command.

        :param    int       swAge: The target LCN-module's firmware version
        :param    int   lockState: The lock-state sent via command

        :return:    True if a poll is required to get the new status-value,
                    otherwise False
        :rtype:    bool
        """
        # LCN modules before 170206 will send an automatic status-message for
        # "lock", but not for "unlock"
        return (not lock_state) and (software_serial < 0x170206)


class VarUnit(Enum):
    """Measurement units used with LCN variables."""

    NATIVE = ""  # LCN internal representation (0 = -100C for absolute values)
    CELSIUS = "\u00b0C"
    KELVIN = "\u00b0K"
    FAHRENHEIT = "\u00b0F"
    LUX_T = "Lux_T"
    LUX_I = "Lux_I"
    METERPERSECOND = "m/s"  # Used for LCN-WIH wind speed
    PERCENT = "%"  # Used for humidity
    PPM = "ppm"  # Used by CO2 sensor
    VOLT = "V"
    AMPERE = "A"
    DEGREE = "\u00b0"  # Used for angles,

    @staticmethod
    def parse(unit: str) -> VarUnit:
        """Parse the given unit string and return VarUnit.

        :param    str    unit:    The input unit
        """
        unit = unit.upper()
        if unit in ["", "NATIVE", "LCN"]:
            var_unit = VarUnit.NATIVE
        elif unit in ["CELSIUS", "\u00b0CELSIUS", "\u00b0C"]:
            var_unit = VarUnit.CELSIUS
        elif unit in ["KELVIN", "\u00b0KELVIN", "\u00b0K", "K"]:
            var_unit = VarUnit.KELVIN
        elif unit in ["FAHRENHEIT", "\u00b0FAHRENHEIT", "\u00b0F"]:
            var_unit = VarUnit.FAHRENHEIT
        elif unit in ["LUX_T", "LX_T"]:
            var_unit = VarUnit.LUX_T
        elif unit in ["LUX", "LUX_I", "LX"]:
            var_unit = VarUnit.LUX_I
        elif unit in ["M/S", "METERPERSECOND"]:
            var_unit = VarUnit.METERPERSECOND
        elif unit in ["%", "PERCENT"]:
            var_unit = VarUnit.PERCENT
        elif unit == "PPM":
            var_unit = VarUnit.PPM
        elif unit in ["VOLT", "V"]:
            var_unit = VarUnit.VOLT
        elif unit in ["AMPERE", "AMP", "A"]:
            var_unit = VarUnit.AMPERE
        elif unit in ["DEGREE", "\u00b0"]:
            var_unit = VarUnit.DEGREE
        else:
            raise ValueError("Bad input unit.")
        return var_unit


class VarValue:
    """A value of an LCN variable.

    It internally stores the native LCN value and allows to convert from/into
    other units. Some conversions allow to specify whether the source value is
    absolute or relative. Relative values are used to create varvalues that
    can be added/subtracted from other (absolute) varvalues.

    :param    int    native_value:    The native value
    """

    def __init__(self, native_value: int) -> None:
        """Construct with native LCN value."""
        self.native_value = native_value

    def __eq__(self, other: object) -> bool:
        """Return if instance equals the given object."""
        if isinstance(other, VarValue):
            return self.native_value == other.native_value
        return False

    def __hash__(self) -> int:
        """Calculate the instance hash value."""
        return self.native_value.__hash__()

    def is_locked_regulator(self) -> bool:
        """Return if regulator is locked."""
        return (self.native_value & 0x8000) != 0

    @staticmethod
    def from_var_unit(value: float, unit: VarUnit, is_abs: bool) -> VarValue:
        """Create a variable value from any input.

        :param    float    value:   The input value
        :param    VarUnit  unit:    The input value's unit
        :param    bool     is_abs:  True for absolute values (relative values
                                    are used to add/subtract from other
                                    VarValues), otherwise False

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        if unit == VarUnit.NATIVE:
            var_value = VarValue.from_native(int(value))
        elif unit == VarUnit.CELSIUS:
            var_value = VarValue.from_celsius(value, is_abs)
        elif unit == VarUnit.KELVIN:
            var_value = VarValue.from_kelvin(value, is_abs)
        elif unit == VarUnit.FAHRENHEIT:
            var_value = VarValue.from_fahrenheit(value, is_abs)
        elif unit == VarUnit.LUX_T:
            var_value = VarValue.from_lux_t(value)
        elif unit == VarUnit.LUX_I:
            var_value = VarValue.from_lux_i(value)
        elif unit == VarUnit.METERPERSECOND:
            var_value = VarValue.from_meters_per_second(value)
        elif unit == VarUnit.PERCENT:
            var_value = VarValue.from_percent(value)
        elif unit == VarUnit.PPM:
            var_value = VarValue.from_ppm(value)
        elif unit == VarUnit.VOLT:
            var_value = VarValue.from_volt(value)
        elif unit == VarUnit.AMPERE:
            var_value = VarValue.from_ampere(value)
        elif unit == VarUnit.DEGREE:
            var_value = VarValue.from_degree(value, is_abs)
        else:
            raise ValueError("Wrong unit.")
        return var_value

    @staticmethod
    def from_native(value: int) -> VarValue:
        """Create a variable value from native input.

        :param    int    value:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(value)

    @staticmethod
    def from_celsius(value: float, is_abs: bool = True) -> VarValue:
        """Create a variable value from Celsius input.

        :param    float    value:    The input value
        :param    bool     is_abs:   True for absolute values (relative values
                                     are used to add/subtract from other
                                     VarValues), otherwise False

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        number = int(round(value * 10))
        return VarValue(number + 1000 if is_abs else number)

    @staticmethod
    def from_kelvin(value: float, is_abs: bool = True) -> VarValue:
        """Create a variable value from Kelvin input.

        :param    float    value:    The input value
        :param    bool     is_abs:   True for absolute values (relative values
                                     are used to add/subtract from other
                                     VarValues), otherwise False

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        if is_abs:
            value -= 273.15

        number = int(round(value * 10))
        return VarValue(number + 1000 if is_abs else number)

    @staticmethod
    def from_fahrenheit(value: float, is_abs: bool = True) -> VarValue:
        """Create a variable value from Fahrenheit input.

        :param    float    value:    The input value
        :param    bool     is_abs:   True for absolute values (relative values
                                     are used to add/subtract from other
                                     VarValues), otherwise False

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        if is_abs:
            value -= 32

        number = int(round(value / 0.18))
        return VarValue(number + 1000 if is_abs else number)

    @staticmethod
    def from_lux_t(lux: float) -> VarValue:
        """Create a variable value from lx input.

        Target must be connected to T-port.

        :param    float    l:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(math.log(lux) - 1.689646994) / 0.010380664))

    @staticmethod
    def from_lux_i(lux: float) -> VarValue:
        """Create a variable value from lx input.

        Target must be connected to I-port.

        :param    float    l:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(math.log(lux) * 100)))

    @staticmethod
    def from_percent(value: float) -> VarValue:
        """Create a variable value from % input.

        :param    float    value:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(value)))

    @staticmethod
    def from_ppm(value: float) -> VarValue:
        """Create a variable value from ppm input.

        Used for CO2 sensors.

        :param    float    value:   The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(value)))

    @staticmethod
    def from_meters_per_second(value: float) -> VarValue:
        """Create a variable value from m/s input.

        Used for LCN-WIH wind speed.

        :param    float    value:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(value * 10)))

    @staticmethod
    def from_volt(value: float) -> VarValue:
        """Create a variable value from V input.

        :param    float    value:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(value * 400)))

    @staticmethod
    def from_ampere(value: float) -> VarValue:
        """Create a variable value from A input.

        :param    float    value:    The input value

        :return: The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(value * 100000)))

    @staticmethod
    def from_degree(value: float, is_abs: bool = True) -> VarValue:
        """Create a variable value from degree (angle) input.

        :param    float    value:        The input value
        :param    bool     is_abs:   True for absolute values (relative values
                                     are used to add/subtract from other
                                     VarValues), otherwise False

        :return:    The variable value (never null)
        :rtype:     VarValue
        """
        number = int(round(value * 10))
        return VarValue(number + 1000 if is_abs else number)

    def to_var_unit(
        self,
        unit: VarUnit,
        is_lockable_regulator_source: bool = False,
    ) -> int | float:
        """Convert the given unit to a VarValue.

        :param    VarUnit    unit:    The variable unit
        :param    bool       is_lockable_regulator_source:  Is lockable source

        :return:    The variable value
        :rtype:     Union[int,float]
        """
        var_value = VarValue(
            self.native_value & 0x7FFF
            if is_lockable_regulator_source
            else self.native_value
        )

        if unit == VarUnit.NATIVE:
            return var_value.to_native()
        if unit == VarUnit.CELSIUS:
            return var_value.to_celsius()
        if unit == VarUnit.KELVIN:
            return var_value.to_kelvin()
        if unit == VarUnit.FAHRENHEIT:
            return var_value.to_fahrenheit()
        if unit == VarUnit.LUX_T:
            return var_value.to_lux_t()
        if unit == VarUnit.LUX_I:
            return var_value.to_lux_i()
        if unit == VarUnit.METERPERSECOND:
            return var_value.to_meters_per_second()
        if unit == VarUnit.PERCENT:
            return var_value.to_percent()
        if unit == VarUnit.PPM:
            return var_value.to_ppm()
        if unit == VarUnit.VOLT:
            return var_value.to_volt()
        if unit == VarUnit.AMPERE:
            return var_value.to_ampere()
        if unit == VarUnit.DEGREE:
            return var_value.to_degree()
        raise ValueError("Wrong unit.")

    def to_native(self) -> int:
        """Convert to native value.

        :return:    The converted value
        :rtype:    int
        """
        return self.native_value

    def to_celsius(self) -> float:
        """Convert to Celsius value.

        :return:    The converted value
        :rtype:    float
        """
        return (self.native_value - 1000) / 10.0

    def to_kelvin(self) -> float:
        """Convert to Kelvin value.

        :return:    The converted value
        :rtype:    float
        """
        return (self.native_value - 1000) / 10.0 + 273.15

    def to_fahrenheit(self) -> float:
        """Convert to Fahrenheit value.

        :return:    The converted value
        :rtype:    float
        """
        return (self.native_value - 1000) * 0.18 + 32.0

    def to_lux_t(self) -> float:
        """Convert to lx value.

        Source must be connected to T-port.

        :return:    The converted value
        :rtype:    float
        """
        return math.exp(0.010380664 * self.native_value + 1.689646994)

    def to_lux_i(self) -> float:
        """Convert to lx value.

        Source must be connected to I-port.

        :return:    The converted value
        :rtype:    float
        """
        return math.exp(self.native_value / 100)

    def to_percent(self) -> int:
        """Convert to % value.

        :return:    The converted value
        :rtype:    int
        """
        return self.native_value

    def to_ppm(self) -> int:
        """Convert to ppm value.

        :return:    The converted value
        :rtype:    int
        """
        return self.native_value

    def to_meters_per_second(self) -> float:
        """Convert to m/s value.

        :return:    The converted value
        :rtype:    float
        """
        return self.native_value / 10.0

    def to_volt(self) -> float:
        """Convert to V value.

        :return:    The converted value
        :rtype:    float
        """
        return self.native_value / 400.0

    def to_ampere(self) -> float:
        """Convert to A value.

        :return:    The converted value
        :rtype:    float
        """
        return self.native_value / 100000.0

    def to_degree(self) -> float:
        """Convert to degree value.

        :return:    The converted value
        :rtype:    float
        """
        return (self.native_value - 1000) / 10.0

    def to_var_unit_string(
        self,
        unit: VarUnit,
        is_lockable_regulator_source: bool = False,
        use_lcn_special_values: bool = False,
    ) -> str:
        """Convert the given unit into a string representation.

        :param    VarUnit    unit:    The input unit
        :param    bool       is_lockable_regulator_source:  Is lockable source
        :param    bool       use_lcn_special_values:  Use LCN special values

        :return:    The string representation of input unit.
        :rtype:     str
        """
        if use_lcn_special_values and (self.native_value == 0xFFFF):  # No value
            ret = "---"
        elif use_lcn_special_values and (
            (self.native_value & 0xFF00) == 0x8100
        ):  # Undefined
            ret = "---"
        elif use_lcn_special_values and (
            (self.native_value & 0xFF00) == 0x7F00
        ):  # Defective
            ret = "!!!"
        else:
            var = VarValue(
                (self.native_value & 0x7FF)
                if is_lockable_regulator_source
                else self.native_value
            )
            if unit == VarUnit.NATIVE:
                ret = f"{var.to_native():.0f}"
            elif unit == VarUnit.CELSIUS:
                ret = f"{var.to_celsius():.01f}"
            elif unit == VarUnit.KELVIN:
                ret = f"{var.to_kelvin():.01f}"
            elif unit == VarUnit.FAHRENHEIT:
                ret = f"{var.to_fahrenheit():.01f}"
            elif unit == VarUnit.LUX_T:
                if var.to_native() > 1152:  # Max. value the HW can do
                    ret = "---"
                else:
                    ret = f"{var.to_lux_t():.0f}"
            elif unit == VarUnit.LUX_I:
                if var.to_native() > 1152:  # Max. value the HW can do
                    ret = "---"
                else:
                    ret = f"{var.to_lux_i():.0f}"
            elif unit == VarUnit.METERPERSECOND:
                ret = f"{var.to_meters_per_second():.0f}"
            elif unit == VarUnit.PERCENT:
                ret = f"{var.to_percent():.0f}"
            elif unit == VarUnit.PPM:
                ret = f"{var.to_ppm():.0f}"
            elif unit == VarUnit.VOLT:
                ret = f"{var.to_volt():.0f}"
            elif unit == VarUnit.AMPERE:
                ret = f"{var.to_ampere():.0f}"
            elif unit == VarUnit.DEGREE:
                ret = f"{var.to_degree():.0f}"
            else:
                raise ValueError("Wrong unit.")

        # handle locked regulators
        if is_lockable_regulator_source and self.is_locked_regulator():
            ret = f"({ret:s})"

        return ret


class LedStatus(Enum):
    """Possible states for LCN LEDs."""

    OFF = "A"
    ON = "E"
    BLINK = "B"
    FLICKER = "F"


class LogicOpStatus(Enum):
    """Possible states for LCN logic-operations."""

    NONE = "N"
    SOME = "T"  # Note: Actually not correct since AND won't be OR also
    ALL = "V"


class TimeUnit(Enum):
    """Time units used for several LCN commands."""

    SECONDS = "S"
    MINUTES = "M"
    HOURS = "H"
    DAYS = "D"

    @staticmethod
    def parse(unit: str) -> TimeUnit:
        """Parse the given time_unit into a time unit.

        It supports several alternative terms.

        :param    str    time_unit:    The text to parse

        :return:    TimeUnit enum
        :rtype:    TimeUnit
        """
        unit = unit.upper()
        if unit in ["SECONDS", "SECOND", "SEC", "S"]:
            time_unit = TimeUnit.SECONDS
        elif unit in ["MINUTES", "MINUTE", "MIN", "M"]:
            time_unit = TimeUnit.MINUTES
        elif unit in ["HOURS", "HOUR", "H"]:
            time_unit = TimeUnit.HOURS
        elif unit in ["DAYS", "DAY", "D"]:
            time_unit = TimeUnit.DAYS
        else:
            raise ValueError("Bad time unit input.")
        return time_unit


class RelayStateModifier(Enum):
    """Relay-state modifiers used in LCN commands."""

    ON = "1"
    OFF = "0"
    TOGGLE = "U"
    NOCHANGE = "-"


class MotorStateModifier(Enum):
    """Motor-state modifiers used in LCN commands.

    LCN module has to be configured for motors connected to relays.
    """

    UP = "U"
    DOWN = "D"
    STOP = "S"
    TOGGLEONOFF = "T"  # toggle on/off
    TOGGLEDIR = "R"  # toggle direction
    CYCLE = "C"  # up, stop, down, stop, ...
    NOCHANGE = "-"


class MotorReverseTime(Enum):
    """Motor reverse time user in LCN commands.

    For modules with FW<190C the release time has to be specified.
    """

    RT70 = "RT70"  # 70ms
    RT600 = "RT600"  # 600ms
    RT1200 = "RT1200"  # 1200ms


class MotorPositioningMode(Enum):
    """Motor positioning mode used in LCN commands."""

    NONE = "NONE"
    BS4 = "BS4"
    MODULE = "MODULE"
    # EMULATED = "EMULATED"


class RelVarRef(Enum):
    """Value-reference for relative LCN variable commands."""

    CURRENT = auto()
    PROG = auto()  # Programmed value (LCN-PRO). Set-points and thresholds.


class SendKeyCommand(Enum):
    """Command types used when sending LCN keys."""

    HIT = "K"
    MAKE = "L"
    BREAK = "O"
    DONTSEND = "-"


class KeyLockStateModifier(Enum):
    """Key-lock modifiers used in LCN commands."""

    ON = "1"
    OFF = "0"
    TOGGLE = "U"
    NOCHANGE = "-"


class BeepSound(Enum):
    """Beep sounds supported by LCN modules."""

    NORMAL = "N"
    SPECIAL = "S"


HARDWARE_DESCRIPTIONS = dict(
    [
        (-1, "UnknownModuleType"),
        (1, "LCN-SW1.0"),
        (2, "LCN-SW1.1"),
        (3, "LCN-UP1.0"),
        (4, "LCN-UP2"),
        (5, "LCN-SW2"),
        (6, "LCN-UP-Profi1-Plus"),
        (7, "LCN-DI12"),
        (8, "LCN-HU"),
        (9, "LCN-SH"),
        (10, "LCN-UP2"),
        (11, "LCN-UPP"),
        (12, "LCN-SK"),
        (14, "LCN-LD"),
        (15, "LCN-SH-Plus"),
        (17, "LCN-UPS"),
        (18, "LCN_UPS24V"),
        (19, "LCN-GTM"),
        (20, "LCN-SHS"),
        (21, "LCN-ESD"),
        (22, "LCN-EB2"),
        (23, "LCN-MRS"),
        (24, "LCN-EB11"),
        (25, "LCN-UMR"),
        (26, "LCN-UPU"),
        (27, "LCN-UMR24V"),
        (28, "LCN-SHD"),
        (29, "LCN-SHU"),
        (30, "LCN-SR6"),
        (31, "LCN-UMF"),
        (32, "LCN-WBH"),
    ]
)


class HardwareType(Enum):
    """Hardware types as returned by serial number request."""

    UNKNOWN = -1
    SW1_0 = 1
    SW1_1 = 2
    UP1_0 = 3
    UP2 = 4
    SW2 = 5
    UP_PROFI1_PLUS = 6
    DI12 = 7
    HU = 8
    SH = 9
    UPP = 11
    SK = 12
    LD = 14
    SH_PLUS = 15
    UPS = 17
    UPS24V = 18
    GTM = 19
    SHS = 20
    ESD = 21
    EB2 = 22
    MRS = 23
    EB11 = 24
    UMR = 25
    UPU = 26
    UMR24V = 27
    SHD = 28
    SHU = 29
    SR6 = 30
    UMF = 31
    WBH = 32

    @property
    def identifier(self) -> Any:
        """Get the LCN hardware identifier."""
        return self.value

    @property
    def description(self) -> str:
        """Get the LCN hardware name."""
        return HARDWARE_DESCRIPTIONS[self.value]


@no_type_check
def hw_type_new(cls, value):
    """Replace Hardwaretype.__new__."""
    if value == 10:
        value = 4
    return super(HardwareType, cls).__new__(cls, value)


setattr(HardwareType, "__new__", hw_type_new)


class AccessControlPeriphery(Enum):
    """Action types for LCN keys."""

    TRANSMITTER = "transmitter"
    TRANSPONDER = "transponder"
    FINGERPRINT = "fingerprint"
    CODELOCK = "codelock"


class AcknowledgeErrorCode(Enum):
    """Acknowledge error codes."""

    UNKNOWN = -1
    OK = 0
    UNKNOWN_COMMAND = 5
    WRONG_PARAMETER_COUNT = 6
    INVALID_PARAMETER_VALUE = 7
    CURRENTLY_NOT_ALLOWED = 8
    NOT_ALLOWED_BY_PROGRAMMING = 9
    INAPPROPRIATE_MODULE = 10
    MISSING_PERIPHERY = 11
    PROGRAMMING_MODE_REQUIRED = 12
    FUSE_DEFECT = 14

    @classmethod
    def _missing_(cls, value: Any) -> AcknowledgeErrorCode:
        """Handle missing values."""
        return cls.UNKNOWN


class LcnEvent(Enum):
    """LCN events."""

    CONNECTION_ESTABLISHED = "connection-established"
    CONNECTION_LOST = "connection-lost"
    CONNECTION_REFUSED = "connection-refused"
    CONNECTION_TIMEOUT = "connection-timeout"
    PING_TIMEOUT = "ping-timeout"
    TIMEOUT_ERROR = "timeout-error"
    LICENSE_ERROR = "license-error"
    AUTHENTICATION_ERROR = "authentication-error"
    BUS_CONNECTED = "bus-connected"
    BUS_DISCONNECTED = "bus-disconnected"
    BUS_CONNECTION_STATUS_CHANGED = "bus-connection-status-changed"


default_connection_settings: dict[str, Any] = {
    "NUM_TRIES": 3,  # Total number of request to sent before going into
    # failed-state.
    "SK_NUM_TRIES": 3,  # Total number of segment coupler scan tries
    "DIM_MODE": OutputPortDimMode.STEPS50,
    "ACKNOWLEDGE": True,  # modules request an acknowledge command
    "DEFAULT_TIMEOUT": 3.5,  # Default timeout for send command retries
    "MAX_STATUS_EVENTBASED_VALUEAGE": 600,  # Poll interval for
    # status values that
    # automatically send
    # their values on change
    "MAX_STATUS_POLLED_VALUEAGE": 30,  # Poll interval for status
    # values that do not send
    # their values on change
    # (always polled)
    "STATUS_REQUEST_DELAY_AFTER_COMMAND": 2,  # Status request delay
    # after a command has
    # been send which
    # potentially changed
    # that status
    "MAX_RESPONSE_AGE": 60,  # Age in seconds after which stored responses are purged
    "BUS_IDLE_TIME": 0.05,  # Time to wait for message traffic before sending
    "PING_SEND_DELAY": 600,  # The default timeout for pings sent to PCHK
    "PING_RECV_TIMEOUT": 10,  # The default timeout for pings expected from PCHK
    "PING_MODULE_TIMEOUT": 60,  # The delay before sending a ping to a module
}
