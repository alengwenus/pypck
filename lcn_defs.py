from enum import Enum, auto
from collections import OrderedDict


default_connection_settings = {'NUM_TRIES': 3,  # Total number of request to sent before going into failed-state.
                               'PING_TIMEOUT': 600000,  # The default timeout for pings sent to PCHK.
                               'MAX_STATUS_EVENTBASED_VALUEAGE_MSEC': 600000,   # Poll interval for status values that automatically send their values on change.
                               'MAX_STATUS_POLLED_VALUEAGE_MSEC': 30000,    # Poll interval for status values that automatically send their values on change.
                               'STATUS_REQUEST_DELAY_AFTER_COMMAND_MSEC': 2000  # Status request delay after a command has been send which potentially changed that status.
                               }




class OldEnum(OrderedDict):
    def __init__(self, *sequential, **named):
        for i, s in enumerate(sequential):
            self[s] = i
        
        for t in named:
            self[t[0]] = t[1]

    def __getattr__(self, name):
        return self[name]
   


   
   
"""
LCN dimming mode.
If solely modules with firmware 170206 or newer are present, LCN-PRO automatically programs STEPS200.
Otherwise the default is STEPS50.
Since LCN-PCHK doesn't know the current mode, it must explicitly be set.
"""    
class OutputPortDimMode(Enum):
    STEPS50 = auto()    # 0..50 dimming steps (all LCN module generations)
    STEPS200 = auto()   # 0..200 dimming steps (since 170206)
    

"""
Tells LCN-PCHK how to format output-port status-messages.
PERCENT: allows to show the status in half-percent steps (e.g. "10.5").
NATIVE: is completely backward compatible and there are no restrictions
concerning the LCN module generations. It requires LCN-PCHK 2.3 or higher though.
"""
class OutputPortStatusMode(Enum):
    PERCENT = auto()    # Default (compatible with all versions of LCN-PCHK)
    NATIVE = auto()     # 0..200 steps (since LCN-PCHK 2.3)


"""
Relay-state modifiers used in LCN commands.
"""
class RelayStateModifier(Enum):
    ON = auto()
    OFF = auto()
    TOGGLE = auto()
    NOCHANGE = auto()



