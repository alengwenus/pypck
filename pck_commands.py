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
    PATTERN_STATUS_THRS = re.compile(r'%M(?P<seg_id>\d{3})(?P<mod_id>\d{3})\.T(?P<register_id>\d)(?P<thrsId>\d)(?P<value>\d+)')

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
    def __init__(self):
        pass
    
    # Terminates a PCK command
    TERMINATION = '\n'
    
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
        return '!OM{:s}{:s}'.format('1' if (dim_mode == lcn_defs.output_port_dim_mode.STEPS200) else '0',
                                    'P' if (status_mode == lcn_defs.output_port_status_mode.PERCENT) else 'N') 

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
        n = round(percent*2)
        if (n % 2) == 0:    # Use the percent command (supported by all LCN-PCHK versions)
            return 'A{:d}DI{:03d}{:03d}'.format(output_id + 1, n / 2, ramp)
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
            return 'A{:d}{:s}{:03d}'.format(output_id + 1, 'AD' if percent >= 0 else 'SB', abs(n / 2))
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
        return 'A{:d}TA{:03d}'.format(output_id, ramp)
    
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
        if states.length != 8:
            raise ValueError('Invalid states length.')
        ret = 'R8'
        for i in range(8):
            if states[i] == lcn_defs.relay_state_modifier.ON:
                ret += '1'
            elif states[i] == lcn_defs.relay_state_modifier.OFF:
                ret += '0'
            elif states[i] == lcn_defs.relay_state_modifier.TOGGLE:
                ret += 'U'
            elif states[i] == lcn_defs.relay_state_modifier.NOCHANGE:
                ret += '-'
            else:
                raise ValueError('Invalid state.')
        return ret

    @staticmethod   
    def request_bin_sensors_status():
        """
        Generates a binary-sensors status request.
         
        @return the PCK command (without address header) as text
        """
        return 'SMB'
    