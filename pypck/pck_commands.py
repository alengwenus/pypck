"""Copyright (c) 2006-2020 by the respective copyright holders.

See the NOTICE file(s) distributed with this work for additional
information.

This program and the accompanying materials are made available under the
terms of the Eclipse Public License 2.0 which is available at
http://www.eclipse.org/legal/epl-2.0

SPDX-License-Identifier: EPL-2.0

Contributors:
  Andre Lengwenus - port to Python and further improvements
  Tobias Juettner - initial LCN binding for openHAB (Java)
"""

import re
from typing import List, Optional, Sequence

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
        r"(?P<manu>[0-9|A-F]{2})FW(?P<software_serial>[0-9|A-F]{6})"
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
        r"\+M004(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.SKH"
        r"(?P<p1>\d{3})(?P<p2>\d{3})"
        r"(?:(?P<p3>\d{3})(?P<p4>\d{3})(?P<p5>\d{3})(?P<p6>\d{3}))?"
        r"(?:(?P<p7>\d{3})(?P<p8>\d{3})(?P<p9>\d{3})(?P<p10>\d{3})"
        r"(?P<p11>\d{3})(?P<p12>\d{3})(?P<p13>\d{3})(?P<p14>\d{3}))?"
    )

    # Pattern to parse send key to host messages.
    PATTERN_SEND_KEYS_HOST = re.compile(
        r"\+M004(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.STH"
        r"(?P<actions>\d{3})(?P<keys>\d{3})"
    )

    @staticmethod
    def get_boolean_value(input_byte: int) -> List[bool]:
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
        return "!OM{:s}{:s}".format(
            "1" if (dim_mode == lcn_defs.OutputPortDimMode.STEPS200) else "0",
            "P" if (status_mode == lcn_defs.OutputPortStatusMode.PERCENT) else "N",
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
        return ">{:s}{:03d}{:03d}{:s}".format(
            "G" if addr.is_group else "M",
            addr.get_physical_seg_id(local_seg_id),
            addr.addr_id,
            "!" if wants_ack else ".",
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
        return "NMN{:d}".format(block_id + 1)

    @staticmethod
    def request_comment(block_id: int) -> str:
        """Generate a comment request.

        :return The PCK command (without address header) as text
        :rtype:    str
        """
        if block_id not in [0, 1, 2]:
            raise ValueError("Invalid block_id.")
        return "NMK{:d}".format(block_id + 1)

    @staticmethod
    def request_oem_text(block_id: int) -> str:
        """Generate an oem text request.

        :return The PCK command (without address header) as text
        :rtype:    str
        """
        if block_id not in [0, 1, 2, 3]:
            raise ValueError("Invalid block_id.")
        return "NMO{:d}".format(block_id + 1)

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
        return "SMA{:d}".format(output_id + 1)

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
            pck = "A{:d}DI{:03d}{:03d}".format(output_id + 1, percent_round // 2, ramp)
        else:
            # We have a ".5" value. Use the native command (supported since
            # LCN-PCHK 2.3)
            pck = "O{:d}DI{:03d}{:03d}".format(output_id + 1, percent_round, ramp)
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
            pck = "OY{0:03d}{0:03d}{0:03d}{0:03d}{1:03d}".format(percent_round, ramp)
        elif percent_round == 0:  # All off
            pck = f"AA{ramp:03d}"
        elif percent_round == 200:  # All on
            pck = f"AE{ramp:03d}"
        else:
            # This is our worst-case: No high-res, no ramp
            pck = "AH{:03d}".format(int(percent_round / 2))
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
            pck = "A{:d}{:s}{:03d}".format(
                output_id + 1, "AD" if percent >= 0 else "SB", abs(percent_round // 2)
            )
        else:
            # We have a ".5" value. Use the native command (supported since
            # LCN-PCHK 2.3)
            pck = "O{:d}{:s}{:03d}".format(
                output_id + 1, "AD" if percent >= 0 else "SB", abs(percent_round)
            )
        return pck

    @staticmethod
    def toggle_output(output_id: int, ramp: int) -> str:
        """Generate a command that toggles a single output-port.

        Toggle mode: (on->off, off->on).

        :param    int    output_id:    Output id 0..3
        :param    int    ramp:         Ramp value
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError("Invalid output_id.")
        return "A{:d}TA{:03d}".format(output_id + 1, ramp)

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
    def control_relays(states: List[lcn_defs.RelayStateModifier]) -> str:
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
        time_msec: int, states: List[lcn_defs.RelayStateModifier]
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
    def control_motors_relays(states: List[lcn_defs.MotorStateModifier]) -> str:
        """Generate a command to control motors via relays.

        :param    MotorStateModifier    states:    The 4 modifiers for the
                                                   motor states as a list
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if len(states) != 4:
            raise ValueError("Invalid states length.")
        ret = "R8"
        for state in states:
            if state == lcn_defs.MotorStateModifier.UP:
                ret += lcn_defs.RelayStateModifier.ON.value
                ret += lcn_defs.RelayStateModifier.OFF.value
            elif state == lcn_defs.MotorStateModifier.DOWN:
                ret += lcn_defs.RelayStateModifier.ON.value
                ret += lcn_defs.RelayStateModifier.ON.value
            elif state == lcn_defs.MotorStateModifier.STOP:
                ret += lcn_defs.RelayStateModifier.OFF.value
                ret += lcn_defs.RelayStateModifier.NOCHANGE.value
            elif state == lcn_defs.MotorStateModifier.TOGGLEONOFF:
                ret += lcn_defs.RelayStateModifier.TOGGLE.value
                ret += lcn_defs.RelayStateModifier.NOCHANGE.value
            elif state == lcn_defs.MotorStateModifier.TOGGLEDIR:
                ret += lcn_defs.RelayStateModifier.NOCHANGE.value
                ret += lcn_defs.RelayStateModifier.TOGGLE.value
            elif state == lcn_defs.MotorStateModifier.CYCLE:
                ret += lcn_defs.RelayStateModifier.TOGGLE.value
                ret += lcn_defs.RelayStateModifier.TOGGLE.value
            elif state == lcn_defs.MotorStateModifier.NOCHANGE:
                ret += lcn_defs.RelayStateModifier.NOCHANGE.value
                ret += lcn_defs.RelayStateModifier.NOCHANGE.value

        return ret

    @staticmethod
    def control_motors_outputs(
        state: lcn_defs.MotorStateModifier,
        reverse_time: Optional[lcn_defs.MotorReverseTime] = None,
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
            elif reverse_time == lcn_defs.MotorReverseTime.RT600:
                params = (0x04, 0xC8, 0x08)
            elif reverse_time == lcn_defs.MotorReverseTime.RT1200:
                params = (0x04, 0xC8, 0x0B)
            else:
                raise ValueError("Wrong MotorReverseTime.")
            ret = "X2{:03d}{:03d}{:03d}".format(*params)

        elif state == lcn_defs.MotorStateModifier.DOWN:
            if reverse_time in [None, lcn_defs.MotorReverseTime.RT70]:
                params = (0x01, 0x00, 0xE4)
            elif reverse_time == lcn_defs.MotorReverseTime.RT600:
                params = (0x05, 0xC8, 0x08)
            elif reverse_time == lcn_defs.MotorReverseTime.RT1200:
                params = (0x05, 0xC8, 0x0B)
            else:
                raise ValueError("Wrong MotorReverseTime.")
            ret = "X2{:03d}{:03d}{:03d}".format(*params)

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
            return "X2{:03d}{:03d}{:03d}".format(30, byte1, byte2)

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
                pck = "Z-{:03d}{:04d}".format(var_id + 1, 4090)
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
            return "X2{:03d}{:03d}{:03d}".format(30, byte1, byte2)

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
                pck = "Z{:s}{:d}".format("A" if value >= 0 else "S", abs(value))
            else:
                # New command for variable 1-12 (compatible with all modules,
                # since LCN-PCHK 2.8)
                pck = "Z{:s}{:03d}{:d}".format(
                    "+" if value >= 0 else "-", var_id + 1, abs(value)
                )
            return pck

        set_point_id = lcn_defs.Var.to_set_point_id(var)
        if set_point_id != -1:
            pck = "RE{:s}S{:s}{:s}{:d}".format(
                "A" if set_point_id == 0 else "B",
                "A" if rel_var_ref == lcn_defs.RelVarRef.CURRENT else "P",
                "+" if value >= 0 else "-",
                abs(value),
            )
            return pck

        thrs_register_id = lcn_defs.Var.to_thrs_register_id(var)
        thrs_id = lcn_defs.Var.to_thrs_id(var)
        if (thrs_register_id != -1) and (thrs_id != -1):
            if software_serial >= 0x170206:
                # New command for registers 1-4 (since 170206, LCN-PCHK 2.8)
                pck = "SS{:s}{:04d}{:s}R{:d}{:d}".format(
                    "R" if rel_var_ref == lcn_defs.RelVarRef.CURRENT else "E",
                    abs(value),
                    "A" if value >= 0 else "S",
                    thrs_register_id + 1,
                    thrs_id + 1,
                )
            elif thrs_register_id == 0:
                # Old command for register 1 (before 170206)
                pck = "SS{:s}{:04d}{:s}{:s}{:s}{:s}{:s}{:s}".format(
                    "R" if rel_var_ref == lcn_defs.RelVarRef.CURRENT else "E",
                    abs(value),
                    "A" if value >= 0 else "S",
                    "1" if thrs_id == 0 else "0",
                    "1" if thrs_id == 1 else "0",
                    "1" if thrs_id == 2 else "0",
                    "1" if thrs_id == 3 else "0",
                    "1" if thrs_id == 4 else "0",
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
                return "MWT{:03d}".format(var_id + 1)

            set_point_id = lcn_defs.Var.to_set_point_id(var)
            if set_point_id != -1:
                return "MWS{:03d}".format(set_point_id + 1)

            thrs_register_id = lcn_defs.Var.to_thrs_register_id(var)
            if thrs_register_id != -1:
                # Whole register
                return "SE{:03d}".format(thrs_register_id + 1)

            s0_id = lcn_defs.Var.to_s0_id(var)
            if s0_id != -1:
                return "MWC{:03d}".format(s0_id + 1)
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
        return "LA{:03d}{:s}".format(led_id + 1, state.value)

    @staticmethod
    def send_keys(cmds: List[lcn_defs.SendKeyCommand], keys: List[bool]) -> str:
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
        table_id: int, time: int, time_unit: lcn_defs.TimeUnit, keys: List[bool]
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
    def lock_keys(table_id: int, states: List[lcn_defs.KeyLockStateModifier]) -> str:
        """Generate a command to lock keys.

        :param     int           table_id:  Table id 0(A)..3(D)
        :param     list(bool)    states:    The 8 key-lock modifiers as list
        :return:   The PCK command (without address header) as text
        :rtype:    str
        """
        if (table_id < 0) or (table_id > 3) or (len(states) != 8):
            raise ValueError("Bad table_id or states.")
        try:
            ret = "TX{:s}".format(PckGenerator.TABLE_NAMES[table_id])
        except IndexError as exc:
            raise ValueError("Wrong table_id.") from exc

        for state in states:
            ret += state.value

        return ret

    @staticmethod
    def lock_keys_tab_a_temporary(
        time: int, time_unit: lcn_defs.TimeUnit, keys: List[bool]
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
            ret += "1" if key else "0"

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
        return "GTDT{:d}{:d}".format(row_id + 1, part_id + 1).encode("utf-8") + part

    @staticmethod
    def lock_regulator(reg_id: int, state: bool) -> str:
        """Generate a command to lock a regulator.

        :param    int    reg_id:    Regulator id 0..1
        :param    bool   state:     The lock state
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if (reg_id < 0) or (reg_id > 1):
            raise ValueError("Wrong reg_id.")
        return "RE{:s}X{:s}".format("A" if reg_id == 0 else "B", "S" if state else "A")

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
        ramp: Optional[int] = None,
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
        ramp: Optional[int] = None,
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
        ramp: Optional[int] = None,
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
        return "SZ{:s}0{:03d}{:s}".format(action, scene_id, "".join(relays_mask))

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
