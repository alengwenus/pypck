import re

from pypck import lcn_defs


class PckParser(object):
    """
    Helpers to parse LCN-PCK commands.
    
    LCN-PCK is the command-syntax used by LCN-PCHK to send and receive LCN commands.
    """
    # Authentication at LCN-PCHK: Request user name.
    AUTH_USERNAME = 'Username:'
    
    # Authentication at LCN-PCHK: Request password.
    AUTH_PASSWORD = 'Password:'

    # Authentication at LCN-PCHK succeeded.
    AUTH_OK = 'OK';

    # LCN-PK/PKU is connected.
    LCNCONNSTATE_CONNECTED = '$io:#LCN:connected'

    # LCN-PK/PKU is disconnected.
    LCNCONNSTATE_DISCONNECTED = '$io:#LCN:disconnected'
    
    # Pattern to parse positive acknowledges.
    PATTERN_ACK_POS = re.compile(r'-M(?P<seg_id>\d{3})(?P<mod_id>\d{3})!')

    # Pattern to parse negative acknowledges.
    PATTERN_ACK_NEG = re.compile(r'-M(?P<seg_id>\d{3})(?P<mod_id>\d{3})(?P<code>\d+)')
    
    # Pattern to parse segment coupler responses.
    PATTERN_SK_RESPONSE = re.compile(r'=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.SK(?P<id>\d+)')

    # Pattern to parse serial number and firmware date responses.
    PATTERN_SN = re.compile(r'=M(?P<seg_id>\d{3})(?P<mod_id>\d{3}).SN(?P<sn>[0-9|A-F]{10})(?P<manu>[0-9|A-F]{2})FW(?P<sw_age>[0-9|A-F]{6})HW(?P<hw_type>\d+)')

    # Pattern to parse output-port status responses in percent.
    PATTERN_STATUS_OUTPUT_PERCENT = re.compile(r':M(?P<seg_id>\d{3})(?P<mod_id>\d{3})A(?P<output_id>\d)(?P<percent>\d+)')

    # Pattern to parse output-port status responses in native format (0..200).
    PATTERN_STATUS_OUTPUT_NATIVE = re.compile(r':M(?P<seg_id>\d{3})(?P<mod_id>\d{3})O(?P<output_id>\d)(?P<value>\d+)')

    # Pattern to parse relays status responses.
    PATTERN_STATUS_RELAYS = re.compile(r':M(?P<seg_id>\d{3})(?P<mod_id>\d{3})Rx(?P<byte_value>\d+)')

    # Pattern to parse binary-sensors status responses.
    PATTERN_STATUS_BINSENSORS = re.compile(r':M(?P<seg_id>\d{3})(?P<mod_id>\d{3})Bx(?P<byte_value>\d+)')       
    
    # Pattern to parse variable 1-12 status responses (since 170206).
    PATTERN_STATUS_VAR = re.compile(r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.A(?P<id>\d{3})(?P<value>\d+)')

    # Pattern to parse set-point variable status responses (since 170206).
    PATTERN_STATUS_SETVAR = re.compile(r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.S(?P<id>\d)(?P<value>\d+)')

    # Pattern to parse threshold status responses (since 170206).
    PATTERN_STATUS_THRS = re.compile(r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.T(?P<register_id>\d)(?P<thrs_id>\d)(?P<value>\d+)')

    # Pattern to parse S0-input status responses (LCN-BU4L).
    PATTERN_STATUS_S0INPUT = re.compile(r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.C(?P<id>\d)(?P<value>\d+)')

    # Pattern to parse generic variable status responses (concrete type unknown, before 170206).
    PATTERN_VAR_GENERIC = re.compile(r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.(?P<value>\d+)')

    # Pattern to parse threshold register 1 status responses (5 values, before 170206). */
    PATTERN_THRS5 = re.compile(r'=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.S1(?P<value1>\d{5})(?P<value2>\d{5})(?P<value3>\d{5})(?P<value4>\d{5})(?P<value5>\d{5})(?P<hyst>\d{5})')

    # Pattern to parse status of LEDs and logic-operations responses.
    PATTERN_STATUS_LEDSANDLOGICOPS = re.compile(r'=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.TL(?P<led_states>[AEBF]{12})(?P<logic_op_states>[NTV]{4})')

    # Pattern to parse key-locks status responses.
    PATTERN_STATUS_KEYLOCKS = re.compile(r'=M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.TX(?P<table0>\d{3})(?P<table1>\d{3})(?P<table2>\d{3})((?P<table3>\d{3}))?')
   
    @staticmethod
    def get_boolean_value(input_byte):
        if (input_byte < 0) or (input_byte > 255):
            raise ValueError('Invalid input_byte.')
        
        result = []
        for i in range(8):
            result.append((input_byte & (1 << i)) != 0)
        return result


class PckGenerator(object):
    """
    Helpers to generate LCN-PCK commands.
    
    LCN-PCK is the command-syntax used by LCN-PCHK to send and receive LCN commands.
    """
    # Terminates a PCK command
    TERMINATION = '\n'

    TABLE_NAMES = ['A', 'B', 'C', 'D']
    
    @staticmethod
    def ping(counter):
        """
        Generates a keep-alive.
        LCN-PCHK will close the connection if it does not receive any commands from
        an open {@link Connection} for a specific period (10 minutes by default).
        
        @param counter the current ping's id (optional, but "best practice"). Should start with 1
        @return the PCK command as text
        """
        return '^ping{:d}'.format(counter)
    
    @staticmethod
    def set_operation_mode(dim_mode, status_mode):
        """
        Generates a PCK command that will set the LCN-PCHK connection's operation mode.
        This influences how output-port commands and status are interpreted and must be
        in sync with the LCN bus.
        
        @param dimMode see {@link LcnDefs.OutputPortDimMode}
        @param statusMode see {@link LcnDefs.OutputPortStatusMode}
        @return the PCK command as text
        """
        return '!OM{:s}{:s}'.format('1' if (dim_mode == lcn_defs.OutputPortDimMode.STEPS200) else '0',
                                    'P' if (status_mode == lcn_defs.OutputPortStatusMode.PERCENT) else 'N') 

    @staticmethod
    def generate_address_header(addr, local_seg_id, wants_ack):
        return '>{:s}{:03d}{:03d}{:s}'.format('G' if addr.is_group() else 'M',
                                              addr.get_physical_seg_id(local_seg_id),
                                              addr.get_id(),
                                              '!' if wants_ack else '.')
        
    @staticmethod
    def segment_coupler_scan():
        """
        Generates a scan-command for LCN segment-couplers.
        Used to detect the local segment (where the physical bus connection is located).

        @return the PCK command (without address header) as text
        """
        return 'SK'
    
    @staticmethod
    def request_sn():
        """
        Generates a firmware/serial-number request.
        
        @return the PCK command (without address header) as text
        """
        return 'SN'
    
    @staticmethod
    def request_output_status(output_id):
        """
        Generates an output-port status request.

        @param outputId 0..3
        @return the PCK command (without address header) as text
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError('Invalid output_id.')
        return 'SMA{:d}'.format(output_id + 1)

    @staticmethod
    def dim_ouput(output_id, percent, ramp):
        """
        Generates a dim command for a single output-port.

        @param outputId 0..3
        @param percent 0..100
        @param ramp use {@link LcnDefs#timeToRampValue(int)}
        @return the PCK command (without address header) as text
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError('Invalid output_id.')
        n = int(round(percent*2))
        ramp = int(ramp)
        if (n % 2) == 0:    # Use the percent command (supported by all LCN-PCHK versions)
            return 'A{:d}DI{:03d}{:03d}'.format(output_id + 1, n // 2, ramp)
        else:               # We have a ".5" value. Use the native command (supported since LCN-PCHK 2.3)
            return 'O{:d}DI{:03d}{:03d}'.format(output_id + 1, n, ramp)
    
    @staticmethod
    def dim_all_outputs(percent, ramp, is1805=False):
        """
        Generates a dim command for all output-ports.

        @param percent 0..100
        @param ramp use {@link LcnDefs#timeToRampValue(int)} (might be ignored in some cases)
        @param is1805 true if the target module's firmware is 180501 or newer
        @return the PCK command (without address header) as text        
        """
        n = round(percent * 2)
        if is1805:
            return 'OY{:03d}{:03d}{:03d}{:03d}{:03d}'.format(n, n, n, n, ramp)  # Supported since LCN-PCHK 2.61
        
        if n == 0:  # All off
            return 'AA{:03d}'.format(ramp)
        elif (n == 200):    # All on
            return 'AE{:03d}'.format(ramp)
        
        # This is our worst-case: No high-res, no ramp
        return 'AH{:03d}'.format(n / 2) 
    
    @staticmethod
    def rel_output(output_id, percent):
        """
        Generates a command to change the value of an output-port.

        @param outputId 0..3
        @param percent -100..100
        @return the PCK command (without address header) as text
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError('Invalid output_id.')
        
        n = round(percent * 2)
        if n % 2 == 0:  # Use the percent command (supported by all LCN-PCHK versions)
            return 'A{:d}{:s}{:03d}'.format(output_id + 1, 'AD' if percent >= 0 else 'SB', abs(n // 2))
        else:   # We have a ".5" value. Use the native command (supported since LCN-PCHK 2.3)
            return 'O{:d}{:s}{:03d}'.format(output_id + 1, 'AD' if percent >= 0 else 'SB', abs(n))
    
    @staticmethod
    def toggle_output(output_id, ramp):
        """
        Generates a command that toggles a single output-port (on->off, off->on).

        @param outputId 0..3
        @param ramp see {@link LcnDefs#timeToRampValue(int)}
        @return the PCK command (without address header) as text        
        """
        if (output_id < 0) or (output_id > 3):
            raise ValueError('Invalid output_id.')
        return 'A{:d}TA{:03d}'.format(output_id + 1, ramp)
    
    @staticmethod
    def toggle_all_outputs(ramp):
        """
        Generates a command that toggles all output-ports (on->off, off->on).

        @param ramp see {@link LcnDefs#timeToRampValue(int)}
        @return the PCK command (without address header) as text        
        """
        return 'AU{:03d}'.format(ramp)
    
    @staticmethod   
    def request_relays_status():
        """
        Generates a relays-status request.
         
        @return the PCK command (without address header) as text
        """
        return 'SMR'
    
    @staticmethod
    def control_relays(states):
        """
        Generates a command to control relays.

        @param states the 8 modifiers for the relay states as a list
        @return the PCK command (without address header) as text
        """
        if len(states) != 8:
            raise ValueError('Invalid states length.')
        ret = 'R8'
        for state in states:
            ret += state.value
        
        return ret

    @staticmethod
    def control_motors(states):
        """
        Generates a command to control motors via relays.
        
        @param states the 4 modifiers for the motor states as a list
        @return the PCK command (without address header) as text
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
        """
        Generates a binary-sensors status request.
         
        @return the PCK command (without address header) as text
        """
        return 'SMB'
    
    @staticmethod
    def var_abs(var, value):
        """
        Generates a command that sets a variable absolute.

        @param var the target variable to set
        @param value the absolute value to set
        @return the PCK command (without address header) as text        
        """
        id = lcn_defs.Var.to_set_point_id(var)
        if id != -1:
            # Set absolute (not in PCK yet)
            b1 = id << 6    # 01000000
            b1 |= 0x20      # xx10xxxx (set absolute)
            value -= 1000   # Offset
            b1 |= (value >> 8) & 0x0f   # xxxx1111
            b2 = value & 0xff
            return 'X2{:03d}{:03d}{:03d}'.format(30, b1, b2)

        # Setting variables and thresholds absolute not implemented in LCN firmware yet
        raise ValueError('Wrong variable type.')
    
    @staticmethod
    def update_status_var(var, value):
        """
        Generates a command that send variable status updates.
        PCHK provides this variables by itself on selected segments
        is only possible with group 4

        @param var the target variable to set
        @param value the absolute value to set
        @return the PCK command (without address header) as text
        """
        id = lcn_defs.Var.to_var_id(var)
        if id != -1:
            # define variable to set, offset 0x01000000
            x2cmd = id | 0x40
            b1 = (value >> 8) & 0xff
            b2 = value & 0xff
            return 'X2{:03d}{:03d}{:03d}'.format(x2cmd, b1, b2)

        # Setting variables and thresholds absolute not implemented in LCN firmware yet
        raise ValueError('Wrong variable type.')

    @staticmethod
    def var_reset(var, is2013 = True):
        """
        Generates a command that resets a variable to 0.

        @param var the target variable to set 0
        @param is2013 the target module's firmware version is 170101 or newer
        @return the PCK command (without address header) as text        
        """
        id = lcn_defs.Var.to_var_id(var)
        if id != -1:
            if is2013:
                return 'Z-{:03d}{:04d}'.format(id + 1, 4090)
            else:
                if id == 0:
                    return 'ZS30000'
                else:
                    raise ValueError('Wrong variable type.')
        
        id = lcn_defs.Var.to_set_point_id(var)
        if id != -1:
            # Set absolute = 0 (not in PCK yet)
            b1 = id << 6    # 01000000
            b1 |= 0x20      # xx10xxxx 9set absolute)
            b2 = 0
            return 'X2{:03d}{:03d}{:03d}'.format(30, b1, b2)

        # Reset for threshold not implemented in LCN firmware yet
        raise ValueError('Wrong variable type.')
            
    @staticmethod
    def var_rel(var, type, value, is2013 = True):
        """
        Generates a command to change the value of a variable.

        @param var the target variable to change
        @param type the reference-point
        @param value the native LCN value to add/subtract (can be negative)
        @param is2013 the target module's firmware version is 170101 or newer
        @return the PCK command (without address header) as text        
        """
        id = lcn_defs.Var.to_var_id(var)
        if id != -1:
            if id == 0: # Old command for variable 1 / T-var (compatible with all modules)
                return 'Z{:s}{:d}'.format('A' if value >= 0 else 'S', abs(value))
            else:   # New command for variable 1-12 (compatible with all modules, since LCN-PCHK 2.8)
                return 'Z{:s}{:03d}{:d}'.format('+' if value >= 0 else '-', id + 1, abs(value))
                
        id = lcn_defs.Var.to_set_point_id(var)
        if id != -1:
            return 'RE{:s}S{:s}{:s}{:d}'.format('A' if id == 0 else 'B',
                                                'A' if type == lcn_defs.RelVarRef.CURRENT else 'P',
                                                '+' if value >= 0 else '-',
                                                abs(value))
        
        register_id = lcn_defs.Var.to_thrs_register_id(var)
        id = lcn_defs.Var.to_thrs_id(var)
        if (register_id != -1) and (id != -1):
            if is2013:      # New command for registers 1-4 (since 170206, LCN-PCHK 2.8)
                return 'SS{:s}{:04d}{:s}R{:d}{:d}'.format('R' if type == lcn_defs.RelVarRef.CURRENT else 'E',
                                                          abs(value),
                                                          'A' if value >= 0 else 'S',
                                                          register_id + 1,
                                                          id + 1)
            elif register_id == 0:      # Old command for register 1 (before 170206)
                return 'SS{:s}{:4d}{:s}{:s}{:s}{:s}{:s}{:s}'.format('R' if type == lcn_defs.RelVarRef.CURRENT else 'E',
                                                                    abs(value),
                                                                    'A' if value >= 0 else 'S',
                                                                    '1' if id == 0 else '0',
                                                                    '1' if id == 1 else '0',
                                                                    '1' if id == 2 else '0',
                                                                    '1' if id == 3 else '0',
                                                                    '1' if id == 4 else '0')
        
        raise ValueError('Wrong variable type.')
    
    @staticmethod
    def request_var_status(var, sw_age = 0x170206):
        """
        Generates a variable value request.
    
        @param var the variable to request
        @param swAge the target module's firmware version
        @return the PCK command (without address header) as text
        """        
        if sw_age >= 0x170206:
            id = lcn_defs.Var.to_var_id(var)
            if id != -1:
                return 'MWT{:03d}'.format(id + 1)
            
            id = lcn_defs.Var.to_set_point_id(var)
            if id != -1:
                return 'MWS{:03d}'.format(id + 1)
            
            id = lcn_defs.Var.to_thrs_register_id(var)
            if id != -1:
                return 'SE{:03d}'.format(id + 1)    # Whole register
            
            id = lcn_defs.Var.to_s0_id(var)
            if id != -1:
                return 'MWC{:03d}'.format(id + 1)
        else:
            if var == lcn_defs.Var.VAR1ORTVAR:
                return 'MWV'
            elif var == lcn_defs.Var.VAR2ORR1VAR:
                return 'MWTA'
            elif var == lcn_defs.Var.VAR3ORR2VAR:
                return 'MWTB'
            elif var == lcn_defs.Var.R1VARSETPOINT:
                return 'MWSA'
            elif var == lcn_defs.Var.R2VARSETPOINT:
                return 'MWSB'
            elif var in [lcn_defs.Var.THRS1, lcn_defs.Var.THRS2, lcn_defs.Var.THRS3, lcn_defs.Var.THRS4, lcn_defs.Var.THRS5]:
                return 'SL1'    # Whole register
        
        raise ValueError('Wrong variable type.')
    
    @staticmethod
    def request_leds_and_logic_ops():
        """
        Generates a request for LED and logic-operations states.

        @return the PCK command (without address header) as text
        """
        return 'SMT'
    
    @staticmethod
    def control_led(led_id, state):
        """
        Generates a command to the set the state of a single LED.

        @param ledId 0..11
        @param state the state to set
        @return the PCK command (without address header) as text        
        """
        if (led_id < 0) or (led_id > 11):
            raise ValueError('Bad led_id.')
        return 'LA{:03d}{:2}'.format(led_id + 1, state.value)
    
    @staticmethod
    def send_keys(cmds, keys):
        """
        Generates a command to send LCN keys.

        @param cmds the 4 concrete commands to send for the tables (A-D)
        @param keys the tables' 8 key-states (true means "send")
        @return the PCK command (without address header) as text        
        """
        if (len(cmds) != 4) or (len(keys) != 8):
            raise ValueError('Wrong cmds length or wrong keys length.')
        ret = 'TS'
        for i, cmd in enumerate(cmds):
            if (cmd == lcn_defs.SendKeyCommand.DONTSEND) and (i == 3):
                # By skipping table D (if it is not used), we use the old command
                # for table A-C which is compatible with older LCN modules
                break
            else:
                ret += cmd.value
        
        for key in keys:
            ret += '1' if key else '0'
        
        return ret
    
    @staticmethod
    def send_keys_hit_defered(table_id, time, time_unit, keys):
        """
        Generates a command to send LCN keys deferred / delayed.
        @param tableId 0(A)..3(D)
        @param time the delay time
        @param timeUnit the time unit
        @param keys the key-states (true means "send")
        @return the PCK command (without address header) as text        
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
        """
        Generates a request for key-lock states.
        Always requests table A-D. Supported since LCN-PCHK 2.8.

        @return the PCK command (without address header) as text        
        """
        return 'STX'

    @staticmethod
    def lock_keys(table_id, states):
        """
        Generates a command to lock keys.

        @param tableId 0(A)..3(D)
        @param states the 8 key-lock modifiers
        @return the PCK command (without address header) as text 
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
    def lock_key_tab_a_temporary(time, time_unit, keys):
        """
        Generates a command to lock keys for table A temporary.
        There is no hardware-support for locking tables B-D.

        @param time the lock time
        @param timeUnit the time unit
        @param keys the 8 key-lock states (true means lock)
        @return the PCK command (without address header) as text       
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
    def dyn_text_header(row, part):
        """
        Generates the command header / start for sending dynamic texts.
        Used by LCN-GTxD periphery (supports 4 text rows).
        To complete the command, the text to send must be appended (UTF-8 encoding).
        Texts are split up into up to 5 parts with 12 "UTF-8 bytes" each.

        @param row 0..3
        @param part 0..4
        @return the PCK command (without address header) as text       
        """
        if (row < 0) or (row > 3) or (part < 0) or (part > 4):
            raise ValueError('Wrong row or part.')
        return 'GTDT{:d}{:d}'.format(row + 1, part + 1)
    
    @staticmethod
    def lock_regulator(reg_id, state):
        """
        Generates a command to lock a regulator.

        @param regId 0..1
        @param state the lock state
        @return the PCK command (without address header) as text
        """
        if (reg_id < 0) or (reg_id > 1):
            raise ValueError('Wrong reg_id.')
        return 'RE{:s}X{:s}'.format('A' if reg_id == 0 else 'B',
                                    'S' if state else 'A')
