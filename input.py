import logging

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
        self._physical_source_addr = physical_source_addr
        self._logical_source_addr = LcnAddrMod()
    
    def get_logical_source_addr(self):
        return self._logical_source_addr
    
    def process(self, conn):
        if conn.is_ready(): # Skip if we don't have all necessary bus info yet
            self.logical_source_addr = conn.physical_to_logical(self._physical_source_addr)



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

            
class Unknown(Input):
    def __init__(self, input):
        super().__init__()
        self.input = input

    @staticmethod
    def try_parse(input):
        return Unknown(input)
    
    def get_input(self):
        return self.input
    
    def process(self, conn):
        pass



            
class InputParser(object):
    parsers = [AuthOk,
               AuthPassword,
               AuthUsername,
               LcnConnState,
               Unknown] 
    
    @staticmethod
    def parse(input):
        for parser in InputParser.parsers:
            input_obj = parser.try_parse(input)
            if input_obj is not None:
                return input_obj

