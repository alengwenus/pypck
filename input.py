import logging
import re
 
from pypck.pck_commands import PckParser, PckGenerator
from pypck.lcn_addr import LcnAddrMod
 
 
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
            return AuthOk()
   
    def process(self, conn):
        conn.on_auth_ok()
 
 
class AuthPassword(Input):
    @staticmethod
    def try_parse(input):
        if input == PckParser.AUTH_PASSWORD:
            return AuthPassword()
   
    def process(self, conn):
        conn.send_command(conn.password)
 
 
class AuthUsername(Input):
    @staticmethod
    def try_parse(input):
        if input == PckParser.AUTH_USERNAME:
            return AuthUsername()
 
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
            return LcnConnState(True)
        elif input == PckParser.LCNCONNSTATE_DISCONNECTED:
            return LcnConnState(False)
 
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
    def try_parse(self, input):
        matcher_pos = PckParser.PATTERN_ACK_POS.match(input)
        if matcher_pos:
            addr = LcnAddrMod(int(matcher_pos.group('seg_id')),
                              int(matcher_pos.group('mod_id')))
            return ModAck(addr, -1)
        
        matcher_neg = PckParser.PATTERN_ACK_NEG.match(input)
        if matcher_neg:
            addr = LcnAddrMod(int(matcher_neg.group('seg_id')),
                              int(matcher_neg.group('mod_id')))
            return ModAck(addr, matcher_neg.group('code'))
           
    def process(self, conn):
        super().process(conn)   # Will replace source segment 0 with the local segment id
        info = conn.get_mod_info(self.logical_source_addr)
        if info is not None:
            info.on_ack(self.code, conn.DEFAULT_TIMEOUT_MSEC)       
 
 
class ModSk(ModInput):
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
            return ModSk(addr, int(matcher.group('id')))
 
    def process(self, conn):
        if self.physical_source_addr.seg_id == 0:
            conn.set_local_seg_id(self.reported_seg_id)
        super().process(conn)   # Will replace source segment 0 with the local segment id


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
            return ModStatusOutput(addr, int(matcher.group('output_id')), float(matcher.group('percent')))
        
        matcher = PckParser.PATTERN_STATUS_OUTPUT_NATIVE.match(input)
        if matcher:
            addr = LcnAddrMod(int(matcher.group('seg_id')),
                              int(matcher.group('mod_id')))
            return ModStatusOutput(addr, int(matcher.group('output_id')), float(matcher.group('value')) / 2.)

    def process(self, conn):
        super().process(conn)   # Will replace source segment 0 with the local segment id
        info = conn.get_mod_info(self.logical_source_addr)
        if info is not None:
            info.request_status_outputs[self.output_id].cancel()
            info.new_input(self)


# ### Inputs send to modules
# 
# class OutputDimAbs(ModInput):
#     # Pattern to parse ON and OFF commands (shortcuts for DIM 0 and DIM 100).
#     PATTERN_ONOFF = re.compile(r'(?P<outputId>[1234]|(ALL))(\.(?P<ramp>\d+(,\d+)?(?P<timeUnit>.+)))?')
#     # Pattern to parse DIM commands.
#     PATTERN_DIM = re.compile(r'(?P<outputId>[1234]|(ALL))\.(?P<value>\d+(,\d+)?)%(\.(?P<ramp>\d+(,\d+)?(?P<timeUnit>.+)))?')
#     # Pattern to parse DIM commands with i%.
#     PATTERN_DIMI = re.compile(r'(?P<outputId>[1234]|(ALL))\.%i(\.(?P<ramp>\d+(,\d+)?(?P<timeUnit>.+)))?')
#     
#     def __init__(self, physical_source_addr, output_id, percent, ramp_msec):
#         super().__init__(physical_source_addr)
#         self.output_id = output_id
#         self.percent = percent
#         self.ramp_msec = ramp_msec
#     
#     @staticmethod
#     def try_parse(input):
#         pass
#     
#     def process(self, conn):
#         super().process(conn)   # Will replace source segment 0 with the local segment id
#         info = conn.get_mod_info(self.logical_source_addr)
#         if info is not None:
#             info.request_status_outputs[self.output_id].cancel()
#             info.new_command(self)

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
               ModStatusOutput,
               Unknown]
    
    @staticmethod
    def parse(input):
        for parser in InputParser.parsers:
            input_obj = parser.try_parse(input)
            if input_obj is not None:
                return input_obj
 
 
