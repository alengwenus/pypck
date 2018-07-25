from enum import Enum, auto
import math


default_connection_settings = {'NUM_TRIES': 3,  # Total number of request to sent before going into failed-state.
                               'PING_TIMEOUT': 600000,  # The default timeout for pings sent to PCHK.
                               'MAX_STATUS_EVENTBASED_VALUEAGE_MSEC': 600000,   # Poll interval for status values that automatically send their values on change.
                               'MAX_STATUS_POLLED_VALUEAGE_MSEC': 30000,    # Poll interval for status values that do not send their values on change (always polled).
                               'STATUS_REQUEST_DELAY_AFTER_COMMAND_MSEC': 2000  # Status request delay after a command has been send which potentially changed that status.
                               }




   
class OutputPortDimMode(Enum):
    """
    LCN dimming mode.
    If solely modules with firmware 170206 or newer are present, LCN-PRO automatically programs STEPS200.
    Otherwise the default is STEPS50.
    Since LCN-PCHK doesn't know the current mode, it must explicitly be set.
    """    
    STEPS50 = auto()    # 0..50 dimming steps (all LCN module generations)
    STEPS200 = auto()   # 0..200 dimming steps (since 170206)
    

class OutputPortStatusMode(Enum):
    """
    Tells LCN-PCHK how to format output-port status-messages.
    PERCENT: allows to show the status in half-percent steps (e.g. "10.5").
    NATIVE: is completely backward compatible and there are no restrictions
    concerning the LCN module generations. It requires LCN-PCHK 2.3 or higher though.
    """
    PERCENT = auto()    # Default (compatible with all versions of LCN-PCHK)
    NATIVE = auto()     # 0..200 steps (since LCN-PCHK 2.3)


def time_to_ramp_value(time_msec):
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


