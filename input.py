import logging
import re
 
from pypck.pck_commands import PckParser, PckGenerator
from pypck.lcn_addr import LcnAddrMod
from pypck.timeout_retry import DEFAULT_TIMEOUT_MSEC
from pypck import lcn_defs

 
class Input(object):
    """
    Parent class for all input data read from LCN-PCHK.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
 
    @staticmethod
    def try_parse(input):
        """
        Tries to parse the given input text.
        Will return a list of parsed Inputs. The list might be empty (but not null).
       
        @param input the input data received from LCN-PCHK
        @return the parsed Inputs (never null)
        """
        raise NotImplementedError
 
def process(self, conn):
    raise NotImplementedError
 
 
class ModInput(Input):
    """
    Parent class of all inputs having an LCN module as its source.
    """
    def __init__(self, physical_source_addr):
        super().__init__()
        self.physical_source_addr = physical_source_addr
        self.logical_source_addr = LcnAddrMod()
   
    def get_logical_source_addr(self):
        return self.logical_source_addr
   
    def process(self, conn):
        if conn.is_ready(): # Skip if we don't have all necessary bus info yet
            self.logical_source_addr = conn.physical_to_logical(self.physical_source_addr)
 
 
 
### Plain text inputs
 
class AuthOk(Input):
    @staticmethod
    def try_parse(input):
        if input == PckParser.AUTH_OK:
            return [AuthOk()]
   
    def process(self, conn):
        conn.on_auth_ok()
 
 
class AuthPassword(Input):
    @staticmethod
    def try_parse(input):
        if input == PckParser.AUTH_PASSWORD:
            return [AuthPassword()]
   
    def process(self, conn):
        conn.send_command(conn.password)
 
 
class AuthUsername(Input):
    @staticmethod
    def try_parse(input):
        if input == PckParser.AUTH_USERNAME:
            return [AuthUsername()]
 
    def process(self, conn):
        conn.send_command(conn.username)
 
 
class LcnConnState(Input):
    def __init__(self, is_lcn_connected):
        super().__init__()
        self._is_lcn_connected = is_lcn_connected
 
    @property
    def is_lcn_connected(self):
        return self._is_lcn_connected
 
    @staticmethod
    def try_parse(input):
        if input == PckParser.LCNCONNSTATE_CONNECTED:
            return [LcnConnState(True)]
        elif input == PckParser.LCNCONNSTATE_DISCONNECTED:
            return [LcnConnState(False)]
 
    def process(self, conn):
        if self.is_lcn_connected:
            self.logger.info('LCN is connected.')
            conn.on_successful_login()
            conn.send_command(PckGenerator.set_operation_mode(conn.dim_mode, conn.status_mode))
 
 
 
### Inputs received from modules
 
class ModAck(ModInput):
    def __init__(self, physical_source_addr, code):
        super().__init__(physical_source_addr)
        self.code = code
   
    def get_code(self):
        return self.code
 
    @staticmethod
    def try_parse(input):
        matcher_pos = PckParser.PATTERN_ACK_POS.match(input)
        if matcher_pos:
            addr = LcnAddrMod(int(matcher_pos.group('seg_id')),
                              int(matcher_pos.group('mod_id')))
            return [ModAck(addr, -1)]
        
        matcher_neg = PckParser.PATTERN_ACK_NEG.match(input)
        if matcher_neg:
            addr = LcnAddrMod(int(matcher_neg.group('seg_id')),
                              int(matcher_neg.group('mod_id')))
            return [ModAck(addr, matcher_neg.group('code'))]
           
    def process(self, conn):
        super().process(conn)   # Will replace source segment 0 with the local segment id
        module_conn = conn.get_module_conn(self.logical_source_addr)
        module_conn.on_ack(self.code, DEFAULT_TIMEOUT_MSEC)       
 
 
class ModSk(ModInput):
    """
    Segment information received from an LCN segment coupler.
    """
    def __init__(self, physical_source_addr, reported_seg_id):
        super().__init__(physical_source_addr)
        self.reported_seg_id = reported_seg_id
   
    def get_reported_seg_id(self):
        return self.reported_seg_id
   
    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_SK_RESPONSE.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            return [ModSk(addr, int(matcher.group('id')))]
 
    def process(self, conn):
        if self.physical_source_addr.seg_id == 0:
            conn.set_local_seg_id(self.reported_seg_id)
        super().process(conn)   # Will replace source segment 0 with the local segment id
        conn.status_segment_scan.cancel()
        for module_conn in conn.module_conns.values():
            module_conn.activate_status_request_handlers()


class ModSn(ModInput):
    """
    Serial number and firmware version received from an LCN module.
    """
    def __init__(self, physical_source_addr, sw_age):
        super().__init__(physical_source_addr)
        self.sw_age = sw_age
   
    def get_sw_age(self):
        return self.sw_age
   
    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_SN.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            return [ModSn(addr, int(matcher.group('sw_age'), 16))]
 
    def process(self, conn):
        super().process(conn)   # Will replace source segment 0 with the local segment id
        #print(self.logical_source_addr)
        module_conn = conn.get_module_conn(self.logical_source_addr)
        #print(module_conn.seg_id, module_conn.mod_id)
        #print(conn.module_conns)
        module_conn.set_sw_age(self.sw_age)
        module_conn.request_sw_age.cancel()
        module_conn.initialize_variables()



class ModStatusOutput(ModInput):
    """
    Status of an output-port received from an LCN module.
    """
    def __init__(self, physical_source_addr, output_id, percent):
        super().__init__(physical_source_addr)
        self.output_id = output_id
        self.percent = percent
        
    def get_output_id(self):
        return self.output_id
    
    def get_percent(self):
        return self.percent
    
    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_STATUS_OUTPUT_PERCENT.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            return [ModStatusOutput(addr, int(matcher.group('output_id')), float(matcher.group('percent')))]
        
        matcher = PckParser.PATTERN_STATUS_OUTPUT_NATIVE.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            return [ModStatusOutput(addr, int(matcher.group('output_id')), float(matcher.group('value')) / 2.)]

    def process(self, conn):
        super().process(conn)   # Will replace source segment 0 with the local segment id
        module_conn = conn.get_module_conn(self.logical_source_addr)
        #module_conn.request_status_outputs[self.output_id].cancel()
        module_conn.new_input(self)


class ModStatusRelays(ModInput):
    """
    Status of 8 relays received from an LCN module.
    """
    def __init__(self, physical_source_addr, states):
        super().__init__(physical_source_addr)
        self.states = states
        
    def get_state(self, relay_id):
        """
        Gets the state of a single relay.
        
        @param relay_id 0..7
        @return the relay's state
        """
        return self.states[relay_id]
    
    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_STATUS_RELAYS.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            return [ModStatusRelays(addr, PckParser.get_boolean_value(int(matcher.group('byte_value'))))]

    def process(self, conn):
        super().process(conn)   # Will replace source segment 0 with the local segment id
        module_conn = conn.get_module_conn(self.logical_source_addr)
        # module_conn.request_status_relays.cancel()
        module_conn.new_input(self)


class ModStatusBinSensors(ModInput):
    """
    Status of 8 binary sensors received from an LCN module.
    """
    def __init__(self, physical_source_addr, states):
        super().__init__(physical_source_addr)
        self.states = states
        
    def get_state(self, bin_sensor_id):
        """
        Gets the state of a single binary-sensor.
        
        @param bin_sensor_id 0..7
        @return the binary-sensor's state
        """
        return self.states[bin_sensor_id]
    
    @staticmethod
    def try_parse(input):
        ret = []
        matcher = PckParser.PATTERN_STATUS_BINSENSORS.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            return [ModStatusRelays(addr, PckParser.get_boolean_value(int(matcher.group('byte_value'))))]
        return ret

    def process(self, conn):
        super().process(conn)   # Will replace source segment 0 with the local segment id
        module_conn = conn.get_module_conn(self.logical_source_addr)
        # module_conn.request_status_relays.cancel()
        module_conn.new_input(self)


class ModStatusVar(ModInput):
    """
    Status of a variable received from an LCN module.
    """
    def __init__(self, physical_source_addr, orig_var, value):
        super().__init__(physical_source_addr)
        self.orig_var = orig_var
        self.value = value
        
    def get_var(self):
        """
        Gets the variable's real type.
        
        @return the real type
        """
        return self.var
    
    def get_value(self):
        """
        Gets the variable's value.

        @return the value        
        """
        return self.value
    
    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_STATUS_VAR.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            var = lcn_defs.var.var_id_to_var(int(matcher.group('id')) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group('value')))
            return [ModStatusVar(addr, var, value)]
        
        matcher = PckParser.PATTERN_STATUS_SETVAR.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            var = lcn_defs.var.set_point_id_to_var(int(matcher.group('id')) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group('value')))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_STATUS_THRS.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            var = lcn_defs.var.thrs_id_to_var(int(matcher.group('id')) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group('value')))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_STATUS_S0INPUT.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            var = lcn_defs.var.s0_id_to_var(int(matcher.group('id')) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group('value')))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_VAR_GENERIC.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            var = lcn_defs.var.UNKNOWN
            value = lcn_defs.VarValue.from_native(int(matcher.group('value')))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_THRS5.match(input)
        if matcher:
            ret = []
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            for thrs_id in range(5):
                var = lcn_defs.var.var_id_to_var(int(matcher.group('id')) - 1)
                value = lcn_defs.VarValue.from_native(int(matcher.group('value{:d}'.format(thrs_id + 1))))
                ret.append(ModStatusVar(addr, var, value))
            return ret

### Other inputs
           
class Unknown(Input):
    def __init__(self, input):
        super().__init__()
        self._input = input
 
    @staticmethod
    def try_parse(input):
        return Unknown(input)
   
    @property
    def input(self):
        return self._input
   
    def process(self, conn):
        pass
 




 
           
class InputParser(object):
    parsers = [AuthOk,
               AuthPassword,
               AuthUsername,
               LcnConnState,
               ModAck,
               ModSk,
               ModSn,
               ModStatusOutput,
               ModStatusRelays,
               ModStatusBinSensors,
               Unknown]
    
    @staticmethod
    def parse(input):
        ret = []
        for parser in InputParser.parsers:
            ret = parser.try_parse(input)
        return ret
            
 
 