class Var(OldEnum):
    def __init__(self, *sequential, **named):
        super().__init__(*sequential, **named)
        # Helper list to get var by numeric id.
        self._var_id_to_var = [self.VAR1ORTVAR, self.VAR2ORR1VAR, self.VAR3ORR2VAR,
                               self.VAR4, self.VAR5, self.VAR6, self.VAR7, self.VAR8,
                               self.VAR9, self.VAR10, self.VAR11, self.VAR12]
        
        # Helper list to get set-point var by numeric id.
        self._set_point_id_to_var = [self.R1VARSETPOINT, self.R2VARSETPOINT]
        
        # Helper list to get threshold var by numeric id.
        self._thrs_id_to_var = [[self.THRS1, self.THRS2, self.THRS3, self.THRS4, self.THRS5],
                                [self.THRS2_1, self.THRS2_2, self.THRS2_3, self.THRS2_4],
                                [self.THRS3_1, self.THRS3_2, self.THRS3_3, self.THRS3_4],
                                [self.THRS4_1, self.THRS4_2, self.THRS4_3, self.THRS4_4]]
        
        # Helper list to get S0-input var by numeric id.
        self._s0_id_to_var = [self.S0INPUT1, self.S0INPUT2, self.S0INPUT3, self.S0INPUT4]
        
    def var_id_to_var(self, var_id):
        """
        Translates a given id into a variable type.

        @param varId 0..11
        @return the translated var
        """
        if (var_id < 0) or (var_id >= len(self._var_id_to_var)):
            raise ValueError('Bad var_id.')
        return self._var_id_to_var[var_id]
        
    def set_point_id_to_var(self, set_point_id):
        """
        Translates a given id into a LCN set-point variable type.

        @param setPointId 0..1
        @return the translated var     
        """    
        if (set_point_id < 0) or (set_point_id >= len(self._set_point_id_to_var)):
            raise ValueError('Bad set_point_id.')
        return self._set_point_id_to_var[set_point_id]
    
    def thrs_id_to_var(self, register_id, thrs_id):
        """
        Translates given ids into a LCN threshold variable type.
        
        @param registerId 0..3
        @param thrsId 0..4 for register 0, 0..3 for registers 1..3
        @return the translated var Var
        """
        if (register_id < 0) or (register_id >= len(self._thrs_to_var)) or (thrs_id < 0) or (thrs_id >= (5 if register_id == 0 else 4)):
            raise ValueError('Bad register_id and/or thrs_id.')
        return self._thrs_id_to_var[register_id][thrs_id]
    
    def s0_id_to_var(self, s0_id):
        """
        Translates a given id into a LCN S0-input variable type.

        @param s0Id 0..3
        @return the translated var
        """
        if (s0_id < 0) or (s0_id >= len(self._s0_id_to_var)):
            raise ValueError('Bad s0_id.')
        return self._s0_id_to_var_array[s0_id]

    def to_var_id(self, var):
        """
        Translates a given variable type into a variable id.
        
        @param var the variable type to translate
        @return 0..11 or -1 if wrong type
        """        
        if var == self.VAR1ORTVAR:
            return 0
        elif var == self.VAR2ORR1VAR:
            return 1
        elif var == self.VAR3ORR2VAR:
            return 2
        elif var == self.VAR4:
            return 3
        elif var == self.VAR5:
            return 4
        elif var == self.VAR6:
            return 5
        elif var == self.VAR7:
            return 6
        elif var == self.VAR8:
            return 7
        elif var == self.VAR9:
            return 8
        elif var == self.VAR10:
            return 9
        elif var == self.VAR11:
            return 10
        elif var == self.VAR12:
            return 11
        else:
            return -1
        
    def to_set_point_id(self, var):
        """
        Translates a given variable type into a set-point id.
        
        @param var the variable type to translate
        @return 0..1 or -1 if wrong type        
        """
        if var == self.R1VARSETPOINT:
            return 0
        elif var == self.R2VARSETPOINT:
            return 1
        else:
            return -1
        
    def to_thrs_register_id(self, var):
        """
        Translates a given variable type into a threshold register id.

        @param var the variable type to translate
        @return 0..3 or -1 if wrong type        
        """
        if var in [self.THRS1, self.THRS2, self.THRS3, self.THRS4, self.THRS5]:
            return 0
        elif var in [self.THRS2_, self.THRS2_2, self.THRS2_3, self.THRS2_4]:
            return 1
        elif var in [self.THRS3_, self.THRS3_2, self.THRS3_3, self.THRS3_4]:
            return 2
        elif var in [self.THRS4_, self.THRS4_2, self.THRS4_3, self.THRS4_4]:
            return 3
        else:
            return -1
        
    def to_thrs_id(self, var):
        """
        Translates a given variable type into a threshold id.

        @param var the variable type to translate
        @return 0..4 or -1 if wrong type        
        """
        if var in [self.THRS1, self.THRS2_1, self.THRS3_1, self.THRS4_1]:
            return 0
        elif var in [self.THRS2, self.THRS2_2, self.THRS3_2, self.THRS4_2]:
            return 1
        elif var in [self.THRS3, self.THRS2_3, self.THRS3_3, self.THRS4_3]:
            return 2
        elif var in [self.THRS4, self.THRS2_4, self.THRS3_4, self.THRS4_4]:
            return 3
        elif var == self.THRS5:
            return 4
        else:
            return -1
    
    def to_s0_id(self, var):
        """
        Translates a given variable type into an S0-input id.

        @param var the variable type to translate
        @return 0..3 or -1 if wrong type
        """
        if var == self.S0INPUT1:
            return 0
        elif var == self.S0INPUT2:
            return 1
        elif var == self.S0INPUT3:
            return 2
        elif var == self.S0INPUT4:
            return 3
        else:
            return -1

    def is_lockable_regulator_source(self, var):
        """
        Checks if the the given variable type is lockable.

        @param var the variable type to check
        @return true if lockable
        """
        return var in [self.R1VARSETPOINT, self.R2VARSETPOINT]
    
    def use_lcn_special_values(self, var):
        """
        Checks if the given variable type uses special values.
        Examples for special values: "No value yet", "sensor defective" etc.

        @param var the variable type to check
        @return true if special values are in use    
        """
        return var not in [self.S0INPU1, self.S0INPUT2, self.S0INPUT3, self.S0INPUT4] 
    
    def has_type_in_response(self, var, sw_age):
        """
        Module-generation check.
        Checks if the given variable type would receive a typed response if
        its status was requested.

        @param var the variable type to check
        @param swAge the target LCN-modules firmware version
        @return true if a response would contain the variable's type
        """
        if sw_age < 0x170206:
            if var in [self.VAR1ORTVAR, self.VAR2ORR1VAR, self.VAR3ORR2VAR, self.R1VARSETPOINT, self.R2VARSETPOINT]:
                return False
        return True

    def is_event_based(self, var, sw_age):
        """
        Module-generation check.
        Checks if the given variable type automatically sends status-updates on
        value-change. It must be polled otherwise.

        @param var the variable type to check
        @param swAge the target LCN-module's firmware version
        @return true if the LCN module supports automatic status-messages for this var        
        """
        if (self.to_set_point_id(var) != -1) or (self.to_s0_id(var) != -1):
            return True
        return sw_age >= 0x170206

    def should_poll_status_after_command(self, var, is2013):
        """
        Module-generation check.
        Checks if the target LCN module would automatically send status-updates if
        the given variable type was changed by command.

        @param var the variable type to check
        @param is2013 the target module's-generation
        @return true if a poll is required to get the new status-value       
        """
        # Regulator set-points will send status-messages on every change (all firmware versions)
        if self.to_set_point_id(var) != -1:
            return False
        
        # Thresholds since 170206 will send status-messages on every change
        if is2013 and (self.to_thrs_register_id(var != -1)):
            return False

        # Others:
        # - Variables before 170206 will never send any status-messages
        # - Variables since 170206 only send status-messages on "big" changes
        # - Thresholds before 170206 will never send any status-messages
        # - S0-inputs only send status-messages on "big" changes
        # (all "big changes" cases force us to poll the status to get faster updates)        
        return True

    def should_poll_status_after_regulator_lock(self, sw_age, lock_state):
        """
        Module-generation check.
        Checks if the target LCN module would automatically send status-updates if
        the given regulator's lock-state was changed by command.

        @param swAge the target LCN-module's firmware version
        @param lockState the lock-state sent via command
        @return true if a poll is required to get the new status-value        
        """
        # LCN modules before 170206 will send an automatic status-message for "lock", but not for "unlock"
        return (lock_state == False) and (sw_age < 0x170206)