class Var(Enum):
    """
    LCN variable types.
    """
    UNKNOWN = auto()         # Used if the real type is not known (yet)
    VAR1ORTVAR = auto()
    VAR2ORR1VAR = auto()
    VAR3ORR2VAR = auto()
    VAR4 = auto()
    VAR5 = auto()
    VAR6 = auto()
    VAR7 = auto()
    VAR8 = auto()
    VAR9 = auto()
    VAR10 = auto()
    VAR11 = auto()
    VAR12 = auto()          # Since 170206
    R1VARSETPOINT = auto()
    R2VARSETPOINT = auto()  # Set-points for regulators
    THRS1 = auto()
    THRS2 = auto()
    THRS3 = auto()
    THRS4 = auto()
    THRS5 = auto()          # Register 1 (THRS5 only before 170206)
    THRS2_1 = auto()
    THRS2_2 = auto()
    THRS2_3 = auto()
    THRS2_4 = auto()        # Register 2 (since 2012)
    THRS3_1 = auto()
    THRS3_2 = auto()
    THRS3_3 = auto()
    THRS3_4 = auto()        # Register 3 (since 2012)
    THRS4_1 = auto()
    THRS4_2 = auto()
    THRS4_3 = auto()
    THRS4_4 = auto()        # Register 4 (since 2012)
    S0INPUT1 = auto()
    S0INPUT2 = auto()
    S0INPUT3 = auto()
    S0INPUT4 = auto()       # LCN-BU4L

    @staticmethod
    def var_id_to_var(var_id):
        """
        Translates a given id into a variable type.

        @param varId 0..11
        @return the translated var
        """
        if (var_id < 0) or (var_id >= len(Var._var_id_to_var)):
            raise ValueError('Bad var_id.')
        return Var._var_id_to_var[var_id]

    @staticmethod        
    def set_point_id_to_var(set_point_id):
        """
        Translates a given id into a LCN set-point variable type.

        @param setPointId 0..1
        @return the translated var     
        """    
        if (set_point_id < 0) or (set_point_id >= len(Var._set_point_id_to_var)):
            raise ValueError('Bad set_point_id.')
        return Var._set_point_id_to_var[set_point_id]
    
    @staticmethod
    def thrs_id_to_var(register_id, thrs_id):
        """
        Translates given ids into a LCN threshold variable type.
        
        @param registerId 0..3
        @param thrsId 0..4 for register 0, 0..3 for registers 1..3
        @return the translated var Var
        """
        if (register_id < 0) or (register_id >= len(Var._thrs_id_to_var)) or (thrs_id < 0) or (thrs_id >= (5 if (register_id == 0) else 4)):
            print(register_id, thrs_id)
            raise ValueError('Bad register_id and/or thrs_id.')
        return Var._thrs_id_to_var[register_id][thrs_id]
    
    @staticmethod
    def s0_id_to_var(s0_id):
        """
        Translates a given id into a LCN S0-input variable type.

        @param s0Id 0..3
        @return the translated var
        """
        if (s0_id < 0) or (s0_id >= len(Var._s0_id_to_var)):
            raise ValueError('Bad s0_id.')
        return Var._s0_id_to_var_array[s0_id]

    @staticmethod
    def to_var_id(var):
        """
        Translates a given variable type into a variable id.
        
        @param var the variable type to translate
        @return 0..11 or -1 if wrong type
        """        
        if var == Var.VAR1ORTVAR:
            return 0
        elif var == Var.VAR2ORR1VAR:
            return 1
        elif var == Var.VAR3ORR2VAR:
            return 2
        elif var == Var.VAR4:
            return 3
        elif var == Var.VAR5:
            return 4
        elif var == Var.VAR6:
            return 5
        elif var == Var.VAR7:
            return 6
        elif var == Var.VAR8:
            return 7
        elif var == Var.VAR9:
            return 8
        elif var == Var.VAR10:
            return 9
        elif var == Var.VAR11:
            return 10
        elif var == Var.VAR12:
            return 11
        else:
            return -1
        
    @staticmethod
    def to_set_point_id(var):
        """
        Translates a given variable type into a set-point id.
        
        @param var the variable type to translate
        @return 0..1 or -1 if wrong type        
        """
        if var == Var.R1VARSETPOINT:
            return 0
        elif var == Var.R2VARSETPOINT:
            return 1
        else:
            return -1
        
    @staticmethod
    def to_thrs_register_id(var):
        """
        Translates a given variable type into a threshold register id.

        @param var the variable type to translate
        @return 0..3 or -1 if wrong type        
        """
        if var in [Var.THRS1, Var.THRS2, Var.THRS3, Var.THRS4, Var.THRS5]:
            return 0
        elif var in [Var.THRS2_1, Var.THRS2_2, Var.THRS2_3, Var.THRS2_4]:
            return 1
        elif var in [Var.THRS3_1, Var.THRS3_2, Var.THRS3_3, Var.THRS3_4]:
            return 2
        elif var in [Var.THRS4_1, Var.THRS4_2, Var.THRS4_3, Var.THRS4_4]:
            return 3
        else:
            return -1

    @staticmethod        
    def to_thrs_id(var):
        """
        Translates a given variable type into a threshold id.

        @param var the variable type to translate
        @return 0..4 or -1 if wrong type        
        """
        if var in [Var.THRS1, Var.THRS2_1, Var.THRS3_1, Var.THRS4_1]:
            return 0
        elif var in [Var.THRS2, Var.THRS2_2, Var.THRS3_2, Var.THRS4_2]:
            return 1
        elif var in [Var.THRS3, Var.THRS2_3, Var.THRS3_3, Var.THRS4_3]:
            return 2
        elif var in [Var.THRS4, Var.THRS2_4, Var.THRS3_4, Var.THRS4_4]:
            return 3
        elif var == Var.THRS5:
            return 4
        else:
            return -1
    
    @staticmethod
    def to_s0_id(var):
        """
        Translates a given variable type into an S0-input id.

        @param var the variable type to translate
        @return 0..3 or -1 if wrong type
        """
        if var == Var.S0INPUT1:
            return 0
        elif var == Var.S0INPUT2:
            return 1
        elif var == Var.S0INPUT3:
            return 2
        elif var == Var.S0INPUT4:
            return 3
        else:
            return -1
    
    @staticmethod
    def is_lockable_regulator_source(var):
        """
        Checks if the the given variable type is lockable.

        @param var the variable type to check
        @return true if lockable
        """
        return var in [Var.R1VARSETPOINT, Var.R2VARSETPOINT]
    
    @staticmethod
    def use_lcn_special_values(var):
        """
        Checks if the given variable type uses special values.
        Examples for special values: "No value yet", "sensor defective" etc.

        @param var the variable type to check
        @return true if special values are in use    
        """
        return var not in [Var.S0INPU1, Var.S0INPUT2, Var.S0INPUT3, Var.S0INPUT4] 
    
    @staticmethod
    def has_type_in_response(var, sw_age):
        """
        Module-generation check.
        Checks if the given variable type would receive a typed response if
        its status was requested.

        @param var the variable type to check
        @param swAge the target LCN-modules firmware version
        @return true if a response would contain the variable's type
        """
        if sw_age < 0x170206:
            if var in [Var.VAR1ORTVAR, Var.VAR2ORR1VAR, Var.VAR3ORR2VAR, Var.R1VARSETPOINT, Var.R2VARSETPOINT]:
                return False
        return True

    @staticmethod
    def is_event_based(var, sw_age):
        """
        Module-generation check.
        Checks if the given variable type automatically sends status-updates on
        value-change. It must be polled otherwise.

        @param var the variable type to check
        @param swAge the target LCN-module's firmware version
        @return true if the LCN module supports automatic status-messages for this var        
        """
        if (Var.to_set_point_id(var) != -1) or (Var.to_s0_id(var) != -1):
            return True
        return sw_age >= 0x170206

    @staticmethod
    def should_poll_status_after_command(var, is2013):
        """
        Module-generation check.
        Checks if the target LCN module would automatically send status-updates if
        the given variable type was changed by command.

        @param var the variable type to check
        @param is2013 the target module's-generation
        @return true if a poll is required to get the new status-value       
        """
        # Regulator set-points will send status-messages on every change (all firmware versions)
        if Var.to_set_point_id(var) != -1:
            return False
        
        # Thresholds since 170206 will send status-messages on every change
        if is2013 and (Var.to_thrs_register_id(var != -1)):
            return False

        # Others:
        # - Variables before 170206 will never send any status-messages
        # - Variables since 170206 only send status-messages on "big" changes
        # - Thresholds before 170206 will never send any status-messages
        # - S0-inputs only send status-messages on "big" changes
        # (all "big changes" cases force us to poll the status to get faster updates)        
        return True

    @staticmethod
    def should_poll_status_after_regulator_lock(sw_age, lock_state):
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


