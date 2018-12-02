'''
Copyright (c) 2006-2018 by the respective copyright holders.

All rights reserved. This program and the accompanying materials
are made available under the terms of the Eclipse Public License v1.0
which accompanies this distribution, and is available at
http://www.eclipse.org/legal/epl-v10.html

Contributors:
  Andre Lengwenus - port to Python and further improvements
  Tobias Juettner - initial LCN binding for openHAB (Java)
'''

import re

from pypck import lcn_defs


class PckParser():
    """Helpers to parse LCN-PCK commands.

    LCN-PCK is the command-syntax used by LCN-PCHK to send and receive LCN
    commands.
    """
    # Authentication at LCN-PCHK: Request user name.
    AUTH_USERNAME = 'Username:'

    # Authentication at LCN-PCHK: Request password.
    AUTH_PASSWORD = 'Password:'

    # Authentication at LCN-PCHK succeeded.
    AUTH_OK = 'OK'

    # LCN-PK/PKU is connected.
    LCNCONNSTATE_CONNECTED = '$io:#LCN:connected'

    # LCN-PK/PKU is disconnected.
    LCNCONNSTATE_DISCONNECTED = '$io:#LCN:disconnected'

    # Pattern to parse positive acknowledges.
    PATTERN_ACK_POS = re.compile(
        r'-M(?P<seg_id>\d{3})(?P<mod_id>\d{3})!')

    # Pattern to parse negative acknowledges.
    PATTERN_ACK_NEG = re.compile(
        r'-M(?P<seg_id>\d{3})(?P<mod_id>\d{3})(?P<code>\d+)')

    # Pattern to parse segment coupler responses.
    PATTERN_SK_RESPONSE = re.compile(
        r'=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.SK(?P<id>\d+)')

    # Pattern to parse serial number and firmware date responses.
    PATTERN_SN = re.compile(
        r'=M(?P<seg_id>\d{3})(?P<mod_id>\d{3}).SN(?P<sn>[0-9|A-F]{10})'
        r'(?P<manu>[0-9|A-F]{2})FW(?P<sw_age>[0-9|A-F]{6})HW(?P<hw_type>\d+)')

    # Pattern to parse output-port status responses in percent.
    PATTERN_STATUS_OUTPUT_PERCENT = re.compile(
        r':M(?P<seg_id>\d{3})(?P<mod_id>\d{3})A(?P<output_id>\d)'
        r'(?P<percent>\d+)')

    # Pattern to parse output-port status responses in native format (0..200).
    PATTERN_STATUS_OUTPUT_NATIVE = re.compile(
        r':M(?P<seg_id>\d{3})(?P<mod_id>\d{3})O(?P<output_id>\d)'
        r'(?P<value>\d+)')

    # Pattern to parse relays status responses.
    PATTERN_STATUS_RELAYS = re.compile(
        r':M(?P<seg_id>\d{3})(?P<mod_id>\d{3})Rx(?P<byte_value>\d+)')

    # Pattern to parse binary-sensors status responses.
    PATTERN_STATUS_BINSENSORS = re.compile(
        r':M(?P<seg_id>\d{3})(?P<mod_id>\d{3})Bx(?P<byte_value>\d+)')

    # Pattern to parse variable 1-12 status responses (since 170206).
    PATTERN_STATUS_VAR = re.compile(
        r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.A(?P<id>\d{3})(?P<value>\d+)')

    # Pattern to parse set-point variable status responses (since 170206).
    PATTERN_STATUS_SETVAR = re.compile(
        r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.S(?P<id>\d)(?P<value>\d+)')

    # Pattern to parse threshold status responses (since 170206).
    PATTERN_STATUS_THRS = re.compile(
        r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.T(?P<register_id>\d)'
        r'(?P<thrs_id>\d)(?P<value>\d+)')

    # Pattern to parse S0-input status responses (LCN-BU4L).
    PATTERN_STATUS_S0INPUT = re.compile(
        r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.C(?P<id>\d)(?P<value>\d+)')

    # Pattern to parse generic variable status responses (concrete type
    # unknown, before 170206).
    PATTERN_VAR_GENERIC = re.compile(
        r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.(?P<value>\d+)')

    # Pattern to parse threshold register 1 status responses (5 values,
    # before 170206). */
    PATTERN_THRS5 = re.compile(
        r'=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.S1(?P<value1>\d{5})'
        r'(?P<value2>\d{5})(?P<value3>\d{5})(?P<value4>\d{5})'
        r'(?P<value5>\d{5})(?P<hyst>\d{5})')

    # Pattern to parse status of LEDs and logic-operations responses.
    PATTERN_STATUS_LEDSANDLOGICOPS = re.compile(
        r'=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.TL(?P<led_states>[AEBF]{12})'
        r'(?P<logic_op_states>[NTV]{4})')

    # Pattern to parse key-locks status responses.
    PATTERN_STATUS_KEYLOCKS = re.compile(
        r'=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.TX(?P<table0>\d{3})'
        r'(?P<table1>\d{3})(?P<table2>\d{3})((?P<table3>\d{3}))?')

    @staticmethod
    def get_boolean_value(input_byte):
        """Get boolean representation for the given byte.

        :param    int    input_byte:    Input byte as int8.

        :return:    List with 8 boolean values.
        :rtype:     list
        """
        if (input_byte < 0) or (input_byte > 255):
            raise ValueError('Invalid input_byte.')

        result = []
        for i in range(8):
            result.append((input_byte & (1 << i)) != 0)
        return result


class PckGenerator():
    """Helpers to generate LCN-PCK commands.

    LCN-PCK is the command-syntax used by LCN-PCHK to send and receive LCN
    commands.
    """
    # Terminates a PCK command
    TERMINATION = '\n'

    TABLE_NAMES = ['A', 'B', 'C', 'D']

    @staticmethod
    def ping(counter):
        """Generates a keep-alive.
        LCN-PCHK will close the connection if it does not receive any commands
        from an open :class:`~pypck.connection.PchkConnectionManager` for a
        specific period (10 minutes by default).

        :param    int    counter:    The current ping's id (optional, but
                                     'best practice'). Should start with 1
        :return:    The PCK command as text
        :rtype:    str
        """
        return '^ping{:d}'.format(counter)

    @staticmethod
    def set_operation_mode(dim_mode, status_mode):
        """Generates a PCK command that will set the LCN-PCHK connection's
        operation mode.
        This influences how output-port commands and status are interpreted
        and must be in sync with the LCN bus.

        :param    OuputPortDimMode        dimMode:        The dimming mode
                                                          (50/200 steps)
        :param    OutputPortStatusMode    statusMode:     The status mode
                                                          (percent/native)
        :return:    The PCK command as text
        :rtype:    str
        """
        return '!OM{:s}{:s}'.format(
            '1' if (dim_mode == lcn_defs.OutputPortDimMode.STEPS200)
            else '0',
            'P' if (status_mode == lcn_defs.OutputPortStatusMode.PERCENT)
            else 'N')

    @staticmethod
    def generate_address_header(addr, local_seg_id, wants_ack):
        """Generates a PCK command address header.

        :param    addr:   The module's/group's address
        :type     addr:   :class:`~LcnAddrMod` or :class:`~LcnAddrGrp`
        :param    int     local_seg_id:    The local segment id
        :param    bool    wants_ack:      Is an acknowledge requested.

        :return:    The PCK address header string.
        :rtype:     str
        """
        return '>{:s}{:03d}{:03d}{:s}'.format('G' if addr.is_group() else 'M',
                                              addr.get_physical_seg_id(
                                                  local_seg_id),
                                              addr.get_id(),
                                              '!' if wants_ack else '.')

    @staticmethod
    def segment_coupler_scan():
        """Generates a scan-command for LCN segment-couplers.
        Used to detect the local segment (where the physical bus connection is
        located).

        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        return 'SK'

    @staticmethod
    def request_sn():
        """Generates a firmware/serial-number request.

        :return: The PCK command (without address header) as text
        :rtype:    str
        """
        return 'SN'

    @staticmethod
    def request_output_status(output_id):
        """Generates an output-port status request.

        :param    int    output_id:    Output id 0..3
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError('Invalid output_id.')
        return 'SMA{:d}'.format(output_id + 1)

    @staticmethod
    def dim_ouput(output_id, percent, ramp):
        """Generates a dim command for a single output-port.

        :param    int    output_it:    Output id 0..3
        :param    int    percent:      Brightness in percent 0..100
        :param    int    ramp:         Ramp value
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError('Invalid output_id.')
        percent_round = int(round(percent * 2))
        ramp = int(ramp)
        if (percent_round % 2) == 0:
            # Use the percent command (supported by all LCN-PCHK versions)
            pck = 'A{:d}DI{:03d}{:03d}'.format(output_id + 1,
                                               percent_round // 2, ramp)
        else:
            # We have a ".5" value. Use the native command (supported since
            # LCN-PCHK 2.3)
            pck = 'O{:d}DI{:03d}{:03d}'.format(output_id + 1,
                                               percent_round, ramp)
        return pck

    @staticmethod
    def dim_all_outputs(percent, ramp, is1805=False):
        """Generates a dim command for all output-ports.

        :param    int    percent:    Brightness in percent 0..100
        :param    int    ramp:       Ramp value
        :param    bool   is1805:     True if the target module's firmware is
                                     180501 or newer, otherwise False
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        percent_round = round(percent * 2)
        if is1805:
            # Supported since LCN-PCHK 2.61
            pck = 'OY{0:03d}{0:03d}{0:03d}{0:03d}{1:03d}'.format(
                percent_round, ramp)
        elif percent_round == 0:  # All off
            pck = 'AA{:03d}'.format(ramp)
        elif percent_round == 200:  # All on
            pck = 'AE{:03d}'.format(ramp)
        else:
            # This is our worst-case: No high-res, no ramp
            pck = 'AH{:03d}'.format(percent_round / 2)
        return pck

    @staticmethod
    def rel_output(output_id, percent):
        """Generates a command to change the value of an output-port.

        :param    int    output_id:    Output id 0..3
        :param    int    percent:      Relative percentage -100..100
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError('Invalid output_id.')

        percent_round = round(percent * 2)
        if percent_round % 2 == 0:
            # Use the percent command (supported by all LCN-PCHK versions)
            pck = 'A{:d}{:s}{:03d}'.format(output_id + 1, 'AD'
                                           if percent >= 0
                                           else 'SB',
                                           abs(percent_round // 2))
        else:
            # We have a ".5" value. Use the native command (supported since
            # LCN-PCHK 2.3)
            pck = 'O{:d}{:s}{:03d}'.format(output_id + 1, 'AD'
                                           if percent >= 0
                                           else 'SB',
                                           abs(percent_round))
            return pck

    @staticmethod
    def toggle_output(output_id, ramp):
        """Generates a command that toggles a single output-port (on->off,
        off->on).

        :param    int    output_id:    Output id 0..3
        :param    int    ramp:         Ramp value
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError('Invalid output_id.')
        return 'A{:d}TA{:03d}'.format(output_id + 1, ramp)

    @staticmethod
    def toggle_all_outputs(ramp):
        """Generates a command that toggles all output-ports (on->off,
        off->on).

        :param    int    ramp:    Ramp value
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        return 'AU{:03d}'.format(ramp)

    @staticmethod
    def request_relays_status():
        """Generates a relays-status request.

        :return: The PCK command (without address header) as text
        :rtype:    str
        """
        return 'SMR'

    @staticmethod
    def control_relays(states):
        """Generates a command to control relays.

        :param     RelayStateModifier    states:    The 8 modifiers for the
                                                    relay states as a list
        :return:   The PCK command (without address header) as text
        :rtype:    str
        """
        if len(states) != 8:
            raise ValueError('Invalid states length.')
        ret = 'R8'
        for state in states:
            ret += state.value

        return ret

    @staticmethod
    def control_motors(states):
        """Generates a command to control motors via relays.

        :param    MotorStateModifier    states:    The 4 modifiers for the
                                                   motor states as a list
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if len(states) != 4:
            raise ValueError('Invalid states length.')
        ret = 'R8'
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
    def request_bin_sensors_status():
        """Generates a binary-sensors status request.

        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        return 'SMB'

    @staticmethod
    def var_abs(var, value):
        """Generates a command that sets a variable absolute.

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
            byte1 |= (value >> 8) & 0x0f  # xxxx1111
            byte2 = value & 0xff
            return 'X2{:03d}{:03d}{:03d}'.format(30, byte1, byte2)

        # Setting variables and thresholds absolute not implemented in LCN
        # firmware yet
        raise ValueError('Wrong variable type.')

    @staticmethod
    def update_status_var(var, value):
        """Generates a command that send variable status updates.
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
            byte1 = (value >> 8) & 0xff
            byte2 = value & 0xff
            return 'X2{:03d}{:03d}{:03d}'.format(x2cmd, byte1, byte2)

        # Setting variables and thresholds absolute not implemented in LCN
        # firmware yet
        raise ValueError('Wrong variable type.')

    @staticmethod
    def var_reset(var, is2013=True):
        """Generates a command that resets a variable to 0.

        :param    Var    var:    The target variable to set 0
        :param    bool   is2013: True if the target module's firmware version
                                 is 170101 or newer, otherwise False
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        var_id = lcn_defs.Var.to_var_id(var)
        if var_id != -1:
            if is2013:
                pck = 'Z-{:03d}{:04d}'.format(var_id + 1, 4090)
            else:
                if var_id == 0:
                    pck = 'ZS30000'
                else:
                    raise ValueError('Wrong variable type.')
            return pck

        set_point_id = lcn_defs.Var.to_set_point_id(var)
        if set_point_id != -1:
            # Set absolute = 0 (not in PCK yet)
            byte1 = set_point_id << 6  # 01000000
            byte1 |= 0x20  # xx10xxxx 9set absolute)
            byte2 = 0
            return 'X2{:03d}{:03d}{:03d}'.format(30, byte1, byte2)

        # Reset for threshold not implemented in LCN firmware yet
        raise ValueError('Wrong variable type.')

    @staticmethod
    def var_rel(var, rel_var_ref, value, is2013=True):
        """Generates a command to change the value of a variable.

        :param    Var          var:    The target variable to change
        :param    RelVarRef    rel_var_ref:   The reference-point
        :param    int          value:  The native LCN value to add/subtract
                                       (can be negative)
        :param    bool         is2013: True if the target module's firmware
                                       version is 170101 or newer, otherwise
                                       False
        :return:    The PCK command (without address header) as text
        :rtype:    str
        """
        var_id = lcn_defs.Var.to_var_id(var)
        if var_id != -1:
            if var_id == 0:
                # Old command for variable 1 / T-var (compatible with all
                # modules)
                pck = 'Z{:s}{:d}'.format('A' if value >= 0 else 'S',
                                         abs(value))
            else:
                # New command for variable 1-12 (compatible with all modules,
                # since LCN-PCHK 2.8)
                pck = 'Z{:s}{:03d}{:d}'.format('+' if value >= 0 else '-',
                                               var_id + 1, abs(value))
            return pck

        set_point_id = lcn_defs.Var.to_set_point_id(var)
        if set_point_id != -1:
            pck = 'RE{:s}S{:s}{:s}{:d}'.format(
                'A' if set_point_id == 0 else 'B',
                'A' if rel_var_ref == lcn_defs.RelVarRef.CURRENT else 'P',
                '+' if value >= 0 else '-',
                abs(value))
            return pck

        thrs_register_id = lcn_defs.Var.to_thrs_register_id(var)
        thrs_id = lcn_defs.Var.to_thrs_id(var)
        if (thrs_register_id != -1) and (thrs_id != -1):
            if is2013:
                # New command for registers 1-4 (since 170206, LCN-PCHK 2.8)
                pck = 'SS{:s}{:04d}{:s}R{:d}{:d}'.format(
                    'R' if rel_var_ref == lcn_defs.RelVarRef.CURRENT else 'E',
                    abs(value),
                    'A' if value >= 0 else 'S',
                    thrs_register_id + 1,
                    thrs_id + 1)
            elif thrs_register_id == 0:
                # Old command for register 1 (before 170206)
                pck = 'SS{:s}{:4d}{:s}{:s}{:s}{:s}{:s}{:s}'.format(
                    'R' if rel_var_ref == lcn_defs.RelVarRef.CURRENT else 'E',
                    abs(value),
                    'A' if value >= 0 else 'S',
                    '1' if thrs_id == 0 else '0',
                    '1' if thrs_id == 1 else '0',
                    '1' if thrs_id == 2 else '0',
                    '1' if thrs_id == 3 else '0',
                    '1' if thrs_id == 4 else '0')
            return pck

        raise ValueError('Wrong variable type.')

    @staticmethod
    def request_var_status(var, sw_age=0x170206):
        """Generates a variable value request.

        :param    Var    var:    The variable to request
        :param    int    swAge:  The target module's firmware version
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if sw_age >= 0x170206:
            var_id = lcn_defs.Var.to_var_id(var)
            if var_id != -1:
                return 'MWT{:03d}'.format(var_id + 1)

            set_point_id = lcn_defs.Var.to_set_point_id(var)
            if set_point_id != -1:
                return 'MWS{:03d}'.format(set_point_id + 1)

            thrs_register_id = lcn_defs.Var.to_thrs_register_id(var)
            if thrs_register_id != -1:
                # Whole register
                return 'SE{:03d}'.format(thrs_register_id + 1)

            s0_id = lcn_defs.Var.to_s0_id(var)
            if s0_id != -1:
                return 'MWC{:03d}'.format(s0_id + 1)
        else:
            if var == lcn_defs.Var.VAR1ORTVAR:
                pck = 'MWV'
            elif var == lcn_defs.Var.VAR2ORR1VAR:
                pck = 'MWTA'
            elif var == lcn_defs.Var.VAR3ORR2VAR:
                pck = 'MWTB'
            elif var == lcn_defs.Var.R1VARSETPOINT:
                pck = 'MWSA'
            elif var == lcn_defs.Var.R2VARSETPOINT:
                pck = 'MWSB'
            elif var in [lcn_defs.Var.THRS1, lcn_defs.Var.THRS2,
                         lcn_defs.Var.THRS3, lcn_defs.Var.THRS4,
                         lcn_defs.Var.THRS5]:
                pck = 'SL1'  # Whole register
            return pck

        raise ValueError('Wrong variable type.')

    @staticmethod
    def request_leds_and_logic_ops():
        """Generates a request for LED and logic-operations states.

        :return: The PCK command (without address header) as text
        :rtype:  str
        """
        return 'SMT'

    @staticmethod
    def control_led(led_id, state):
        """Generates a command to the set the state of a single LED.

        :param    int          led_id:   Led id 0..11
        :param    LedStatus    state:    The state to set
        :return: The PCK command (without address header) as text
        :rtype:  str
        """
        if (led_id < 0) or (led_id > 11):
            raise ValueError('Bad led_id.')
        return 'LA{:03d}{:2}'.format(led_id + 1, state.value)

    @staticmethod
    def send_keys(cmds, keys):
        """Generates a command to send LCN keys.

        :param    SendKeyCOmmand    cmds:    The 4 concrete commands to send
                                             for the tables (A-D) as list
        :param    list(bool)        keys:    The tables' 8 key-states (True
                                             means "send") as list

        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if (len(cmds) != 4) or (len(keys) != 8):
            raise ValueError('Wrong cmds length or wrong keys length.')
        ret = 'TS'
        for i, cmd in enumerate(cmds):
            if (cmd == lcn_defs.SendKeyCommand.DONTSEND) and (i == 3):
                # By skipping table D (if it is not used), we use the old
                # command
                # for table A-C which is compatible with older LCN modules
                break
            else:
                ret += cmd.value

        for key in keys:
            ret += '1' if key else '0'

        return ret

    @staticmethod
    def send_keys_hit_deferred(table_id, time, time_unit, keys):
        """Generates a command to send LCN keys deferred / delayed.

        :param     int         table_id:    Table id 0(A)..3(D)
        :param     int         time:        The delay time
        :param     TimeUnit    time_unit:   The time unit
        :param     list(bool)  keys:        The table's 8 key-states (True
                                            means "send") as list
        :return:   The PCK command (without address header) as text
        :rtype:    str
        """
        if (table_id < 0) or (table_id > 3) or (len(keys) != 8):
            raise ValueError('Bad table_id or keys.')
        ret = 'TV'
        try:
            ret += PckGenerator.TABLE_NAMES[table_id]
        except IndexError:
            raise ValueError('Wrong table_id.')

        ret += '{:03d}'.format(time)
        if time_unit == lcn_defs.TimeUnit.SECONDS:
            if (time < 1) or (time > 60):
                raise ValueError('Wrong time.')
            ret += 'S'
        elif time_unit == lcn_defs.TimeUnit.MINUTES:
            if (time < 1) or (time > 90):
                raise ValueError('Wrong time.')
            ret += 'M'
        elif time_unit == lcn_defs.TimeUnit.HOURS:
            if (time < 1) or (time > 50):
                raise ValueError('Wrong time.')
            ret += 'H'
        elif time_unit == lcn_defs.TimeUnit.DAYS:
            if (time < 1) or (time > 45):
                raise ValueError('Wrong time.')
            ret += 'D'
        else:
            raise ValueError('Wrong time_unit.')

        for key in keys:
            ret += '1' if key else '0'

        return ret

    @staticmethod
    def request_key_lock_status():
        """Generates a request for key-lock states.
        Always requests table A-D. Supported since LCN-PCHK 2.8.

        :return:    The PCK command (without address header) as text
        :rtype:     str
        """
        return 'STX'

    @staticmethod
    def lock_keys(table_id, states):
        """Generates a command to lock keys.

        :param     int           table_id:  Table id 0(A)..3(D)
        :param     list(bool)    states:    The 8 key-lock modifiers as list
        :return:   The PCK command (without address header) as text
        :rtype:    str
        """
        if (table_id < 0) or (table_id > 3) or (len(states) != 8):
            raise ValueError('Bad table_id or states.')
        try:
            ret = 'TX{:s}'.format(PckGenerator.TABLE_NAMES[table_id])
        except IndexError:
            raise ValueError('Wrong table_id.')

        for state in states:
            ret += state.value

        return ret

    @staticmethod
    def lock_keys_tab_a_temporary(time, time_unit, keys):
        """Generates a command to lock keys for table A temporary.
        There is no hardware-support for locking tables B-D.

        :param     int         time:         The lock time
        :param     TimeUnit    time_unit:    The time unit
        :param     list(bool)  keys:         The 8 key-lock states (True means
                                             lock) as list
        :return:   The PCK command (without address header) as text
        :rtype:    str
        """
        if len(keys) != 8:
            raise ValueError('Wrong keys lenght.')
        ret = 'TXZA{:03d}'.format(time)

        if time_unit == lcn_defs.TimeUnit.SECONDS:
            if (time < 1) or (time > 60):
                raise ValueError('Wrong time.')
            ret += 'S'
        elif time_unit == lcn_defs.TimeUnit.MINUTES:
            if (time < 1) or (time > 90):
                raise ValueError('Wrong time.')
            ret += 'M'
        elif time_unit == lcn_defs.TimeUnit.HOURS:
            if (time < 1) or (time > 50):
                raise ValueError('Wrong time.')
            ret += 'H'
        elif time_unit == lcn_defs.TimeUnit.DAYS:
            if (time < 1) or (time > 45):
                raise ValueError('Wrong time.')
            ret += 'D'
        else:
            raise ValueError('Wrong time_unit.')

        for key in keys:
            ret += '1' if key else '0'

        return ret

    @staticmethod
    def dyn_text_part(row_id, part_id, part):
        """Generates the command header / start for sending dynamic texts.
        Used by LCN-GTxD periphery (supports 4 text rows).
        To complete the command, the text to send must be appended (UTF-8
        encoding).
        Texts are split up into up to 5 parts with 12 "UTF-8 bytes" each.

        :param    int    row_id:    Row id 0..3
        :param    int    part_id:   Part id 0..4
        :param    str    part:      Text part (up to 12 bytes), encoded as
                                    lcn_defs.LCN_ENCODING
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if (row_id < 0) or (row_id > 3) or (part_id < 0) or \
           (part_id > 4) or (len(part) > 12):
            raise ValueError('Wrong row_id, part_id or part length.')
        return 'GTDT{:d}{:d}{:s}'.format(row_id + 1, part_id + 1,
                                         part.decode(lcn_defs.LCN_ENCODING))

    @staticmethod
    def lock_regulator(reg_id, state):
        """Generates a command to lock a regulator.

        :param    int    reg_id:    Regulator id 0..1
        :param    bool   state:     The lock state
        :return:  The PCK command (without address header) as text
        :rtype:   str
        """
        if (reg_id < 0) or (reg_id > 1):
            raise ValueError('Wrong reg_id.')
        return 'RE{:s}X{:s}'.format('A' if reg_id == 0 else 'B',
                                    'S' if state else 'A')