"""
LCN variable types.
"""
var = Var('UNKNOWN',   # Used if the real type is not known (yet)
          'VAR1ORTVAR',
          'VAR2ORR1VAR',
          'VAR3ORR2VAR',
          'VAR4',
          'VAR5',
          'VAR6',
          'VAR7',
          'VAR8',
          'VAR9',
          'VAR10',
          'VAR11',
          'VAR12',     # Since 170206
          'R1VARSETPOINT',
          'R2VARSETPOINT',     # Set-points for regulators
          'THRS1',
          'THRS2',
          'THRS3',
          'THRS4',
          'THRS5',     # Register 1 (THRS5 only before 170206)
          'THRS2_1',
          'THRS2_2',
          'THRS2_3',
          'THRS2_4',   # Register 2 (since 2012)
          'THRS3_1',
          'THRS3_2',
          'THRS3_3',
          'THRS3_4',   # Register 3 (since 2012)
          'THRS4_1',
          'THRS4_2',
          'THRS4_3',
          'THRS4_4',   # Register 4 (since 2012)
          'S0INPUT1',
          'S0INPUT2',
          'S0INPUT3',
          'S0INPUT4')  # LCN-BU4L


class VarUnit(OldEnum):
    def __init__(self, *sequential, **named):
        super().__init__(*sequential, **named)
    
    def parse(self, input):
        input = input.upper()
        if input == 'LCN':
            return self.NATIVE
        elif input in ['CELSIUS', 'oCELSIUS', 'oC']:
            return self.CELSIUS
        elif input in ['KELVIN', 'oKELVIN', 'oK']:
            return self.KELVIN
        elif input in ['FAHRENHEIT', 'oFAHRENHEIT', 'oF']:
            return self.FAHRENHEIT
        elif input in ['LUX_T', 'LX_T']:
            return self.LUX_T
        elif input in ['LUX', 'LX']:
            return self.LUX_I
        elif input == 'M/S':
            return self.METERPERSECOND
        elif input == '%':
            return self.PERCENT
        elif input == 'PPM':
            return self.PPM
        elif input in ['VOLT', 'V']:
            return self.VOLT
        elif input in ['AMPERE', 'AMP', 'A']:
            return self.AMPERE
        elif input in ['DEGREE', 'o']:
            return self.DEGREE
        
        
        
    
var_unit = VarUnit('NATIVE',    # LCN internal representation (0 = -100�C for absolute values)
                   'CELSIUS',
                   'KELVIN',
                   'FAHRENHEIT',
                   'LUX_T',
                   'LUX_I',
                   'METERPERSECOND',    # Used for LCN-WIH wind speed
                   'PERCENT',   # Used for humidity
                   'PPM',   # Used by CO2 sensor
                   'VOLT',
                   'AMPERE',
                   'DEGREE'    #Used for angles,
                   )


class VarValue(object):
    """
    A value of an LCN variable.

    It internally stores the native LCN value and allows to convert from/into other units.
    Some conversions allow to specify whether the source value is absolute or relative.
    Relative values are used to create varvalues that can be added/subtracted from
    other (absolute) varvalues.    
    """
    def __init__(self, native_value):
        """
        Constructor with native LCN value.

        @param nativeValue the native value       
        """
        self.native_value = native_value

    @staticmethod
    def from_native(self, n):
        return VarValue(n)




def time_to_ramp_value(self, time_msec):
    """
    Converts the given time into an LCN ramp value.
    
    @param timeMSec the time in milliseconds
    @return the (LCN-internal) ramp value (0..250)
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
        ret = (time_msec / 1000 - 6) / 2 + 10
        if ret >= 250:
            ret = 250
    return ret 