# Helper list to get var by numeric id.
Var._var_id_to_var = [Var.VAR1ORTVAR, Var.VAR2ORR1VAR, Var.VAR3ORR2VAR,
                      Var.VAR4, Var.VAR5, Var.VAR6, Var.VAR7, Var.VAR8,
                      Var.VAR9, Var.VAR10, Var.VAR11, Var.VAR12]

# Helper list to get set-point var by numeric id.
Var._set_point_id_to_var = [Var.R1VARSETPOINT, Var.R2VARSETPOINT]

# Helper list to get threshold var by numeric id.
Var._thrs_id_to_var = [[Var.THRS1, Var.THRS2, Var.THRS3, Var.THRS4, Var.THRS5],
                       [Var.THRS2_1, Var.THRS2_2, Var.THRS2_3, Var.THRS2_4],
                       [Var.THRS3_1, Var.THRS3_2, Var.THRS3_3, Var.THRS3_4],
                       [Var.THRS4_1, Var.THRS4_2, Var.THRS4_3, Var.THRS4_4]]

# Helper list to get S0-input var by numeric id.
Var._s0_id_to_var = [Var.S0INPUT1, Var.S0INPUT2, Var.S0INPUT3, Var.S0INPUT4]




class VarUnit(Enum):
    """
    Measurement units used with LCN variables.
    """
    NATIVE = auto()         # LCN internal representation (0 = -100�C for absolute values)
    CELSIUS = auto()
    KELVIN = auto()
    FAHRENHEIT = auto()
    LUX_T = auto()
    LUX_I = auto()
    METERPERSECOND = auto() # Used for LCN-WIH wind speed
    PERCENT = auto()        # Used for humidity
    PPM = auto()            # Used by CO2 sensor
    VOLT = auto()
    AMPERE = auto()
    DEGREE = auto()         #Used for angles,

    @staticmethod
    def parse(input):
        input = input.upper()
        if input == 'LCN':
            return VarUnit.NATIVE
        elif input in ['CELSIUS', '\u00b0CELSIUS', '\u00b0C']:
            return VarUnit.CELSIUS
        elif input in ['KELVIN', '\u00b0KELVIN', '\u00b0K']:
            return VarUnit.KELVIN
        elif input in ['FAHRENHEIT', '\u00b0FAHRENHEIT', '\u00b0F']:
            return VarUnit.FAHRENHEIT
        elif input in ['LUX_T', 'LX_T']:
            return VarUnit.LUX_T
        elif input in ['LUX', 'LX']:
            return VarUnit.LUX_I
        elif input == 'M/S':
            return VarUnit.METERPERSECOND
        elif input == '%':
            return VarUnit.PERCENT
        elif input == 'PPM':
            return VarUnit.PPM
        elif input in ['VOLT', 'V']:
            return VarUnit.VOLT
        elif input in ['AMPERE', 'AMP', 'A']:
            return VarUnit.AMPERE
        elif input in ['DEGREE', '\u00b0']:
            return VarUnit.DEGREE
        else:
            raise ValueError('Bad input.')
        

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

    def is_lock_regulator(self):
        return (self.native_value & 0x8000) != 0

    @staticmethod
    def from_var_unit(v, unit, abs):
        """
        Creates a variable value from any input.

        @param v the input value
        @param unit the input value's unit
        @param abs true for absolute values (relative values are used to add/subtract from other VarValues)
        @return the variable value (never null)        
        """
        if unit == VarUnit.NATIVE:
            return VarValue.from_native(int(v))
        elif unit == VarUnit.CELSIUS:
            return VarValue.from_celsius(v, abs)
        elif unit == VarUnit.KELVIN:
            return VarValue.from_kelvin(v, abs)
        elif unit == VarUnit.FAHRENHEIT:
            return VarValue.from_fahrenheit(v, abs)
        elif unit == VarUnit.LUX_T:
            return VarValue.from_lux_t(v)
        elif unit == VarUnit.LUX_I:
            return VarValue.from_lux_i(v)
        elif unit == VarUnit.METERPERSECOND:
            return VarValue.from_meters_per_second(v)
        elif unit == VarUnit.PERCENT:
            return VarValue.from_percent(v)
        elif unit == VarUnit.PPM:
            return VarValue.from_ppm(v)
        elif unit == VarUnit.VOLT:
            return VarValue.from_volt(v)
        elif unit == VarUnit.AMPERE:
            return VarValue.from_kelvin(v)
        elif unit == VarUnit.DEGREE:
            return VarValue.from_degree(v)
        else:
            raise ValueError('Wrong unit.')

    @staticmethod
    def from_native(n):
        """
        Creates a variable value from native input.

        @param n the input value
        @return the variable value (never null)
        """
        return VarValue(n)

    @staticmethod
    def from_celsius(c, abs = True):
        """
        Creates a variable value from \u00b0C input.

        @param c the input value
        @param abs true for absolute values (relative values are used to add/subtract from other VarValues)
        @return the variable value (never null)        
        """
        n = int(round(c * 10))
        return VarValue(n + 1000 if abs else n)
    
    @staticmethod
    def from_kelvin(k, abs = True):
        """
        Creates a variable value from \u00b0K input.

        @param k the input value
        @param abs true for absolute values (relative values are used to add/subtract from other VarValues)
        @return the variable value (never null)        
        """
        if abs:
            k -= 273.15
        
        n = int(round(k * 10))
        return VarValue(n + 1000 if abs else n)

    @staticmethod
    def from_fahrenheit(f, abs = True):
        """
        Creates a variable value from \u00b0F input.

        @param f the input value
        @param abs true for absolute values (relative values are used to add/subtract from other VarValues)
        @return the variable value (never null)
        """
        if abs:
            f -= 32
        
        n = int(round(f / 0.18))
        return VarValue(n + 1000 if abs else n)
    
    
    @staticmethod
    def from_lux_t(l):
        """
        Creates a variable value from lx input.
        Target must be connected to T-port.

        @param l the input value
        @return the variable value (never null)
        """
        return VarValue(int(round(math.log(l) - 1.689646994) / 0.010380664))
    
    @staticmethod
    def from_lux_i(l):
        """
        Creates a variable value from lx input.
        Target must be connected to I-port.

        @param l the input value
        @return the variable value (never null)
        """
        return VarValue(int(round(math.log(l) * 100)))
    
    @staticmethod
    def from_percent(p):
        """
        Creates a variable value from % input.

        @param p the input value
        @return the variable value (never null)        
        """
        return VarValue(int(round(p)))
    
    @staticmethod
    def from_ppm(p):
        """
        Creates a variable value from ppm input.
        Used for CO2 sensors.

        @param p the input value
        @return the variable value (never null)       
        """
        return VarValue(int(round(p)))
    
    @staticmethod
    def from_meters_per_second(ms):
        """
        Creates a variable value from m/s input.
        Used for LCN-WIH wind speed.

        @param ms the input value
        @return the variable value (never null)
        """
        return VarValue(int(round(ms * 10)))
    
    @staticmethod
    def from_volt(v):
        """
        Creates a variable value from V input.

        @param v the input value
        @return the variable value (never null)        
        """
        return VarValue(int(round(v * 400)))
    
    @staticmethod
    def from_ampere(a):
        """
        Creates a variable value from A input.

        @param a the input value
        @return the variable value (never null)       
        """
        return VarValue(int(round(a * 100)))
    
    @staticmethod
    def from_degree(d, abs = True):
        """
        Creates a variable value from \u00b0 (angle) input.

        @param d the input value
        @param abs true for absolute values (relative values are used to add/subtract from other VarValues)
        @return the variable value (never null)
        """
        n = int(round(d * 10))
        return VarValue(n + 1000 if abs else n)
    
    def to_var_unit(self, unit, is_lockable_regulator_source):
        v = VarValue(self.native_value & 0x7fff if is_lockable_regulator_source else self.native_value)
    
        if unit == VarUnit.NATIVE:
            return v.to_native()
        elif unit == VarUnit.CELSIUS:
            return v.to_celsius()
        elif unit == VarUnit.KELVIN:
            return v.to_kelvin()
        elif unit == VarUnit.FAHRENHEIT:
            return v.to_fahrenheit()
        elif unit == VarUnit.LUX_T:
            return v.to_lux_t()
        elif unit == VarUnit.LUX_I:
            return v.to_lux_i()
        elif unit == VarUnit.METERPERSECOND:
            return v.to_meters_per_second()
        elif unit == VarUnit.PERCENT:
            return v.to_percent()
        elif unit == VarUnit.PPM:
            return v.to_ppm()
        elif unit == VarUnit.VOLT:
            return v.to_volt()
        elif unit == VarUnit.AMPERE:
            return v.to_ampere()
        elif unit == VarUnit.DEGREE:
            return v.to_degree()
        else:
            raise ValueError('Wrong unit.')
    
    def to_native(self):
        """
        Converts to native value.

        @return the converted value
        """
        return self.native_value
    
    def to_celsius(self):
        """
        Converts to \u00b0C value.
        
        @return the converted value
        """
        return (self.native_value - 1000) / 10.
    
    def to_kelvin(self):
        """
        Converts to \u00b0K value.
        
        @return the converted value
        """
        return (self.native_value - 1000) / 10. + 273.15
    
    def to_fahrenheit(self):
        """
        Converts to \u00b0F value.
        
        @return the converted value
        """
        return (self.native_value - 1000) * 0.18 + 32.
    
    def to_lux_t(self):
        """
        Converts to lx value.
        Source must be connected to T-port.
        
        @return the converted value
        """
        return math.exp(0.010380664 * self.native_value + 1.689646994)
    
    def to_lux_i(self):
        """
        Converts to lx value.
        Source must be connected to I-port.
        
        @return the converted value
        """
        return math.exp(self.native_value / 100)
    
    def to_percent(self):
        """
        Converts to % value.

        @return the converted value
        """
        return self.native_value

    def to_ppm(self):
        """
        Converts to ppm value.

        @return the converted value
        """
        return self.native_value
    
    def to_meters_per_sec(self):
        """
        Converts to m/s value.

        @return the converted value
        """
        return self.native_value / 10.
    
    def to_volt(self):
        """
        Converts to V value.

        @return the converted value
        """
        return self.native_value / 400.
    
    def to_ampere(self):
        """
        Converts to A value.

        @return the converted value
        """
        return self.native_value / 100.
    
    def to_degree(self):
        """
        Converts to \u00b0 value.

        @return the converted value
        """
        return (self.native_value - 1000) / 10.
    
    def to_var_unit_string(self, unit, is_lockable_regulator_source, use_lcn_special_values):
        if use_lcn_special_values and (self.native_value == 0xffff):    # No value
            ret = '---'
        elif use_lcn_special_values and ((self.native_value & 0xff00) == 0x8100):   # Undefined
            ret = '---'
        elif use_lcn_special_values and ((self.native_value & 0xff00) == 0x7f00):   # Defective
            ret = '!!!'
        else:
            var = VarValue((self.native_value & 0x7ff) if is_lockable_regulator_source else self.native_value)
            if unit == VarUnit.NATIVE:
                ret = '{:.0f}'.format(var.to_native())
            elif unit == VarUnit.CELSIUS:
                ret = '{:.01f}'.format(var.to_celsius())
            elif unit == VarUnit.KELVIN:
                ret = '{:.01f}'.format(var.to_kelvin())
            elif unit == VarUnit.FAHRENHEIT:
                ret = '{:.01f}'.format(var.to_fahrenheit())
            elif unit == VarUnit.LUX_T:
                if (var.to_native() > 1152):    # Max. value the HW can do
                    ret = '---'
                else:
                    ret = '{:.0f}'.format(var.to_lux_t())
            elif unit == VarUnit.LUX_I:
                if (var.to_native() > 1152):    # Max. value the HW can do
                    ret = '---'
                else:
                    ret = '{:.0f}'.format(var.to_lux_i())
            elif unit == VarUnit.METERPERSECOND:
                ret = '{:.0f}'.format(var.to_meters_per_sec())
            elif unit == VarUnit.PERCENT:
                ret = '{:.0f}'.format(var.to_percent())
            elif unit == VarUnit.PPM:
                ret = '{:.0f}'.format(var.to_ppm())
            elif unit == VarUnit.VOLT:
                ret = '{:.0f}'.format(var.to_volt())
            elif unit == VarUnit.AMPERE:
                ret = '{:.0f}'.format(var.to_ampere())
            elif unit == VarUnit.DEGREE:
                ret = '{:.0f}'.format(var.to_degree())
            else:
                raise ValueError('Wrong unit.')

        # handle locked regulators
        if is_lockable_regulator_source and self.is_lock_regulator():
            ret = '({:s})'.format(ret)

        return ret
    

