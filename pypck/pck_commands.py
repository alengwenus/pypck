"""PCK command parsers and generators."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pypck import lcn_defs
from pypck.lcn_addr import LcnAddr


class PckParser:
    """Helpers to parse LCN-PCK commands.

    LCN-PCK is the command-syntax used by LCN-PCHK to send and receive LCN
    commands.
    """

    # Authentication at LCN-PCHK: Request user name.
    AUTH_USERNAME = "Username:"

    # Authentication at LCN-PCHK: Request password.
    AUTH_PASSWORD = "Password:"

    # Authentication at LCN-PCHK succeeded.
    AUTH_OK = "OK"

    # Authentication at LCN-PCHK failed.
    AUTH_FAILED = "Authentification failed."

    # LCN-PK/PKU is connected.
    LCNCONNSTATE_CONNECTED = "$io:#LCN:connected"

    # LCN-PK/PKU is disconnected.
    LCNCONNSTATE_DISCONNECTED = "$io:#LCN:disconnected"

    # Decimal mode set
    DEC_MODE_SET = "(dec-mode)"

    # License Error
    LICENSE_ERROR = "$err:(license?)"

    # Pattern to parse error messages.
    PATTERN_COMMAND_ERROR = re.compile(r"\((?P<message>.+)\?\)")

    # Pattern to parse ping messages.
    PATTERN_PING = re.compile(r"\^ping(?P<count>\d*)-")

    # Pattern to parse positive acknowledges.
    PATTERN_ACK_POS = re.compile(r"-M(?P<seg_id>\d{3})(?P<mod_id>\d{3})!")

    # Pattern to parse negative acknowledges.
    PATTERN_ACK_NEG = re.compile(r"-M(?P<seg_id>\d{3})(?P<mod_id>\d{3})(?P<code>\d+)")

    # Pattern to parse segment coupler responses.
    PATTERN_SK_RESPONSE = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.SK(?P<id>\d+)"
    )

    # Pattern to parse serial number and firmware date responses.
    PATTERN_SN = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.SN(?P<hardware_serial>[0-9|A-F]{10})"
        r"(?P<manu>.{2})FW(?P<software_serial>[0-9|A-F]{6})"
        r"HW(?P<hardware_type>\d+)"
    )

    # Pattern to parse module name and comment
    PATTERN_NAME_COMMENT = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.(?P<command>[NKO])"
        r"(?P<block_id>\d)(?P<text>.{0,12})"
    )

    # Pattern to parse the static and dynamic group membership status
    PATTERN_STATUS_GROUPS = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.G(?P<kind>[DP])(?P<max_groups>\d{3})"
        r"(?:(?P<g1>\d{3}))?(?:(?P<g2>\d{3}))?(?:(?P<g3>\d{3}))?(?:(?P<g4>\d{3}))?"
        r"(?:(?P<g5>\d{3}))?(?:(?P<g6>\d{3}))?(?:(?P<g7>\d{3}))?(?:(?P<g8>\d{3}))?"
        r"(?:(?P<g9>\d{3}))?(?:(?P<g10>\d{3}))?(?:(?P<g11>\d{3}))?(?:(?P<g12>\d{3}))?"
    )

    # Pattern to parse output-port status responses in percent.
    PATTERN_STATUS_OUTPUT_PERCENT = re.compile(
        r":M(?P<seg_id>\d{3})(?P<mod_id>\d{3})A(?P<output_id>\d)(?P<percent>\d+)"
    )

    # Pattern to parse output-port status responses in native format (0..200).
    PATTERN_STATUS_OUTPUT_NATIVE = re.compile(
        r":M(?P<seg_id>\d{3})(?P<mod_id>\d{3})O(?P<output_id>\d)(?P<value>\d+)"
    )

    # Pattern to parse relays status responses.
    PATTERN_STATUS_RELAYS = re.compile(
        r":M(?P<seg_id>\d{3})(?P<mod_id>\d{3})Rx(?P<byte_value>\d+)"
    )

    # Pattern to parse binary-sensors status responses.
    PATTERN_STATUS_BINSENSORS = re.compile(
        r":M(?P<seg_id>\d{3})(?P<mod_id>\d{3})Bx(?P<byte_value>\d+)"
    )

    # Pattern to parse variable 1-12 status responses (since 170206).
    PATTERN_STATUS_VAR = re.compile(
        r"%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.A(?P<id>\d{3})(?P<value>\d+)"
    )

    # Pattern to parse set-point variable status responses (since 170206).
    PATTERN_STATUS_SETVAR = re.compile(
        r"%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.S(?P<id>\d)(?P<value>\d+)"
    )

    # Pattern to parse threshold status responses (since 170206).
    PATTERN_STATUS_THRS = re.compile(
        r"%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.T(?P<register_id>\d)"
        r"(?P<thrs_id>\d)(?P<value>\d+)"
    )

    # Pattern to parse S0-input status responses (LCN-BU4L).
    PATTERN_STATUS_S0INPUT = re.compile(
        r"%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.C(?P<id>\d)(?P<value>\d+)"
    )

    # Pattern to parse generic variable status responses (concrete type
    # unknown, before 170206).
    PATTERN_VAR_GENERIC = re.compile(
        r"%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.(?P<value>\d+)"
    )

    # Pattern to parse threshold register 1 status responses (5 values,
    # before 170206). */
    PATTERN_THRS5 = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.S1(?P<value1>\d{5})"
        r"(?P<value2>\d{5})(?P<value3>\d{5})(?P<value4>\d{5})"
        r"(?P<value5>\d{5})(?P<hyst>\d{5})"
    )

    # Pattern to parse status of LEDs and logic-operations responses.
    PATTERN_STATUS_LEDSANDLOGICOPS = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.TL(?P<led_states>[AEBF]{12})"
        r"(?P<logic_op_states>[NTV]{4})"
    )

    # Pattern to parse key-locks status responses.
    PATTERN_STATUS_KEYLOCKS = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.TX(?P<table0>\d{3})"
        r"(?P<table1>\d{3})(?P<table2>\d{3})((?P<table3>\d{3}))?"
    )

    # Pattern to parse scene output status messages.
    PATTERN_STATUS_SCENE_OUTPUTS = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.SZ(?P<scene_id>\d{3})"
        r"(?P<output1>\d{3})(?P<ramp1>\d{3})(?P<output2>\d{3})(?P<ramp2>\d{3})"
        r"(?P<output3>\d{3})(?P<ramp3>\d{3})(?P<output4>\d{3})(?P<ramp4>\d{3})"
    )

    # Pattern to parse send command to host messages.
    PATTERN_SEND_COMMAND_HOST = re.compile(
        r"(\$M|\+M004)(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.SKH"
        r"(?P<p1>\d{3})(?P<p2>\d{3})"
        r"(?:(?P<p3>\d{3})(?P<p4>\d{3})(?P<p5>\d{3})(?P<p6>\d{3}))?"
        r"(?:(?P<p7>\d{3})(?P<p8>\d{3})(?P<p9>\d{3})(?P<p10>\d{3})"
        r"(?P<p11>\d{3})(?P<p12>\d{3})(?P<p13>\d{3})(?P<p14>\d{3}))?"
    )

    # Pattern to parse send key to host messages.
    PATTERN_SEND_KEYS_HOST = re.compile(
        r"(\$M|\+M004)(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.STH"
        r"(?P<actions>\d{3})(?P<keys>\d{3})"
    )

    # Pattern to parse transmitter status messages.
    PATTERN_STATUS_TRANSMITTER = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.ZI"
        r"(?P<code1>\d{3})(?P<code2>\d{3})(?P<code3>\d{3})"
        r"(?P<level>\d{2})(?P<key>\d)(?P<action>\d{3})"
    )

    # Pattern to parse transponder status messages.
    PATTERN_STATUS_TRANSPONDER = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.ZT"
        r"(?P<code1>\d{3})(?P<code2>\d{3})(?P<code3>\d{3})"
    )

    # Pattern to parse fingerprint status messages.
    PATTERN_STATUS_FINGERPRINT = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.ZF"
        r"(?P<code1>\d{3})(?P<code2>\d{3})(?P<code3>\d{3})"
    )

    # Pattern to parse codelock status messages.
    PATTERN_STATUS_CODELOCK = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.ZC"
        r"(?P<code1>\d{3})(?P<code2>\d{3})(?P<code3>\d{3})"
    )

    # Pattern to parse motor position BS4 status messages.
    PATTERN_STATUS_MOTOR_POSITION_BS4 = re.compile(
        r"=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\."
        r"RM(?P<motor1_id>[1-4])(?P<position1>[0-9]{3})(?P<limit1>[0-9]{3}|\?)"
        r"(?P<time_down1>[0-9]{5}|\?)(?P<time_up1>[0-9]{5}|\?)"
        r"RM(?P<motor2_id>[1-4])(?P<position2>[0-9]{3})(?P<limit2>[0-9]{3}|\?)"
        r"(?P<time_down2>[0-9]{5}|\?)(?P<time_up2>[0-9]{5}|\?)"
    )

    # Pattern to parse motor position module status messages.
    PATTERN_STATUS_MOTOR_POSITION_MODULE = re.compile(
        r":M(?P<seg_id>\d{3})(?P<mod_id>\d{3})"
        r"P(?P<motor_id>[1-4])(?P<position>[0-9]{3})"
    )

    @staticmethod
    def get_boolean_value(input_byte: int) -> list[bool]:
        """Get boolean representation for the given byte.

        :param    int    input_byte:    Input byte as int8.

        :return:    List with 8 boolean values.
        :rtype:     list
        """
        if (input_byte < 0) or (input_byte > 255):
            raise ValueError("Invalid input_byte.")

        result = []
        for i in range(8):
            result.append((input_byte & (1 << i)) != 0)
        return result


class PckGenerator:
    """Helpers to generate LCN-PCK commands.

    LCN-PCK is the command-syntax used by LCN-PCHK to send and receive LCN
    commands.
    """

    # Terminates a PCK command
    TERMINATION = "\n"

    TABLE_NAMES = ["A", "B", "C", "D"]

    @staticmethod
    def ping(counter: int) -> str:
        """Generate a keep-alive.

        LCN-PCHK will close the connection if it does not receive any commands
        specific period (10 minutes by default).

        :param    int    counter:    The current ping's id (optional, but
                                     'best practice'). Should start with 1
        :return:    The PCK command as text
        :rtype:    str
        """
        return f"^ping{counter:d}"

    @staticmethod
    def set_dec_mode() -> str:
        """Generate PCK command to set used number system to decimal."""
        return "!CHD"

    @staticmethod
    def set_operation_mode(
        dim_mode: lcn_defs.OutputPortDimMode, status_mode: lcn_defs.OutputPortStatusMode
    ) -> str:
        """Generate a PCK command to set the connection's operation mode.

        This influences how output-port commands and status are interpreted
        and must be in sync with the LCN bus.

        :param    OuputPortDimMode        dimMode:        The dimming mode
                                                          (50/200 steps)
        :param    OutputPortStatusMode    statusMode:     The status mode
                                                          (percent/native)
        :return:    The PCK command as text
        :rtype:    str
        """
        return (
            "!OM"
            f"{'1' if (dim_mode == lcn_defs.OutputPortDimMode.STEPS200) else '0'}"
            f"{'P' if (status_mode == lcn_defs.OutputPortStatusMode.PERCENT) else 'N'}"
        )

    @staticmethod
    def generate_address_header(
        addr: LcnAddr, local_seg_id: int, wants_ack: bool
    ) -> str:
        """Generate a PCK command address header.

        :param    addr:   The module's/group's address
        :type     addr:   :class:`~LcnAddr`
        :param    int     local_seg_id:    The local segment id
        :param    bool    wants_ack:      Is an acknowledge requested.

        :return:    The PCK address header string.
        :rtype:     str
        """
        return (
            ">"
            f"{'G' if addr.is_group else 'M'}"
            f"{addr.get_physical_seg_id(local_seg_id):03d}"
            f"{addr.addr_id:03d}"
            f"{'!' if wants_ack else '.'}"
        )

    @staticmethod
    def segment_coupler_scan() -> str:
        """Generate a scan-command for LCN segment-couplers.

        Used to detect the local segment (where the physical bus connection is
        located).

        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        return "SK"

    @staticmethod
    def request_serial() -> str:
        """Generate a firmware/serial-number request.

        :return: The PCK command (without address header) as text
        :rtype:    str
        """
        return "SN"

    @staticmethod
    def request_name(block_id: int) -> str:
        """Generate a name request.

        :return The PCK command (without address header) as text
        :rtype:    str
        """
        if block_id not in [0, 1]:
            raise ValueError("Invalid block_id.")
        return f"NMN{block_id + 1}"

    @staticmethod
    def request_comment(block_id: int) -> str:
        """Generate a comment request.

        :return The PCK command (without address header) as text
        :rtype:    str
        """
        if block_id not in [0, 1, 2]:
            raise ValueError("Invalid block_id.")
        return f"NMK{block_id + 1}"

    @staticmethod
    def request_oem_text(block_id: int) -> str:
        """Generate an oem text request.

        :return The PCK command (without address header) as text
        :rtype:    str
        """
        if block_id not in [0, 1, 2, 3]:
            raise ValueError("Invalid block_id.")
        return f"NMO{block_id + 1}"

    @staticmethod
    def request_group_membership_static() -> str:
        """Generate a group membership request for static membership (EEPROM).

        :return The PCK command (without address header) as text
        :rtype:    str
        """
        return "GP"

    @staticmethod
    def request_group_membership_dynamic() -> str:
        """Generate a group membership request for dynamic membership.

        :return The PCK command (without address header) as text
        :rtype:    str
        """
        return "GD"

    @staticmethod
    def request_output_status(output_id: int) -> str:
        """Generate an output-port status request.

        :param    int    output_id:    Output id 0..3
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError("Invalid output_id.")
        return f"SMA{output_id + 1}"

    @staticmethod
    def dim_output(output_id: int, percent: float, ramp: int) -> str:
        """Generate a dim command for a single output-port.

        :param    int    output_id:    Output id 0..3
        :param    float  percent:      Brightness in percent 0..100
        :param    int    ramp:         Ramp value
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError("Invalid output_id.")
        percent_round = int(round(percent * 2))
        ramp = int(ramp)
        if (percent_round % 2) == 0:
            # Use the percent command (supported by all LCN-PCHK versions)
            pck = f"A{output_id + 1}DI{percent_round // 2:03d}{ramp:03d}"
        else:
            # We have a ".5" value. Use the native command (supported since
            # LCN-PCHK 2.3)
            pck = f"O{output_id + 1}DI{percent_round:03d}{ramp:03d}"
        return pck

    @staticmethod
    def dim_all_outputs(percent: float, ramp: int, software_serial: int) -> str:
        """Generate a dim command for all output-ports.

        :param    float  percent:           Brightness in percent 0..100
        :param    int    ramp:              Ramp value
        :param    int    software_serial:   The expected firmware version of all
                                            receiving modules.
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        percent_round = int(round(percent * 2))
        if software_serial >= 0x180501:
            # Supported since LCN-PCHK 2.61
            pck = (
                "OY"
                f"{percent_round:03d}"
                f"{percent_round:03d}"
                f"{percent_round:03d}"
                f"{percent_round:03d}"
                f"{ramp:03d}"
            )
        elif percent_round == 0:  # All off
            pck = f"AA{ramp:03d}"
        elif percent_round == 200:  # All on
            pck = f"AE{ramp:03d}"
        else:
            # This is our worst-case: No high-res, no ramp
            pck = f"AH{percent_round // 2:03d}"
        return pck

    @staticmethod
    def rel_output(output_id: int, percent: float) -> str:
        """Generate a command to change the value of an output-port.

        :param    int    output_id:    Output id 0..3
        :param    float  percent:      Relative percentage -100..100
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError("Invalid output_id.")

        percent_round = int(round(percent * 2))
        if percent_round % 2 == 0:
            # Use the percent command (supported by all LCN-PCHK versions)
            pck = (
                "A"
                f"{output_id + 1}"
                f"{'AD' if percent >= 0 else 'SB'}"
                f"{abs(percent_round // 2):03d}"
            )
        else:
            # We have a ".5" value. Use the native command (supported since
            # LCN-PCHK 2.3)
            pck = (
                "O"
                f"{output_id + 1}"
                f"{'AD' if percent >= 0 else 'SB'}"
                f"{abs(percent_round):03d}"
            )
        return pck

    @staticmethod
    def toggle_output(output_id: int, ramp: int, to_memory: bool = False) -> str:
        """Generate a command that toggles a single output-port.

        Toggle mode: (on->off, off->on).

        :param    int    output_id:    Output id 0..3
        :param    int    ramp:         Ramp value
        :param    bool   to_memory:    If True, the dimming status is stored

        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError("Invalid output_id.")
        return f"A{output_id + 1}{'MT' if to_memory else 'TA'}{ramp:03d}"

    @staticmethod
    def toggle_all_outputs(ramp: int) -> str:
        """Generate a command that toggles all output-ports.

        Toggle mode: (on->off, off->on).

        :param    int    ramp:    Ramp value
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        return f"AU{ramp:03d}"

    @staticmethod
    def request_relays_status() -> str:
        """Generate a relays-status request.

        :return: The PCK command (without address header) as text
        :rtype:    str
        """
        return "SMR"

    @staticmethod
    def control_relays(states: list[lcn_defs.RelayStateModifier]) -> str:
        """Generate a command to control relays.

        :param     RelayStateModifier    states:    The 8 modifiers for the
                                                    relay states as a list
        :return:   The PCK command (without address header) as text
        :rtype:    str
        """
        if len(states) != 8:
            raise ValueError("Invalid states length.")
        ret = "R8"
        for state in states:
            ret += state.value

        return ret

    @staticmethod
    def control_relays_timer(
        time_msec: int, states: list[lcn_defs.RelayStateModifier]
    ) -> str:
        """Generate a command to control relays.

        :param     int                   time_msec: Duration of timer in
                                                    milliseconds
        :param     RelayStateModifier    states:    The 8 modifiers for the
                                                    relay states as a list
                                                    (only ON and OFF allowed)
        :return:   The PCK command (without address header) as text
        :rtype:    str
        """
        if len(states) != 8:
            raise ValueError("Invalid states length.")
        value = lcn_defs.time_to_native_value(time_msec)
        ret = f"R8T{value:03d}"
        for state in states:
            assert state in (
                lcn_defs.RelayStateModifier.ON,
                lcn_defs.RelayStateModifier.OFF,
            )
            ret += state.value

        return ret

    @staticmethod
    def control_motor_relays(
        motor_id: int,
        state: lcn_defs.MotorStateModifier,
        mode: lcn_defs.MotorPositioningMode = lcn_defs.MotorPositioningMode.NONE,
    ) -> str:
        """Generate a command to control motors via relays.

        :param    int                 motor_id:    The motor id 0..3
        :param    MotorStateModifier  state:       The modifier for the
                                                   motor state
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if 0 > motor_id > 3:
            raise ValueError("Invalid motor id")

        if mode not in lcn_defs.MotorPositioningMode:
            raise ValueError("Wrong motor position mode")

        if mode == lcn_defs.MotorPositioningMode.BS4:
            new_motor_id = [1, 2, 5, 6][motor_id]
            if state == lcn_defs.MotorStateModifier.DOWN:
                # AU=window open / cover down
                action = "AU"
            elif state == lcn_defs.MotorStateModifier.UP:
                # ZU=window close / cover up
                action = "ZU"
            elif state == lcn_defs.MotorStateModifier.STOP:
                action = "ST"
            else:
                raise ValueError("Invalid motor state for BS4 mode")

            return f"R8M{new_motor_id}{action}"

        # lcn_defs.MotorPositioningMode.NONE
        # lcn_defs.MotorPositioningMode.MODULE
        if state == lcn_defs.MotorStateModifier.UP:
            port_onoff = lcn_defs.RelayStateModifier.ON
            port_updown = lcn_defs.RelayStateModifier.OFF
        elif state == lcn_defs.MotorStateModifier.DOWN:
            port_onoff = lcn_defs.RelayStateModifier.ON
            port_updown = lcn_defs.RelayStateModifier.ON
        elif state == lcn_defs.MotorStateModifier.STOP:
            port_onoff = lcn_defs.RelayStateModifier.OFF
            port_updown = lcn_defs.RelayStateModifier.NOCHANGE
        elif state == lcn_defs.MotorStateModifier.TOGGLEONOFF:
            port_onoff = lcn_defs.RelayStateModifier.TOGGLE
            port_updown = lcn_defs.RelayStateModifier.NOCHANGE
        elif state == lcn_defs.MotorStateModifier.TOGGLEDIR:
            port_onoff = lcn_defs.RelayStateModifier.NOCHANGE
            port_updown = lcn_defs.RelayStateModifier.TOGGLE
        elif state == lcn_defs.MotorStateModifier.CYCLE:
            port_onoff = lcn_defs.RelayStateModifier.TOGGLE
            port_updown = lcn_defs.RelayStateModifier.TOGGLE
        elif state == lcn_defs.MotorStateModifier.NOCHANGE:
            port_onoff = lcn_defs.RelayStateModifier.NOCHANGE
            port_updown = lcn_defs.RelayStateModifier.NOCHANGE
        else:
            raise ValueError("Invalid motor state")

        states = [lcn_defs.RelayStateModifier.NOCHANGE] * 8
        states[motor_id * 2] = port_onoff
        states[motor_id * 2 + 1] = port_updown
        return "R8" + "".join([state.value for state in states])

    @staticmethod
    def control_motor_relays_position(
        motor_id: int, position: float, mode: lcn_defs.MotorPositioningMode
    ) -> str:
        """Control motor position via relays and BS4 or module.

        :param    int                   motor_id:   The motor port of the LCN module
        :param    float                 position:   The position to set in percentage (0..100)
                                                    (0: closed cover, 100: open cover)
        :param    MotorPositioningMode  mode:       The motor positioning mode

        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if mode not in (
            lcn_defs.MotorPositioningMode.BS4,
            lcn_defs.MotorPositioningMode.MODULE,
        ):
            raise ValueError("Wrong motor positioning mode")

        if 0 > motor_id > 3:
            raise ValueError("Invalid motor")

        if mode == lcn_defs.MotorPositioningMode.BS4:
            new_motor_id = [1, 2, 5, 6][motor_id]
            action = f"GP{int(200 - 2 * position):03d}"
            return f"R8M{new_motor_id}{action}"
        elif mode == lcn_defs.MotorPositioningMode.MODULE:
            new_motor_id = 1 << motor_id
            return f"JH{100 - position:03d}{new_motor_id:03d}"

        return ""

    @staticmethod
    def request_motor_position_status(motor_pair: int) -> str:
        """Generate a motor position status request for BS4.

        :param    int    motor_pair:    Motor pair 0: 1, 2; 1: 3, 4

        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        if motor_pair not in [0, 1]:
            raise ValueError("Invalid motor_pair.")
        return f"R8M{7 if motor_pair else 3}P{motor_pair + 1}"

    @staticmethod
    def control_motor_outputs(
        state: lcn_defs.MotorStateModifier,
        reverse_time: lcn_defs.MotorReverseTime | None = None,
    ) -> str:
        """Generate a command to control a motor via output ports 1+2.

        :param    MotorStateModifier    state:     The modifier for the
                                                   motor state
        :param    MotorReverseTime      reverse_time: Reverse time for modules
                                                      with FW<190C
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if state == lcn_defs.MotorStateModifier.UP:
            if reverse_time in [None, lcn_defs.MotorReverseTime.RT70]:
                params = (0x01, 0xE4, 0x00)
                ret = f"X2{params[0]:03d}{params[1]:03d}{params[2]:03d}"
            elif reverse_time == lcn_defs.MotorReverseTime.RT600:
                ret = PckGenerator.dim_output(0, 100, 8)
            elif reverse_time == lcn_defs.MotorReverseTime.RT1200:
                ret = PckGenerator.dim_output(0, 100, 11)
            else:
                raise ValueError("Wrong MotorReverseTime.")

        elif state == lcn_defs.MotorStateModifier.DOWN:
            if reverse_time in [None, lcn_defs.MotorReverseTime.RT70]:
                params = (0x01, 0x00, 0xE4)
                ret = f"X2{params[0]:03d}{params[1]:03d}{params[2]:03d}"
            elif reverse_time == lcn_defs.MotorReverseTime.RT600:
                ret = PckGenerator.dim_output(1, 100, 8)
            elif reverse_time == lcn_defs.MotorReverseTime.RT1200:
                ret = PckGenerator.dim_output(1, 100, 11)
            else:
                raise ValueError("Wrong MotorReverseTime.")

        elif state == lcn_defs.MotorStateModifier.STOP:
            ret = "AY000000"
        elif state == lcn_defs.MotorStateModifier.CYCLE:
            ret = "JE"
        else:
            raise ValueError("MotorStateModifier is not supported by output ports.")

        return ret

    @staticmethod
    def request_bin_sensors_status() -> str:
        """Generate a binary-sensors status request.

        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        return "SMB"

    @staticmethod
    def var_abs(var: lcn_defs.Var, value: int) -> str:
        """Generate a command that sets a variable absolute.

        :param    Var    var:    The target variable to set
        :param    int    value:  The absolute value to set
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        set_point_id = lcn_defs.Var.to_set_point_id(var)
        if set_point_id != -1:
            # Set absolute (not in PCK yet)
            byte1 = set_point_id << 6  # 01000000
            byte1 |= 0x20  # xx10xxxx (set absolute)
            value -= 1000  # Offset
            byte1 |= (value >> 8) & 0x0F  # xxxx1111
            byte2 = value & 0xFF
            return f"X2{30:03d}{byte1:03d}{byte2:03d}"

        # Setting variables and thresholds absolute not implemented in LCN
        # firmware yet
        raise ValueError("Wrong variable type.")

    @staticmethod
    def update_status_var(var: lcn_defs.Var, value: int) -> str:
        """Generate a command that send variable status updates.

        PCHK provides this variables by itself on selected segments
        is only possible with group 4

        :param    Var    var:    The target variable to set
        :param    int    value:  The absolute value to set
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        var_id = lcn_defs.Var.to_var_id(var)
        if var_id != -1:
            # define variable to set, offset 0x01000000
            x2cmd = var_id | 0x40
            byte1 = (value >> 8) & 0xFF
            byte2 = value & 0xFF
            return f"X2{x2cmd:03d}{byte1:03d}{byte2:03d}"

        # Setting variables and thresholds absolute not implemented in LCN
        # firmware yet
        raise ValueError("Wrong variable type.")

    @staticmethod
    def var_reset(var: lcn_defs.Var, software_serial: int) -> str:
        """Generate a command that resets a variable to 0.

        :param    Var    var:               The target variable to set 0
        :param    int    software_serial:   The expected firmware version of all
                                            receiving modules.
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        var_id = lcn_defs.Var.to_var_id(var)
        if var_id != -1:
            if software_serial >= 0x170206:
                pck = f"Z-{var_id + 1:03d}{4090:04d}"
            else:
                if var_id == 0:
                    pck = "ZS30000"
                else:
                    raise ValueError("Wrong variable type.")
            return pck

        set_point_id = lcn_defs.Var.to_set_point_id(var)
        if set_point_id != -1:
            # Set absolute = 0 (not in PCK yet)
            byte1 = set_point_id << 6  # 01000000
            byte1 |= 0x20  # xx10xxxx 9set absolute)
            byte2 = 0
            return f"X2{30:03d}{byte1:03d}{byte2:03d}"

        # Reset for threshold not implemented in LCN firmware yet
        raise ValueError("Wrong variable type.")

    @staticmethod
    def var_rel(
        var: lcn_defs.Var,
        rel_var_ref: lcn_defs.RelVarRef,
        value: int,
        software_serial: int,
    ) -> str:
        """Generate a command to change the value of a variable.

        :param    Var       var:                The target variable to change
        :param    RelVarRef rel_var_ref:        The reference-point
        :param    int       value:              The native LCN value to add/subtract
                                                (can be negative)
        :param    int       software_serial:    The expected firmware version of all
                                                receiving modules.
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        var_id = lcn_defs.Var.to_var_id(var)
        if var_id != -1:
            if var_id == 0:
                # Old command for variable 1 / T-var (compatible with all
                # modules)
                pck = f"Z{'A' if value >= 0 else 'S'}{abs(value)}"
            else:
                # New command for variable 1-12 (compatible with all modules,
                # since LCN-PCHK 2.8)
                pck = f"Z{'+' if value >= 0 else '-'}{var_id + 1:03d}{abs(value)}"
            return pck

        set_point_id = lcn_defs.Var.to_set_point_id(var)
        if set_point_id != -1:
            pck = (
                "RE"
                f"{'A' if set_point_id == 0 else 'B'}"
                f"S{'A' if rel_var_ref == lcn_defs.RelVarRef.CURRENT else 'P'}"
                f"{'+' if value >= 0 else '-'}"
                f"{abs(value)}"
            )
            return pck

        thrs_register_id = lcn_defs.Var.to_thrs_register_id(var)
        thrs_id = lcn_defs.Var.to_thrs_id(var)
        if (thrs_register_id != -1) and (thrs_id != -1):
            if software_serial >= 0x170206:
                # New command for registers 1-4 (since 170206, LCN-PCHK 2.8)
                pck = (
                    "SS"
                    f"{'R' if rel_var_ref == lcn_defs.RelVarRef.CURRENT else 'E'}"
                    f"{abs(value):04d}"
                    f"{'A' if value >= 0 else 'S'}"
                    f"R{thrs_register_id + 1}"
                    f"{thrs_id + 1}"
                )
            elif thrs_register_id == 0:
                # Old command for register 1 (before 170206)
                pck = (
                    "SS"
                    f"{'R' if rel_var_ref == lcn_defs.RelVarRef.CURRENT else 'E'}"
                    f"{abs(value):04d}"
                    f"{'A' if value >= 0 else 'S'}"
                    f"{'1' if thrs_id == 0 else '0'}"
                    f"{'1' if thrs_id == 1 else '0'}"
                    f"{'1' if thrs_id == 2 else '0'}"
                    f"{'1' if thrs_id == 3 else '0'}"
                    f"{'1' if thrs_id == 4 else '0'}"
                )
            return pck

        raise ValueError("Wrong variable type.")

    @staticmethod
    def request_var_status(var: lcn_defs.Var, software_serial: int) -> str:
        """Generate a variable value request.

        :param    Var    var:               The variable to request
        :param    int    software_serial:   The target module's firmware version
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if software_serial >= 0x170206:
            var_id = lcn_defs.Var.to_var_id(var)
            if var_id != -1:
                return f"MWT{var_id + 1:03d}"

            set_point_id = lcn_defs.Var.to_set_point_id(var)
            if set_point_id != -1:
                return f"MWS{set_point_id + 1:03d}"

            thrs_register_id = lcn_defs.Var.to_thrs_register_id(var)
            if thrs_register_id != -1:
                # Whole register
                return f"SE{thrs_register_id + 1:03d}"

            s0_id = lcn_defs.Var.to_s0_id(var)
            if s0_id != -1:
                return f"MWC{s0_id + 1:03d}"
        else:
            if var == lcn_defs.Var.VAR1ORTVAR:
                pck = "MWV"
            elif var == lcn_defs.Var.VAR2ORR1VAR:
                pck = "MWTA"
            elif var == lcn_defs.Var.VAR3ORR2VAR:
                pck = "MWTB"
            elif var == lcn_defs.Var.R1VARSETPOINT:
                pck = "MWSA"
            elif var == lcn_defs.Var.R2VARSETPOINT:
                pck = "MWSB"
            elif var in [
                lcn_defs.Var.THRS1,
                lcn_defs.Var.THRS2,
                lcn_defs.Var.THRS3,
                lcn_defs.Var.THRS4,
                lcn_defs.Var.THRS5,
            ]:
                pck = "SL1"  # Whole register
            return pck

        raise ValueError("Wrong variable type.")

    @staticmethod
    def request_leds_and_logic_ops() -> str:
        """Generate a request for LED and logic-operations states.

        :return: The PCK command (without address header) as text
        :rtype:  str
        """
        return "SMT"

    @staticmethod
    def control_led(led_id: int, state: lcn_defs.LedStatus) -> str:
        """Generate a command to the set the state of a single LED.

        :param    int          led_id:   Led id 0..11
        :param    LedStatus    state:    The state to set
        :return: The PCK command (without address header) as text
        :rtype:  str
        """
        if (led_id < 0) or (led_id > 11):
            raise ValueError("Bad led_id.")
        return f"LA{led_id + 1:03d}{state.value}"

    @staticmethod
    def send_keys(cmds: list[lcn_defs.SendKeyCommand], keys: list[bool]) -> str:
        """Generate a command to send LCN keys.

        :param    SendKeyCommand    cmds:    The 4 concrete commands to send
                                             for the tables (A-D) as list
        :param    list(bool)        keys:    The tables' 8 key-states (True
                                             means "send") as list

        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if (len(cmds) != 4) or (len(keys) != 8):
            raise ValueError("Wrong cmds length or wrong keys length.")
        ret = "TS"
        for i, cmd in enumerate(cmds):
            if (cmd == lcn_defs.SendKeyCommand.DONTSEND) and (i == 3):
                # By skipping table D (if it is not used), we use the old
                # command
                # for table A-C which is compatible with older LCN modules
                break
            ret += cmd.value

        for key in keys:
            ret += "1" if key else "0"

        return ret

    @staticmethod
    def send_keys_hit_deferred(
        table_id: int, time: int, time_unit: lcn_defs.TimeUnit, keys: list[bool]
    ) -> str:
        """Generate a command to send LCN keys deferred / delayed.

        :param     int         table_id:    Table id 0(A)..3(D)
        :param     int         time:        The delay time
        :param     TimeUnit    time_unit:   The time unit
        :param     list(bool)  keys:        The table's 8 key-states (True
                                            means "send") as list
        :return:   The PCK command (without address header) as text
        :rtype:    str
        """
        if (table_id < 0) or (table_id > 3) or (len(keys) != 8):
            raise ValueError("Bad table_id or keys.")
        ret = "TV"
        try:
            ret += PckGenerator.TABLE_NAMES[table_id]
        except IndexError as exc:
            raise ValueError("Wrong table_id.") from exc

        ret += f"{time:03d}"
        if time_unit == lcn_defs.TimeUnit.SECONDS:
            if (time < 1) or (time > 60):
                raise ValueError("Wrong time.")
            ret += "S"
        elif time_unit == lcn_defs.TimeUnit.MINUTES:
            if (time < 1) or (time > 90):
                raise ValueError("Wrong time.")
            ret += "M"
        elif time_unit == lcn_defs.TimeUnit.HOURS:
            if (time < 1) or (time > 50):
                raise ValueError("Wrong time.")
            ret += "H"
        elif time_unit == lcn_defs.TimeUnit.DAYS:
            if (time < 1) or (time > 45):
                raise ValueError("Wrong time.")
            ret += "D"
        else:
            raise ValueError("Wrong time_unit.")

        for key in keys:
            ret += "1" if key else "0"

        return ret

    @staticmethod
    def request_key_lock_status() -> str:
        """Generate a request for key-lock states.

        Always requests table A-D. Supported since LCN-PCHK 2.8.

        :return:    The PCK command (without address header) as text
        :rtype:     str
        """
        return "STX"

    @staticmethod
    def lock_keys(table_id: int, states: list[lcn_defs.KeyLockStateModifier]) -> str:
        """Generate a command to lock keys.

        :param     int           table_id:  Table id 0(A)..3(D)
        :param     list(bool)    states:    The 8 key-lock modifiers as list
        :return:   The PCK command (without address header) as text
        :rtype:    str
        """
        if (table_id < 0) or (table_id > 3) or (len(states) != 8):
            raise ValueError("Bad table_id or states.")
        try:
            ret = f"TX{PckGenerator.TABLE_NAMES[table_id]}"
        except IndexError as exc:
            raise ValueError("Wrong table_id.") from exc

        for state in states:
            ret += state.value

        return ret

    @staticmethod
    def lock_keys_tab_a_temporary(
        time: int,
        time_unit: lcn_defs.TimeUnit,
        keys: list[lcn_defs.KeyLockStateModifier],
    ) -> str:
        """Generate a command to lock keys for table A temporary.

        There is no hardware-support for locking tables B-D.

        :param     int         time:         The lock time
        :param     TimeUnit    time_unit:    The time unit
        :param     list(bool)  keys:         The 8 key-lock states (True means
                                             lock) as list
        :return:   The PCK command (without address header) as text
        :rtype:    str
        """
        if len(keys) != 8:
            raise ValueError("Wrong keys length.")
        ret = f"TXZA{time:03d}"

        if time_unit == lcn_defs.TimeUnit.SECONDS:
            if (time < 1) or (time > 60):
                raise ValueError("Wrong time.")
            ret += "S"
        elif time_unit == lcn_defs.TimeUnit.MINUTES:
            if (time < 1) or (time > 90):
                raise ValueError("Wrong time.")
            ret += "M"
        elif time_unit == lcn_defs.TimeUnit.HOURS:
            if (time < 1) or (time > 50):
                raise ValueError("Wrong time.")
            ret += "H"
        elif time_unit == lcn_defs.TimeUnit.DAYS:
            if (time < 1) or (time > 45):
                raise ValueError("Wrong time.")
            ret += "D"
        else:
            raise ValueError("Wrong time_unit.")

        for key in keys:
            ret += "1" if key == lcn_defs.KeyLockStateModifier.ON else "0"

        return ret

    @staticmethod
    def dyn_text_part(row_id: int, part_id: int, part: bytes) -> bytes:
        """Generate the command header / start for sending dynamic texts.

        Used by LCN-GTxD periphery (supports 4 text rows).
        To complete the command, the text to send must be appended (UTF-8
        encoding).
        Texts are split up into up to 5 parts with 12 "UTF-8 bytes" each.

        :param    int    row_id:    Row id 0..3
        :param    int    part_id:   Part id 0..4
        :param    bytes  part:      Text part (up to 12 bytes), encoded as
                                    lcn_defs.LCN_ENCODING
        :return:  The PCK command (without address header) as encoded bytes
        :rtype:   bytes
        """
        if (
            (row_id < 0)
            or (row_id > 3)
            or (part_id < 0)
            or (part_id > 4)
            or (len(part) > 12)
        ):
            raise ValueError("Wrong row_id, part_id or part length.")
        return f"GTDT{row_id + 1}{part_id + 1}".encode() + part

    @staticmethod
    def lock_regulator(
        reg_id: int,
        state: bool,
        software_serial: int,
        target_value: float = -1,
    ) -> str:
        """Generate a command to lock a regulator.

        :param    int    reg_id:    Regulator id 0..1
        :param    bool   state:     The lock state
        :param    int    software_serial: The expected firmware version of all
                                           receiving modules.
        :param    foat    target_value: The target value in percent (use -1 to ignore)
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if (reg_id < 0) or (reg_id > 1):
            raise ValueError("Wrong reg_id.")
        if ((target_value < 0) or (target_value > 100)) and (target_value != -1):
            raise ValueError("Wrong target_value.")
        if (target_value != -1) and (software_serial >= 0x120301) and state:
            reg_byte = reg_id * 0x40 + 0x07
            return f"X2{0x1E:03d}{reg_byte:03d}{int(2 * target_value):03d}"
        return f"RE{'A' if reg_id == 0 else 'B'}X{'S' if state else 'A'}"

    @staticmethod
    def change_scene_register(register_id: int) -> str:
        """Change the active scene register.

        :param    int    register_id:    Register id 0..9
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if (register_id < 0) or (register_id > 9):
            raise ValueError("Wrong register_id.")
        return f"SZW{register_id:03d}"

    @staticmethod
    def store_scene_outputs_direct(
        register_id: int, scene_id: int, percents: Sequence[float], ramps: Sequence[int]
    ) -> str:
        """Store the given output values and ramps in the given scene.

        :param    int           register_id: Register id 0..9
        :param    int           scene_id:    Scene id 0..9
        :param    list(float)   percents:    Output values in percent as list
        :param    list(int)     ramp:        Ramp values as list
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if (scene_id < 0) or (scene_id > 9):
            raise ValueError("Wrong scene_id.")
        if len(percents) not in (2, 4):
            raise ValueError("Need 2 or 4 output percent values.")
        if len(ramps) != len(percents):
            raise ValueError("Need as many ramp values as output percent values.")
        cmd = f"SZD{register_id:03d}{scene_id:03d}"
        for i, percent in enumerate(percents):
            cmd += f"{int(percent * 2):03d}{ramps[i]:03d}"
        return cmd

    @staticmethod
    def activate_scene_output(
        scene_id: int,
        output_ports: Sequence[lcn_defs.OutputPort] = (),
        ramp: int | None = None,
    ) -> str:
        """Activate the stored output states for the given scene.

        Please note: The output ports 3 and 4 can only be activated
        simultaneously. If one of them is given, the other one is activated,
        too.

        :param    int                scene_id:       Scene id 0..9
        :param    list(OutputPort)   output_ports:   Output ports to activate
                                                     as list
        :param    int                ramp:           Ramp value
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        return PckGenerator._activate_or_store_scene_output(
            scene_id, output_ports, ramp, store=False
        )

    @staticmethod
    def store_scene_output(
        scene_id: int,
        output_ports: Sequence[lcn_defs.OutputPort] = (),
        ramp: int | None = None,
    ) -> str:
        """Store the current output states in the given scene.

        Please note: The output ports 3 and 4 can only be stored
        simultaneously. If one of them is given, the other one is stored,
        too.

        :param    int                scene_id:       Scene id 0..9
        :param    list(OutputPort)   output_ports:   Output ports to store
                                                     as list
        :param    int                ramp:           Ramp value
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        return PckGenerator._activate_or_store_scene_output(
            scene_id, output_ports, ramp, store=True
        )

    @staticmethod
    def _activate_or_store_scene_output(
        scene_id: int,
        output_ports: Sequence[lcn_defs.OutputPort] = (),
        ramp: int | None = None,
        store: bool = False,
    ) -> str:
        if (scene_id < 0) or (scene_id > 9):
            raise ValueError("Wrong scene_id.")
        if not output_ports:
            raise ValueError("output_port list is empty.")
        output_mask = 0
        if lcn_defs.OutputPort.OUTPUT1 in output_ports:
            output_mask += 1
        if lcn_defs.OutputPort.OUTPUT2 in output_ports:
            output_mask += 2
        if (
            lcn_defs.OutputPort.OUTPUT3 in output_ports
            or lcn_defs.OutputPort.OUTPUT4 in output_ports
        ):
            output_mask += 4
        if store:
            action = "S"
        else:
            action = "A"
        if ramp is None:
            pck = f"SZ{action:s}{output_mask:1d}{scene_id:03d}"
        else:
            pck = f"SZ{action:s}{output_mask:1d}{scene_id:03d}{ramp:03d}"
        return pck

    @staticmethod
    def activate_scene_relay(
        scene_id: int, relay_ports: Sequence[lcn_defs.RelayPort] = ()
    ) -> str:
        """Activate the stored relay states for the given scene.

        :param    int                scene_id:       Scene id 0..9
        :param    list(RelayPort)    relay_ports:    Relay ports to activate
                                                     as list
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        return PckGenerator._activate_or_store_scene_relay(
            scene_id, relay_ports, store=False
        )

    @staticmethod
    def store_scene_relay(
        scene_id: int, relay_ports: Sequence[lcn_defs.RelayPort] = ()
    ) -> str:
        """Store the current relay states in the given scene.

        :param    int                scene_id:       Scene id 0..9
        :param    list(RelayPort)    relay_ports:    Relay ports to store
                                                     as list
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        return PckGenerator._activate_or_store_scene_relay(
            scene_id, relay_ports, store=True
        )

    @staticmethod
    def _activate_or_store_scene_relay(
        scene_id: int,
        relay_ports: Sequence[lcn_defs.RelayPort] = (),
        store: bool = False,
    ) -> str:
        if (scene_id < 0) or (scene_id > 9):
            raise ValueError("Wrong scene_id.")
        if not relay_ports:
            raise ValueError("relay_port list is empty.")
        relays_mask = ["0"] * 8
        for port in relay_ports:
            relays_mask[port.value] = "1"
        if store:
            action = "S"
        else:
            action = "A"
        return f"SZ{action}0{scene_id:03d}{''.join(relays_mask)}"

    @staticmethod
    def request_status_scene(register_id: int, scene_id: int) -> str:
        """Request the stored output and ramp values for the given scene.

        :param    int    register_id:    Register id 0..9
        :param    int    register_id:    Scene id 0..9
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if (register_id < 0) or (register_id > 9):
            raise ValueError("Wrong register_id.")
        if (scene_id < 0) or (scene_id > 9):
            raise ValueError("Wrong scene_id.")
        return f"SZR{register_id:03d}{scene_id:03d}"

    @staticmethod
    def beep(sound: lcn_defs.BeepSound, count: int) -> str:
        """Make count number of beep sounds.

        :param    BeepSound sound:  Beep sound style
        :param    int       count:  Number of beeps (1..15)
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if (count < 1) or (count > 15):
            raise ValueError("Wrong number of beeps.")
        return f"PI{sound.value:s}{count:03d}"

    @staticmethod
    def empty() -> str:
        """Generate an empty command (LEER) that does nothing.

        Combine with request for acknowledgement to discover and
        ping modules and to discover and verify group memberships.

        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        return "LEER"
