"""Parsers for incoming PCK messages."""

from __future__ import annotations

import logging

from pypck import lcn_defs
from pypck.lcn_addr import LcnAddr
from pypck.pck_commands import PckParser

_LOGGER = logging.getLogger(__name__)


class Input:
    """Parent class for all input data read from LCN-PCHK.

    An implementation of :class:`~pypck.input.Input` has to provide easy
    accessible attributes and/or methods to expose the PCK command properties
    to the user.
    Each Input object provides an implementation of
    :func:`~pypck.input.Input.try_parse` static method, to parse the given
    plain text PCK command. If the command can be parsed by the Input object,
    a list of instances of :class:`~pypck.input.Input` is returned. Otherwise,
    nothing is returned.
    """

    def __init__(self) -> None:
        """Construct Input object."""

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).
        """
        raise NotImplementedError


class ModInput(Input):  # pylint: disable=too-few-public-methods, abstract-method
    """Parent class of all inputs having an LCN module as its source.

    The class in inherited from :class:`~pypck.input.Input`
    """

    def __init__(self, physical_source_addr: LcnAddr):
        """Construct ModInput object."""
        super().__init__()
        self.physical_source_addr = physical_source_addr


# ## Plain text inputs


class AuthUsername(Input):
    """Authentication username message received from PCHK."""

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        if data == PckParser.AUTH_USERNAME:
            return [AuthUsername()]
        return None


class AuthPassword(Input):
    """Authentication password message received from PCHK."""

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        if data == PckParser.AUTH_PASSWORD:
            return [AuthPassword()]
        return None


class AuthOk(Input):
    """Authentication ok message received from PCHK."""

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        if data == PckParser.AUTH_OK:
            return [AuthOk()]
        return None


class AuthFailed(Input):
    """Authentication failed message received from PCHK."""

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        if data == PckParser.AUTH_FAILED:
            return [AuthFailed()]
        return None


class LcnConnState(Input):
    """LCN bus connected message received from PCHK."""

    def __init__(self, is_lcn_connected: bool):
        """Construct Input object."""
        super().__init__()
        self._is_lcn_connected = is_lcn_connected

    @property
    def is_lcn_connected(self) -> bool:
        """Return the LCN bus connection status.

        :return:   True if connection to hardware bus was established,
                   otherwise False.
        :rtype:    bool
        """
        return self._is_lcn_connected

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        if data == PckParser.LCNCONNSTATE_CONNECTED:
            return [LcnConnState(True)]
        if data == PckParser.LCNCONNSTATE_DISCONNECTED:
            return [LcnConnState(False)]
        return None


class LicenseError(Input):
    """LCN bus connected message received from PCHK."""

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        if data == PckParser.LICENSE_ERROR:
            return [LicenseError()]
        return None


class DecModeSet(Input):
    """Decimal mode set received from PCHK."""

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        if data == PckParser.DEC_MODE_SET:
            return [DecModeSet()]
        return None


class CommandError(Input):
    """Command error received from PCHK."""

    def __init__(self, message: str):
        """Construct Input object."""
        super().__init__()
        self.message = message

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_COMMAND_ERROR.match(data)
        if matcher:
            return [CommandError(matcher.group("message"))]
        return None


class Ping(Input):
    """Ping message received from PCHK."""

    def __init__(self, count: int | None):
        """Construct Input object."""
        super().__init__()
        self._count = count

    @property
    def count(self) -> int | None:
        """Return the ping count.

        :return:   Ping count
        :rtype:    int | None
        """
        return self._count

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_PING.match(data)
        if matcher:
            count = matcher.group("count")
            if count == "":
                return [Ping(None)]
            return [Ping(int(count))]

        return None


# ## Inputs received from modules


class ModAck(ModInput):
    """Acknowledge message received from module."""

    def __init__(
        self, physical_source_addr: LcnAddr, code: lcn_defs.AcknowledgeErrorCode
    ):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.code = code

    def get_code(self) -> lcn_defs.AcknowledgeErrorCode:
        """Return the acknowledge code."""
        return self.code

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher_pos = PckParser.PATTERN_ACK_POS.match(data)
        if matcher_pos:
            addr = LcnAddr(
                int(matcher_pos.group("seg_id")), int(matcher_pos.group("mod_id"))
            )
            return [ModAck(addr, lcn_defs.AcknowledgeErrorCode.OK)]

        matcher_neg = PckParser.PATTERN_ACK_NEG.match(data)
        if matcher_neg:
            addr = LcnAddr(
                int(matcher_neg.group("seg_id")), int(matcher_neg.group("mod_id"))
            )
            return [
                ModAck(
                    addr, lcn_defs.AcknowledgeErrorCode(int(matcher_neg.group("code")))
                )
            ]

        return None


class ModSk(ModInput):
    """Segment information received from an LCN segment coupler."""

    def __init__(self, physical_source_addr: LcnAddr, reported_seg_id: int):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.reported_seg_id = reported_seg_id

    def get_reported_seg_id(self) -> int:
        """Return the segment id reported from segment coupler.

        :return:   Reported segment id.
        :rtype:    int
        """
        return self.reported_seg_id

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_SK_RESPONSE.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            return [ModSk(addr, int(matcher.group("id")))]

        return None


class ModSn(ModInput):
    """Serial number and firmware version received from an LCN module."""

    def __init__(
        self,
        physical_source_addr: LcnAddr,
        hardware_serial: int,
        manu: int,
        software_serial: int,
        hardware_type: lcn_defs.HardwareType,
    ):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.hardware_serial = hardware_serial
        self.manu = manu
        self.software_serial = software_serial
        self.hardware_type = hardware_type

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_SN.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            hardware_serial = int(matcher.group("hardware_serial"), 16)
            try:
                manu = int(matcher.group("manu"), 16)
            except (
                ValueError
            ):  # unconventional manufacturer code (e.g., due to LinHK VM)
                manu = 0xFF
                _LOGGER.warning(
                    "Unconventional manufacturer code for module (S%d, M%d): %s. Defaulting to 0x%02X",
                    addr.seg_id,
                    addr.addr_id,
                    matcher.group("manu"),
                    manu,
                )
            software_serial = int(matcher.group("software_serial"), 16)
            try:
                hardware_type = lcn_defs.HardwareType(
                    int(matcher.group("hardware_type"))
                )
            except ValueError:  # unknown hardware type
                hardware_type = lcn_defs.HardwareType(-1)
            return [ModSn(addr, hardware_serial, manu, software_serial, hardware_type)]

        return None


class ModNameComment(ModInput):
    """Name or comment received from an LCN module."""

    def __init__(
        self, physical_source_addr: LcnAddr, command: str, block_id: int, text: str
    ):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.command = command
        self.block_id = block_id
        self.text = text

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_NAME_COMMENT.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            command = matcher.group("command")
            block_id = int(matcher.group("block_id")) - 1
            text = matcher.group("text")
            return [ModNameComment(addr, command, block_id, text)]

        return None


class ModStatusGroups(ModInput):
    """Group memberships status received from an LCN module."""

    def __init__(
        self,
        physical_source_addr: LcnAddr,
        dynamic: bool,
        max_groups: int,
        groups: list[LcnAddr],
    ):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.dynamic = dynamic
        self.max_groups = max_groups
        self.groups = groups

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_GROUPS.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            dynamic = matcher.group("kind") == "D"
            max_groups = int(matcher.group("max_groups"))
            groups = [
                LcnAddr(addr.seg_id, int(group), True)
                for group in matcher.groups()[4:]
                if group is not None
            ]
            return [ModStatusGroups(addr, dynamic, max_groups, groups)]

        return None


class ModStatusOutput(ModInput):
    """Status of an output-port in percent received from an LCN module."""

    def __init__(self, physical_source_addr: LcnAddr, output_id: int, percent: float):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.output_id = output_id
        self.percent = percent

    def get_output_id(self) -> int:
        """Return the output port id.

        :return:    Output port id.
        :rtype:     int
        """
        return self.output_id

    def get_percent(self) -> float:
        """Return the output brightness in percent.

        :return:    Brightness in percent.
        :rtype:     float
        """
        return self.percent

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_OUTPUT_PERCENT.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            return [
                ModStatusOutput(
                    addr,
                    int(matcher.group("output_id")) - 1,
                    float(matcher.group("percent")),
                )
            ]

        return None


class ModStatusOutputNative(ModInput):
    """Status of an output-port in native units received from an LCN module."""

    def __init__(self, physical_source_addr: LcnAddr, output_id: int, value: int):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.output_id = output_id
        self.value = value

    def get_output_id(self) -> int:
        """Return the output port id.

        :return:    Output port id.
        :rtype:     int
        """
        return self.output_id

    def get_value(self) -> int:
        """Return the output brightness in native units.

        :return:    Brightness in percent.
        :rtype:     float
        """
        return self.value

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_OUTPUT_NATIVE.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            return [
                ModStatusOutputNative(
                    addr,
                    int(matcher.group("output_id")) - 1,
                    int(matcher.group("value")),
                )
            ]

        return None


class ModStatusRelays(ModInput):
    """Status of 8 relays received from an LCN module.

    Includes helper functions for motor states based on LCN wiring.
    """

    def __init__(self, physical_source_addr: LcnAddr, states: list[bool]):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.states = states

    def get_state(self, relay_id: int) -> bool:
        """
        Get the state of a single relay.

        :param    int    relay_id:    Relay id (0..7)

        :return:                      The relay's state
        :rtype:   bool
        """
        return self.states[relay_id]

    def get_motor_onoff_relay(self, motor_id: int) -> int:
        """Get the motor on/off relay id."""
        if 0 > motor_id > 3:
            raise ValueError("Motor id must be in range 0..3")
        return motor_id * 2

    def get_motor_updown_relay(self, motor_id: int) -> int:
        """Get the motor up/down relay id."""
        if 0 > motor_id > 3:
            raise ValueError("Motor id must be in range 0..3")
        return motor_id * 2 + 1

    def motor_is_on(self, motor_id: int) -> bool:
        """Check if a motor is on."""
        return self.states[self.get_motor_onoff_relay(motor_id)]

    def is_opening(self, motor_id: int) -> bool:
        """Check if a motor is opening."""
        if self.motor_is_on(motor_id):
            return not self.states[self.get_motor_updown_relay(motor_id)]
        return False

    def is_closing(self, motor_id: int) -> bool:
        """Check if a motor is closing."""
        if self.motor_is_on(motor_id):
            return self.states[self.get_motor_updown_relay(motor_id)]
        return False

    def is_assumed_closed(self, motor_id: int) -> bool:
        """Check if a motor is closed.

        The closed state is assumed if the motor direction is down and the motor is switched off."
        """
        if not self.motor_is_on(motor_id):
            return self.states[self.get_motor_updown_relay(motor_id)]
        return False

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_RELAYS.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            return [
                ModStatusRelays(
                    addr, PckParser.get_boolean_value(int(matcher.group("byte_value")))
                )
            ]

        return None


class ModStatusBinSensors(ModInput):
    """Status of 8 binary sensors received from an LCN module."""

    def __init__(self, physical_source_addr: LcnAddr, states: list[bool]):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.states = states

    def get_state(self, bin_sensor_id: int) -> bool:
        """Get the state of a single binary-sensor.

        :param    int    bin_sensor_id:    Binary sensor id (0..7)

        :return:                           The binary-sensor's state
        :rtype:   bool
        """
        return self.states[bin_sensor_id]

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_BINSENSORS.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            return [
                ModStatusBinSensors(
                    addr, PckParser.get_boolean_value(int(matcher.group("byte_value")))
                )
            ]

        return None


class ModStatusVar(ModInput):
    """Status of a variable received from an LCN module."""

    def __init__(
        self,
        physical_source_addr: LcnAddr,
        orig_var: lcn_defs.Var,
        value: lcn_defs.VarValue,
    ):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.orig_var = orig_var
        self.value = value
        self.var = self.orig_var

    def get_var(self) -> lcn_defs.Var:
        """Get the variable's real type.

        :return:        The real type
        :rtype:        :class:`~pypck.lcn_defs.Var`
        """
        return self.var

    def get_value(self) -> lcn_defs.VarValue:
        """Get the variable's value.

        :return:    The value of the variable.
        :rtype:     int
        """
        return self.value

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_VAR.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            var = lcn_defs.Var.var_id_to_var(int(matcher.group("id")) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group("value")))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_STATUS_SETVAR.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            var = lcn_defs.Var.set_point_id_to_var(int(matcher.group("id")) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group("value")))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_STATUS_THRS.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            var = lcn_defs.Var.thrs_id_to_var(
                int(matcher.group("register_id")) - 1, int(matcher.group("thrs_id")) - 1
            )
            value = lcn_defs.VarValue.from_native(int(matcher.group("value")))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_STATUS_S0INPUT.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            var = lcn_defs.Var.s0_id_to_var(int(matcher.group("id")) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group("value")))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_VAR_GENERIC.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            var = lcn_defs.Var.UNKNOWN
            value = lcn_defs.VarValue.from_native(int(matcher.group("value")))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_THRS5.match(data)
        if matcher:
            ret: list[Input] = []
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            for thrs_id in range(5):
                var = lcn_defs.Var.thrs_id_to_var(0, thrs_id)
                value = lcn_defs.VarValue.from_native(
                    int(matcher.group(f"value{thrs_id + 1}"))
                )
                ret.append(ModStatusVar(addr, var, value))
            return ret

        return None


class ModStatusLedsAndLogicOps(ModInput):
    """Status of LEDs and logic-operations received from an LCN module.

    :param    int      physicalSourceAddr:   The physical source address
    :param    states_led:         The 12 LED states
    :type     states_led:         list(:class:`~pypck.lcn_defs.LedStatus`)
    :param    states_logic_ops:   The 4 logic-operation states
    :type     states_logic_ops:   list(:class:`~pypck.lcn_defs.LogicOpStatus`)
    """

    def __init__(
        self,
        physical_source_addr: LcnAddr,
        states_led: list[lcn_defs.LedStatus],
        states_logic_ops: list[lcn_defs.LogicOpStatus],
    ):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.states_led = states_led  # 12x LED status.
        self.states_logic_ops = states_logic_ops  # 4x logic-operation status.

    def get_led_state(self, led_id: int) -> lcn_defs.LedStatus:
        """Get the status of a single LED.

        :param    int    led_id:   LED id (0..11)
        :return:                   The LED's status
        :rtype:   list(:class:`~pypck.lcn_defs.LedStatus`)
        """
        return self.states_led[led_id]

    def get_logic_op_state(self, logic_op_id: int) -> lcn_defs.LogicOpStatus:
        """Get the status of a single logic operation.

        :param    int    logic_op_id:    Logic operation id (0..3)
        :return:    The logic-operation's status
        :rtype:     list(:class:`~pypck.lcn_defs.LogicOpStatus`)
        """
        return self.states_logic_ops[logic_op_id]

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_LEDSANDLOGICOPS.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))

            led_states = matcher.group("led_states").upper()
            states_leds = [lcn_defs.LedStatus(led_state) for led_state in led_states]

            logic_op_states = matcher.group("logic_op_states").upper()
            states_logic_ops = [
                lcn_defs.LogicOpStatus(logic_op_state)
                for logic_op_state in logic_op_states
            ]
            return [ModStatusLedsAndLogicOps(addr, states_leds, states_logic_ops)]

        return None


class ModStatusKeyLocks(ModInput):
    """Status of locked keys received from an LCN module.

    :param    int                physicalSourceAddr:   The source address
    :param    list(list(bool))   states:               The 4x8 key-lock states
    """

    def __init__(self, physical_source_id: LcnAddr, states: list[list[bool]]):
        """Construct ModInput object."""
        super().__init__(physical_source_id)
        self.states = states

    def get_state(self, table_id: int, key_id: int) -> bool:
        """Get the lock-state of a single key.

        :param    int    tableId:    Table id: (0..3  =>  A..D)
        :param    int    keyId:      Key id (0..7  =>  1..8)
        :return:  The key's lock-state
        :rtype:   bool
        """
        return self.states[table_id][key_id]

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_KEYLOCKS.match(data)
        states: list[list[bool]] = []
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            for i in range(4):
                state = matcher.group(f"table{i:d}")
                if state is not None:
                    states.append(PckParser.get_boolean_value(int(state)))
            return [ModStatusKeyLocks(addr, states)]

        return None


class ModStatusAccessControl(ModInput):
    """Status of a transmitter, transponder or fingerprint sensor."""

    def __init__(
        self,
        physical_source_addr: LcnAddr,
        periphery: lcn_defs.AccessControlPeriphery,
        code: str,
        level: int | None = None,
        key: int | None = None,
        action: lcn_defs.KeyAction | None = None,
        battery: lcn_defs.BatteryStatus | None = None,
    ):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.periphery = periphery
        self.code = code
        self.level = level
        self.key = key
        self.action = action
        self.battery = battery

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_TRANSMITTER.match(data)
        if matcher:
            periphery = lcn_defs.AccessControlPeriphery.TRANSMITTER
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            code = (
                f"{int(matcher.group('code1')):02x}"
                f"{int(matcher.group('code2')):02x}"
                f"{int(matcher.group('code3')):02x}"
            )
            level = int(matcher.group("level"))
            key = int(matcher.group("key")) - 1

            actions = {
                "1": lcn_defs.KeyAction.HIT,
                "2": lcn_defs.KeyAction.MAKE,
                "3": lcn_defs.KeyAction.BREAK,
            }

            battery_status = {
                "0": lcn_defs.BatteryStatus.FULL,
                "1": lcn_defs.BatteryStatus.WEAK,
            }

            action = actions[matcher.group("action")[2]]
            battery = battery_status[matcher.group("action")[1]]

            return [
                ModStatusAccessControl(
                    addr, periphery, code, level, key, action, battery
                )
            ]

        matcher = PckParser.PATTERN_STATUS_TRANSPONDER.match(data)
        if matcher:
            periphery = lcn_defs.AccessControlPeriphery.TRANSPONDER
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            code = (
                f"{int(matcher.group('code1')):02x}"
                f"{int(matcher.group('code2')):02x}"
                f"{int(matcher.group('code3')):02x}"
            )
            return [ModStatusAccessControl(addr, periphery, code)]

        matcher = PckParser.PATTERN_STATUS_FINGERPRINT.match(data)
        if matcher:
            periphery = lcn_defs.AccessControlPeriphery.FINGERPRINT
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            code = (
                f"{int(matcher.group('code1')):02x}"
                f"{int(matcher.group('code2')):02x}"
                f"{int(matcher.group('code3')):02x}"
            )
            return [ModStatusAccessControl(addr, periphery, code)]

        matcher = PckParser.PATTERN_STATUS_CODELOCK.match(data)
        if matcher:
            periphery = lcn_defs.AccessControlPeriphery.CODELOCK
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            code = (
                f"{int(matcher.group('code1')):02x}"
                f"{int(matcher.group('code2')):02x}"
                f"{int(matcher.group('code3')):02x}"
            )
            return [ModStatusAccessControl(addr, periphery, code)]

        return None


class ModStatusSceneOutputs(ModInput):
    """Status of the output values and ramp values received from an LCN module."""

    def __init__(
        self,
        physical_source_addr: LcnAddr,
        scene_id: int,
        values: list[int],
        ramps: list[int],
    ):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.scene_id = scene_id
        self.values = values
        self.ramps = ramps

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_SCENE_OUTPUTS.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            scene_id = int(matcher.group("scene_id"))
            values = [int(matcher.group(f"output{i + 1:d}")) for i in range(4)]
            ramps = [int(matcher.group(f"ramp{i + 1:d}")) for i in range(4)]
            return [ModStatusSceneOutputs(addr, scene_id, values, ramps)]

        return None


class ModStatusMotorPositionBS4(ModInput):
    """Status of motor positions (if BS4 connected) received from an LCN module.

    Position and limit is in percent. 0%: cover closed, 100%: cover open.
    """

    def __init__(
        self,
        physical_source_addr: LcnAddr,
        motor: int,
        position: float,
        limit: float | None = None,
        time_down: int | None = None,
        time_up: int | None = None,
    ):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.motor = motor
        self.position = position
        self.limit = limit
        self.time_down = time_down
        self.time_up = time_up

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_MOTOR_POSITION_BS4.match(data)
        if matcher:
            motor_status_inputs: list[Input] = []
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            for idx in (1, 2):
                motor = matcher.group(f"motor{idx}_id")
                position = matcher.group(f"position{idx}")
                limit = matcher.group(f"limit{idx}")
                time_down = matcher.group(f"time_down{idx}")
                time_up = matcher.group(f"time_up{idx}")

                motor_status_inputs.append(
                    ModStatusMotorPositionBS4(
                        addr,
                        int(motor) - 1,
                        (200 - int(position)) / 2,
                        None if limit == "?" else (200 - int(limit)) / 2,
                        None if time_down == "?" else int(time_down),
                        None if time_up == "?" else int(time_up),
                    )
                )
            return motor_status_inputs

        return None


class ModStatusMotorPositionModule(ModInput):
    """Status of motor positions received from an LCN module.

    Position is in percent. 0%: cover closed, 100%: cover open.
    """

    def __init__(
        self,
        physical_source_addr: LcnAddr,
        motor: int,
        position: float,
    ):
        """Construct ModInput object."""
        super().__init__(physical_source_addr)
        self.motor = motor
        self.position = position

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_STATUS_MOTOR_POSITION_MODULE.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            motor = matcher.group("motor_id")
            position = matcher.group("position")

            return [
                ModStatusMotorPositionModule(
                    addr,
                    int(motor) - 1,
                    100 - float(position),
                )
            ]

        return None


class ModSendCommandHost(ModInput):
    """Send command to host message from module."""

    def __init__(self, physical_source_addr: LcnAddr, parameters: tuple[int, ...]):
        """Construct ModSendCommandHost object."""
        super().__init__(physical_source_addr)
        self.parameters = parameters

    def get_parameters(self) -> tuple[int, ...]:
        """Return the received parameters.

        :return:    Parameters
        :rtype:     List with parameters of type int.
        """
        return self.parameters

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_SEND_COMMAND_HOST.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            parameters = tuple(
                int(param) for param in matcher.groups()[3:] if param is not None
            )
            return [ModSendCommandHost(addr, parameters)]

        return None


class ModSendKeysHost(ModInput):
    """Send command to host message from module."""

    def __init__(
        self,
        physical_source_addr: LcnAddr,
        actions: list[lcn_defs.SendKeyCommand],
        keys: list[bool],
    ):
        """Construct ModSendKeysHost object."""
        super().__init__(physical_source_addr)
        self.actions = actions
        self.keys = keys

    def get_actions(self) -> list[lcn_defs.SendKeyCommand]:
        """Get key actions for each table.

        :returns:   List of length 3 with key actions for each table A, B, C.
        :rtype:     list(:class:`~pypck.lcn_defs.SendKeyCommand`)
        """
        return self.actions

    def get_keys(self) -> list[bool]:
        """Get keys which should be triggered.

        :returns:   List of booleans (length 8) for each key
                    (True: trigger, False: do nothing).
        :rtype:     list(bool)
        """
        return self.keys

    @staticmethod
    def try_parse(data: str) -> list[Input] | None:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        matcher = PckParser.PATTERN_SEND_KEYS_HOST.match(data)
        if matcher:
            addr = LcnAddr(int(matcher.group("seg_id")), int(matcher.group("mod_id")))
            actions_value = int(matcher.group("actions"))
            keys_value = int(matcher.group("keys"))

            mapping = (
                lcn_defs.SendKeyCommand.DONTSEND,
                lcn_defs.SendKeyCommand.HIT,
                lcn_defs.SendKeyCommand.MAKE,
                lcn_defs.SendKeyCommand.BREAK,
            )

            actions = []
            for idx in range(3):
                action = mapping[(actions_value >> 2 * idx) & 0x03]
                actions.append(action)

            keys = [bool(keys_value >> bit & 0x01) for bit in range(8)]

            return [ModSendKeysHost(addr, actions, keys)]

        return None


# ## Other inputs


class Unknown(Input):
    """Handle all unknown input data."""

    def __init__(self, data: str):
        """Construct Input object."""
        super().__init__()
        self._data = data

    @staticmethod
    def try_parse(data: str) -> list[Input]:
        """Try to parse the given input text.

        Will return a list of parsed Inputs. The list might be empty (but not
        null).

        :param    data    str:    The input data received from LCN-PCHK

        :return:            The parsed Inputs (never null)
        :rtype:             List with instances of :class:`~pypck.input.Input`
        """
        return [Unknown(data)]

    @property
    def data(self) -> str:
        """Return the received data.

        :return:    Received data.
        :rtype:     str
        """
        return self._data


class InputParser:
    """Parse all input objects for given input data."""

    parsers: list[type[Input]] = [
        AuthUsername,
        AuthPassword,
        AuthOk,
        AuthFailed,
        LcnConnState,
        LicenseError,
        DecModeSet,
        CommandError,
        Ping,
        ModAck,
        ModNameComment,
        ModSk,
        ModSn,
        ModStatusGroups,
        ModStatusOutput,
        ModStatusOutputNative,
        ModStatusRelays,
        ModStatusBinSensors,
        ModStatusVar,
        ModStatusLedsAndLogicOps,
        ModStatusKeyLocks,
        ModStatusAccessControl,
        ModStatusSceneOutputs,
        ModStatusMotorPositionBS4,
        ModStatusMotorPositionModule,
        ModSendCommandHost,
        ModSendKeysHost,
        Unknown,
    ]

    @staticmethod
    def parse(data: str) -> list[Input]:
        """Parse all input objects for given input data.

        :param    str    data:    The input data received from LCN-PCHK

        :return:    The parsed Inputs (never null)
        :rtype:     List with instances of :class:`~pypck.input.Input`
        """
        for parser in InputParser.parsers:
            ret: list[Input] | None = parser.try_parse(data)
            if ret is not None:
                return ret

        # We must never get to this point since the Unknown parser matches
        # everything.
        assert False