class LedStatus(Enum):
    """
    Possible states for LCN LEDs
    """
    OFF = 'A'
    ON = 'E'
    BLINK = 'B'
    FLICKER = 'F'
    

class LogicOpStatus(Enum):
    """
    Possible states for LCN logic-operations.
    """
    NOT = 'N'
    OR = "T"     # Note: Actually not correct since AND won't be OR also
    AND = 'V'
    

class TimeUnit(Enum):
    """
    Time units used for several LCN commands.
    """
    SECONDS = 'S'
    MINUTES = 'M'
    HOURS = 'H'
    DAYS = 'D'
    
    @staticmethod
    def parse(input):
        """
        Parses the given input into a time unit.
        It supports several alternative terms.

        @param input the text to parse
        @return the parsed {@link TimeUnit}
        """
        input = input.upper()
        if input in ['SECONDS', 'SECOND', 'SEC', 'S']:
            return TimeUnit.SECONDS
        elif input in ['MINUTES', 'MINUTE', 'MIN', 'M']:
            return TimeUnit.MINUTES
        elif input in ['HOURS', 'HOUR', 'H']:
            return TimeUnit.HOURS
        elif input in ['DAYS', 'DAY', 'D']:
            return TimeUnit.DAYS
        else:
            raise ValueError('Bad time unit input.')
        

class RelayStateModifier(Enum):
    """
    Relay-state modifiers used in LCN commands.
    """
    ON = '1'
    OFF = '0'
    TOGGLE = 'U'
    NOCHANGE = '-'
    

class RelVarRef(Enum):
    """
    Value-reference for relative LCN variable commands.
    """
    CURRENT = auto()
    PROG = auto()       # Programmed value (LCN-PRO). Relevant for set-points and thresholds.
    

class SendKeyCommand(Enum):
    """
    Command types used when sending LCN keys.
    """
    HIT = 'K'
    MAKE = 'L'
    BREAK = 'O'
    DONTSEND = '-'
    
    
class KeyLockStateModifier(Enum):
    """
    Key-lock modifiers used in LCN commands.
    """
    ON = '1'
    OFF = '0'
    TOGGLE = 'U'
    NOCHANGE = '-'
