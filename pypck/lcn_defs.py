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

import math
import re
from itertools import product

from aenum import Enum, auto

LCN_ENCODING = 'utf-8'
PATTERN_SPLIT_PORT_PIN = re.compile(r'(?P<port>[a-zA-Z]+)(?P<pin>\d+)')


def split_port_pin(portpin):
    """Splits the port and the pin from the given input string.

    :param    str    portpin:    Input string
    """
    res = PATTERN_SPLIT_PORT_PIN.findall(portpin)
    return res[0][0], int(res[0][1])


class OutputPort(Enum):
    """Output port of LCN module.
    """
    OUTPUT1 = 0
    OUTPUT2 = 1
    OUTPUT3 = 2
    OUTPUT4 = 3


class RelayPort(Enum):
    """Relay port of LCN module.
    """
    RELAY1 = 0
    RELAY2 = 1
    RELAY3 = 2
    RELAY4 = 3
    RELAY5 = 4
    RELAY6 = 5
    RELAY7 = 6
    RELAY8 = 7

    MOTORONOFF1 = 0
    MOTORUPDOWN1 = 1
    MOTORONOFF2 = 2
    MOTORUPDOWN2 = 3
    MOTORONOFF3 = 4
    MOTORUPDOWN3 = 5
    MOTORONOFF4 = 6
    MOTORUPDOWN4 = 7


class MotorPort(Enum):
    """Motor ports of LCN module.
    """
    MOTOR1 = 0
    MOTOR2 = 1
    MOTOR3 = 2
    MOTOR4 = 3


class LedPort(Enum):
    """LED port of LCN module.
    """
    LED1 = 0
    LED2 = 1
    LED3 = 2
    LED4 = 3
    LED5 = 4
    LED6 = 5
    LED7 = 6
    LED8 = 7
    LED9 = 8
    LED10 = 9
    LED11 = 10
    LED12 = 11


class LogicOpPort(Enum):
    """Logic Operation port of LCN module
    """
    LOGICOP1 = 0
    LOGICOP2 = 1
    LOGICOP3 = 2
    LOGICOP4 = 3


class BinSensorPort(Enum):
    """Binary sensor port of LCN module.
    """
    BINSENSOR1 = 0
    BINSENSOR2 = 1
    BINSENSOR3 = 2
    BINSENSOR4 = 3
    BINSENSOR5 = 4
    BINSENSOR6 = 5
    BINSENSOR7 = 6
    BINSENSOR8 = 7


# Keys
# pylint: disable=invalid-name
Key = Enum('Key', ' '.join(['{:s}{:d}'.format(t[0], t[1]) for t in
                            product(['A', 'B', 'C', 'D'], range(1, 9))]),
           module=__name__)


class OutputPortDimMode(Enum):
    """LCN dimming mode.
    If solely modules with firmware 170206 or newer are present, LCN-PRO
    automatically programs STEPS200.
    Otherwise the default is STEPS50.
    Since LCN-PCHK doesn't know the current mode, it must explicitly be set.
    """
    STEPS50 = auto()  # 0..50 dimming steps (all LCN module generations)
    STEPS200 = auto()  # 0..200 dimming steps (since 170206)


class OutputPortStatusMode(Enum):
    """
    Tells LCN-PCHK how to format output-port status-messages.
    PERCENT: allows to show the status in half-percent steps (e.g. "10.5").
    NATIVE: is completely backward compatible and there are no restrictions
    concerning the LCN module generations. It requires LCN-PCHK 2.3 or higher
    though.
    """
    PERCENT = auto()  # Default (compatible with all versions of LCN-PCHK)
    NATIVE = auto()  # 0..200 steps (since LCN-PCHK 2.3)


def time_to_ramp_value(time_msec):
    """
    Converts the given time into an LCN ramp value.

    :param    int    time_msec:    The time in milliseconds.

    :returns: The (LCN-internal) ramp value (0..250).
    :rtype: int
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
    return int(ret)


def ramp_value_to_time(ramp_value):
    """Converts the given LCN ramp value into a time.

    :param    int    ramp_value:    The LCN ramp value (0..250).

    :returns: The ramp time in milliseconds.
    :rtype: int
    """
    if not 0 <= ramp_value <= 250:
        raise ValueError('Ramp value has to be in range 0..250.')

    if ramp_value < 10:
        times = [250, 500, 660, 1000, 1400, 2000, 3000, 4000, 5000, 6000]
        t = times[ramp_value]
    else:
        t = int(((ramp_value - 10) * 2 + 6) * 1000)
    return t


class Var(Enum):
    """LCN variable types.
    """
    UNKNOWN = -1  # Used if the real type is not known (yet)
    VAR1ORTVAR = 0
    TVAR = 0
    VAR1 = 0
    VAR2ORR1VAR = 1
    R1VAR = 1
    VAR2 = 1
    VAR3ORR2VAR = 2
    R2VAR = 2
    VAR3 = 2
    VAR4 = 3
    VAR5 = 4
    VAR6 = 5
    VAR7 = 6
    VAR8 = 7
    VAR9 = 8
    VAR10 = 9
    VAR11 = 10
    VAR12 = 11  # Since 170206
    R1VARSETPOINT = auto()
    R2VARSETPOINT = auto()  # Set-points for regulators
    THRS1 = auto()
    THRS2 = auto()
    THRS3 = auto()
    THRS4 = auto()
    THRS5 = auto()  # Register 1 (THRS5 only before 170206)
    THRS2_1 = auto()
    THRS2_2 = auto()
    THRS2_3 = auto()
    THRS2_4 = auto()  # Register 2 (since 2012)
    THRS3_1 = auto()
    THRS3_2 = auto()
    THRS3_3 = auto()
    THRS3_4 = auto()  # Register 3 (since 2012)
    THRS4_1 = auto()
    THRS4_2 = auto()
    THRS4_3 = auto()
    THRS4_4 = auto()  # Register 4 (since 2012)
    S0INPUT1 = auto()
    S0INPUT2 = auto()
    S0INPUT3 = auto()
    S0INPUT4 = auto()  # LCN-BU4LJVarValue

    @staticmethod
    def var_id_to_var(var_id):
        """
        Translates a given id into a variable type.

        :param    int    varId:    The variable id (0..11)

        :returns: The translated variable enum.
        :rtype: Var
        """
        if (var_id < 0) or (var_id >= len(Var.variables)):
            raise ValueError('Bad var_id.')
        return Var.variables[var_id]

    @staticmethod
    def set_point_id_to_var(set_point_id):
        """
        Translates a given id into a LCN set-point variable type.

        :param     int    set_point_id:    Set-point id 0..1

        :return: The translated var
        :rtype:  Var
        """
        if (set_point_id < 0) or (set_point_id >=
                                  len(Var.set_points)):
            raise ValueError('Bad set_point_id.')
        return Var.set_points[set_point_id]

    @staticmethod
    def thrs_id_to_var(register_id, thrs_id):
        """
        Translates given ids into a LCN threshold variable type.

        :param    int    register_id:    Register id 0..3
        :param    int    thrs_id:        Threshold id 0..4 for register 0,
                                                      0..3 for registers 1..3

        :return: The translated var
        :rtype:    Var
        """
        if (register_id < 0) or (register_id >= len(Var.thresholds)) or\
                (thrs_id < 0) or (thrs_id >= (5 if (register_id == 0) else 4)):
            raise ValueError('Bad register_id and/or thrs_id.')
        return Var.thresholds[register_id][thrs_id]

    @staticmethod
    def s0_id_to_var(s0_id):
        """
        Translates a given id into a LCN S0-input variable type.

        :param     int    s0_id:     S0 id 0..3

        :return:    The translated var
        :rtype:     Var
        """
        if (s0_id < 0) or (s0_id >= len(Var.s0s)):
            raise ValueError('Bad s0_id.')
        return Var._s0_id_to_var_array[s0_id]

    @staticmethod
    def to_var_id(var):
        """
        Translates a given variable type into a variable id.

        :param     Var    var:    The variable type to translate

        :return:     Variable id 0..11 or -1 if wrong type
        :rtype:    int
        """
        if var == Var.VAR1ORTVAR:
            var_id = 0
        elif var == Var.VAR2ORR1VAR:
            var_id = 1
        elif var == Var.VAR3ORR2VAR:
            var_id = 2
        elif var == Var.VAR4:
            var_id = 3
        elif var == Var.VAR5:
            var_id = 4
        elif var == Var.VAR6:
            var_id = 5
        elif var == Var.VAR7:
            var_id = 6
        elif var == Var.VAR8:
            var_id = 7
        elif var == Var.VAR9:
            var_id = 8
        elif var == Var.VAR10:
            var_id = 9
        elif var == Var.VAR11:
            var_id = 10
        elif var == Var.VAR12:
            var_id = 11
        else:
            var_id = -1
        return var_id

    @staticmethod
    def to_set_point_id(var):
        """
        Translates a given variable type into a set-point id.

        :param     Var    var:     The variable type to translate

        :return:    Variable id 0..1 or -1 if wrong type
        :rtype:    int
        """
        if var == Var.R1VARSETPOINT:
            set_point_id = 0
        elif var == Var.R2VARSETPOINT:
            set_point_id = 1
        else:
            set_point_id = -1
        return set_point_id

    @staticmethod
    def to_thrs_register_id(var):
        """
        Translates a given variable type into a threshold register id.

        :param    Var    var:    The variable type to translate

        :return:    Register id 0..3 or -1 if wrong type
        :rtype:    int
        """
        if var in [Var.THRS1, Var.THRS2, Var.THRS3, Var.THRS4, Var.THRS5]:
            thrs_register_id = 0
        elif var in [Var.THRS2_1, Var.THRS2_2, Var.THRS2_3, Var.THRS2_4]:
            thrs_register_id = 1
        elif var in [Var.THRS3_1, Var.THRS3_2, Var.THRS3_3, Var.THRS3_4]:
            thrs_register_id = 2
        elif var in [Var.THRS4_1, Var.THRS4_2, Var.THRS4_3, Var.THRS4_4]:
            thrs_register_id = 3
        else:
            thrs_register_id = -1
        return thrs_register_id

    @staticmethod
    def to_thrs_id(var):
        """
        Translates a given variable type into a threshold id.

        :param    Var    var:    The variable type to translate

        :return:    Threshold id 0..4 or -1 if wrong type
        :rtype:    int
        """
        if var in [Var.THRS1, Var.THRS2_1, Var.THRS3_1, Var.THRS4_1]:
            thrs_id = 0
        elif var in [Var.THRS2, Var.THRS2_2, Var.THRS3_2, Var.THRS4_2]:
            thrs_id = 1
        elif var in [Var.THRS3, Var.THRS2_3, Var.THRS3_3, Var.THRS4_3]:
            thrs_id = 2
        elif var in [Var.THRS4, Var.THRS2_4, Var.THRS3_4, Var.THRS4_4]:
            thrs_id = 3
        elif var == Var.THRS5:
            thrs_id = 4
        else:
            thrs_id = -1
        return thrs_id

    @staticmethod
    def to_s0_id(var):
        """
        Translates a given variable type into an S0-input id.

        :param    Var    var:    The variable type to translate

        :return:    S0 id 0..3 or -1 if wrong type
        :rtype:    int
        """
        if var == Var.S0INPUT1:
            s0_id = 0
        elif var == Var.S0INPUT2:
            s0_id = 1
        elif var == Var.S0INPUT3:
            s0_id = 2
        elif var == Var.S0INPUT4:
            s0_id = 3
        else:
            s0_id = -1
        return s0_id

    @staticmethod
    def is_lockable_regulator_source(var):
        """
        Checks if the the given variable type is lockable.

        :param    Var    var:    The variable type to check

        :return:    True if lockable, otherwise False
        :rtype:    bool
        """
        return var in [Var.R1VARSETPOINT, Var.R2VARSETPOINT]

    @staticmethod
    def use_lcn_special_values(var):
        """
        Checks if the given variable type uses special values.
        Examples for special values: 'No value yet', 'sensor defective' etc.

        :param    Var    var:    The variable type to check

        :return:    True if special values are in use, otherwise False
        :rtype:    bool
        """
        return var not in [Var.S0INPU1, Var.S0INPUT2, Var.S0INPUT3,
                           Var.S0INPUT4]

    @staticmethod
    def has_type_in_response(var, sw_age):
        """
        Module-generation check.
        Checks if the given variable type would receive a typed response if
        its status was requested.

        :param    Var    var:    The variable type to check
        :param    int    swAge:  The target LCN-modules firmware version

        :return:    True if a response would contain the variable's type,
                    otherwise False
        :rtype:    bool
        """
        if sw_age < 0x170206:
            if var in [Var.VAR1ORTVAR, Var.VAR2ORR1VAR, Var.VAR3ORR2VAR,
                       Var.R1VARSETPOINT, Var.R2VARSETPOINT]:
                return False
        return True

    @staticmethod
    def is_event_based(var, sw_age):
        """
        Module-generation check.
        Checks if the given variable type automatically sends status-updates
        on value-change. It must be polled otherwise.

        :param    Var    var:    The variable type to check
        :param    int    swAge:  The target LCN-module's firmware version

        :return:    True if the LCN module supports automatic status-messages
                    for this var, otherwise False
        :rtype:    bool
        """
        if (Var.to_set_point_id(var) != -1) or (Var.to_s0_id(var) != -1):
            return True
        return sw_age >= 0x170206

    @staticmethod
    def should_poll_status_after_command(var, is2013):
        """
        Module-generation check.
        Checks if the target LCN module would automatically send status-updates
        if the given variable type was changed by command.

        :param    Var    var:    The variable type to check
        :param    bool   is2013: The target module's-generation

        :return:    True if a poll is required to get the new status-value,
                    otherwise False
        :rtype:    bool
        """
        # Regulator set-points will send status-messages on every change
        # (all firmware versions)
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
        # (all "big changes" cases force us to poll the status to get faster
        # updates)
        return True

    @staticmethod
    def should_poll_status_after_regulator_lock(sw_age, lock_state):
        """
        Module-generation check.
        Checks if the target LCN module would automatically send status-updates
        if the given regulator's lock-state was changed by command.

        :param    int       swAge: The target LCN-module's firmware version
        :param    int   lockState: The lock-state sent via command

        :return:    True if a poll is required to get the new status-value,
                    otherwise False
        :rtype:    bool
        """
        # LCN modules before 170206 will send an automatic status-message for
        # "lock", but not for "unlock"
        return (not lock_state) and (sw_age < 0x170206)


# Helper list to get var by numeric id.
Var.variables = [Var.VAR1ORTVAR, Var.VAR2ORR1VAR, Var.VAR3ORR2VAR,
                 Var.VAR4, Var.VAR5, Var.VAR6, Var.VAR7, Var.VAR8,
                 Var.VAR9, Var.VAR10, Var.VAR11, Var.VAR12]

# Helper list to get set-point var by numeric id.
Var.set_points = [Var.R1VARSETPOINT, Var.R2VARSETPOINT]

# Helper list to get threshold var by numeric id.
Var.thresholds = [[Var.THRS1, Var.THRS2, Var.THRS3, Var.THRS4, Var.THRS5],
                  [Var.THRS2_1, Var.THRS2_2, Var.THRS2_3, Var.THRS2_4],
                  [Var.THRS3_1, Var.THRS3_2, Var.THRS3_3, Var.THRS3_4],
                  [Var.THRS4_1, Var.THRS4_2, Var.THRS4_3, Var.THRS4_4]]

# Helper list to get S0-input var by numeric id.
Var.s0s = [Var.S0INPUT1, Var.S0INPUT2, Var.S0INPUT3, Var.S0INPUT4]


class VarUnit(Enum):
    """Measurement units used with LCN variables.
    """
    NATIVE = ''  # LCN internal representation (0 = -100C for absolute values)
    CELSIUS = u'\u00b0C'
    KELVIN = u'\u00b0K'
    FAHRENHEIT = u'\u00b0F'
    LUX_T = 'Lux_T'
    LUX_I = 'Lux_I'
    METERPERSECOND = 'm/s'  # Used for LCN-WIH wind speed
    PERCENT = '%'  # Used for humidity
    PPM = 'ppm'  # Used by CO2 sensor
    VOLT = 'V'
    AMPERE = 'A'
    DEGREE = u'\u00b0'  # Used for angles,

    @staticmethod
    def parse(unit):
        """Parse the given unit string and return VarUnit.

        :param    str    unit:    The input unit
        """
        unit = unit.upper()
        if unit in ['', 'NATIVE', 'LCN']:
            var_unit = VarUnit.NATIVE
        elif unit in ['CELSIUS', u'\u00b0CELSIUS', u'\u00b0C']:
            var_unit = VarUnit.CELSIUS
        elif unit in ['KELVIN', u'\u00b0KELVIN', u'\u00b0K']:
            var_unit = VarUnit.KELVIN
        elif unit in ['FAHRENHEIT', u'\u00b0FAHRENHEIT', u'\u00b0F']:
            var_unit = VarUnit.FAHRENHEIT
        elif unit in ['LUX_T', 'LX_T']:
            var_unit = VarUnit.LUX_T
        elif unit in ['LUX', 'LX']:
            var_unit = VarUnit.LUX_I
        elif unit == 'M/S':
            var_unit = VarUnit.METERPERSECOND
        elif unit in ['%', 'PERCENT']:
            var_unit = VarUnit.PERCENT
        elif unit == 'PPM':
            var_unit = VarUnit.PPM
        elif unit in ['VOLT', 'V']:
            var_unit = VarUnit.VOLT
        elif unit in ['AMPERE', 'AMP', 'A']:
            var_unit = VarUnit.AMPERE
        elif unit in ['DEGREE', u'\u00b0']:
            var_unit = VarUnit.DEGREE
        else:
            raise ValueError('Bad input unit.')
        return var_unit


class VarValue():
    """A value of an LCN variable.

    It internally stores the native LCN value and allows to convert from/into
    other units. Some conversions allow to specify whether the source value is
    absolute or relative. Relative values are used to create varvalues that
    can be added/subtracted from other (absolute) varvalues.

    :param    int    native_value:    The native value
    """

    def __init__(self, native_value):
        """Constructor with native LCN value.
        """
        self.native_value = native_value

    def is_locked_regulator(self):
        """Return if regulator is locked.
        """
        return (self.native_value & 0x8000) != 0

    @staticmethod
    def from_var_unit(v, unit, is_abs):
        """Creates a variable value from any input.

        :param    float    v:       The input value
        :param    VarUnit  unit:    The input value's unit
        :param    bool     is_abs:  True for absolute values (relative values
                                    are used to add/subtract from other
                                    VarValues), otherwise False

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        if unit == VarUnit.NATIVE:
            var_value = VarValue.from_native(int(v))
        elif unit == VarUnit.CELSIUS:
            var_value = VarValue.from_celsius(v, is_abs)
        elif unit == VarUnit.KELVIN:
            var_value = VarValue.from_kelvin(v, is_abs)
        elif unit == VarUnit.FAHRENHEIT:
            var_value = VarValue.from_fahrenheit(v, is_abs)
        elif unit == VarUnit.LUX_T:
            var_value = VarValue.from_lux_t(v)
        elif unit == VarUnit.LUX_I:
            var_value = VarValue.from_lux_i(v)
        elif unit == VarUnit.METERPERSECOND:
            var_value = VarValue.from_meters_per_second(v)
        elif unit == VarUnit.PERCENT:
            var_value = VarValue.from_percent(v)
        elif unit == VarUnit.PPM:
            var_value = VarValue.from_ppm(v)
        elif unit == VarUnit.VOLT:
            var_value = VarValue.from_volt(v)
        elif unit == VarUnit.AMPERE:
            var_value = VarValue.from_kelvin(v)
        elif unit == VarUnit.DEGREE:
            var_value = VarValue.from_degree(v)
        else:
            raise ValueError('Wrong unit.')
        return var_value

    @staticmethod
    def from_native(n):
        """Creates a variable value from native input.

        :param    int    n:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(n)

    @staticmethod
    def from_celsius(c, is_abs=True):
        """Creates a variable value from Celsius input.

        :param    float    c:        The input value
        :param    bool     is_abs:   True for absolute values (relative values
                                     are used to add/subtract from other
                                     VarValues), otherwise False

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        n = int(round(c * 10))
        return VarValue(n + 1000 if is_abs else n)

    @staticmethod
    def from_kelvin(k, is_abs=True):
        """Creates a variable value from Kelvin input.

        :param    float    k:        The input value
        :param    bool     is_abs:   True for absolute values (relative values
                                     are used to add/subtract from other
                                     VarValues), otherwise False

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        if is_abs:
            k -= 273.15

        n = int(round(k * 10))
        return VarValue(n + 1000 if is_abs else n)

    @staticmethod
    def from_fahrenheit(f, is_abs=True):
        """Creates a variable value from Fahrenheit input.

        :param    float    f:        The input value
        :param    bool     is_abs:   True for absolute values (relative values
                                     are used to add/subtract from other
                                     VarValues), otherwise False

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        if is_abs:
            f -= 32

        n = int(round(f / 0.18))
        return VarValue(n + 1000 if is_abs else n)

    @staticmethod
    def from_lux_t(l):
        """Creates a variable value from lx input.
        Target must be connected to T-port.

        :param    float    l:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(math.log(l) - 1.689646994) / 0.010380664))

    @staticmethod
    def from_lux_i(l):
        """Creates a variable value from lx input.
        Target must be connected to I-port.

        :param    float    l:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(math.log(l) * 100)))

    @staticmethod
    def from_percent(p):
        """Creates a variable value from % input.

        :param    float    p:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(p)))

    @staticmethod
    def from_ppm(p):
        """Creates a variable value from ppm input.
        Used for CO2 sensors.

        :param    float    p:   The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(p)))

    @staticmethod
    def from_meters_per_second(ms):
        """Creates a variable value from m/s input.
        Used for LCN-WIH wind speed.

        :param    float    ms:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(ms * 10)))

    @staticmethod
    def from_volt(v):
        """Creates a variable value from V input.

        :param    float    v:    The input value

        :return:    The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(v * 400)))

    @staticmethod
    def from_ampere(a):
        """Creates a variable value from A input.

        :param    float    a:    The input value

        :return: The variable value (never null)
        :rtype:    VarValue
        """
        return VarValue(int(round(a * 100)))

    @staticmethod
    def from_degree(d, is_abs=True):
        """Creates a variable value from degree (angle) input.

        :param    float    d:        The input value
        :param    bool     is_abs:   True for absolute values (relative values
                                     are used to add/subtract from other
                                     VarValues), otherwise False

        :return:    The variable value (never null)
        :rtype:     VarValue
        """
        n = int(round(d * 10))
        return VarValue(n + 1000 if is_abs else n)

    def to_var_unit(self, unit, is_lockable_regulator_source=False):
        """Converts the given unit to a VarValue.

        :param    VarUnit    unit:    The variable unit
        :param    bool       is_lockable_regulator_source:  Is lockable source

        :return:    The variable value
        :rtype:     VarValue
        """
        v = VarValue(self.native_value & 0x7fff if is_lockable_regulator_source
                     else self.native_value)

        if unit == VarUnit.NATIVE:
            var_value = v.to_native()
        elif unit == VarUnit.CELSIUS:
            var_value = v.to_celsius()
        elif unit == VarUnit.KELVIN:
            var_value = v.to_kelvin()
        elif unit == VarUnit.FAHRENHEIT:
            var_value = v.to_fahrenheit()
        elif unit == VarUnit.LUX_T:
            var_value = v.to_lux_t()
        elif unit == VarUnit.LUX_I:
            var_value = v.to_lux_i()
        elif unit == VarUnit.METERPERSECOND:
            var_value = v.to_meters_per_second()
        elif unit == VarUnit.PERCENT:
            var_value = v.to_percent()
        elif unit == VarUnit.PPM:
            var_value = v.to_ppm()
        elif unit == VarUnit.VOLT:
            var_value = v.to_volt()
        elif unit == VarUnit.AMPERE:
            var_value = v.to_ampere()
        elif unit == VarUnit.DEGREE:
            var_value = v.to_degree()
        else:
            raise ValueError('Wrong unit.')
        return var_value

    def to_native(self):
        """Converts to native value.

        :return:    The converted value
        :rtype:    int
        """
        return self.native_value

    def to_celsius(self):
        """Converts to Celsius value.

        :return:    The converted value
        :rtype:    float
        """
        return (self.native_value - 1000) / 10.

    def to_kelvin(self):
        """Converts to Kelvin value.

        :return:    The converted value
        :rtype:    float
        """
        return (self.native_value - 1000) / 10. + 273.15

    def to_fahrenheit(self):
        """Converts to Fahrenheit value.

        :return:    The converted value
        :rtype:    float
        """
        return (self.native_value - 1000) * 0.18 + 32.

    def to_lux_t(self):
        """Converts to lx value.
        Source must be connected to T-port.

        :return:    The converted value
        :rtype:    float
        """
        return math.exp(0.010380664 * self.native_value + 1.689646994)

    def to_lux_i(self):
        """Converts to lx value.
        Source must be connected to I-port.

        :return:    The converted value
        :rtype:    float
        """
        return math.exp(self.native_value / 100)

    def to_percent(self):
        """Converts to % value.

        :return:    The converted value
        :rtype:    int
        """
        return self.native_value

    def to_ppm(self):
        """Converts to ppm value.

        :return:    The converted value
        :rtype:    int
        """
        return self.native_value

    def to_meters_per_second(self):
        """Converts to m/s value.

        :return:    The converted value
        :rtype:    float
        """
        return self.native_value / 10.

    def to_volt(self):
        """Converts to V value.

        :return:    The converted value
        :rtype:    float
        """
        return self.native_value / 400.

    def to_ampere(self):
        """Converts to A value.

        :return:    The converted value
        :rtype:    float
        """
        return self.native_value / 100.

    def to_degree(self):
        """Converts to degree value.

        :return:    The converted value
        :rtype:    float
        """
        return (self.native_value - 1000) / 10.

    def to_var_unit_string(self, unit, is_lockable_regulator_source=False,
                           use_lcn_special_values=False):
        """Converts the given unit into a string representation.

        :param    VarUnit    unit:    The input unit
        :param    bool       is_lockable_regulator_source:  Is lockable source
        :param    bool       use_lcn_special_values:  Use LCN special values

        :return:    The string representation of input unit.
        :rtype:     str
        """
        if use_lcn_special_values and\
                (self.native_value == 0xffff):  # No value
            ret = '---'
        elif use_lcn_special_values and\
                ((self.native_value & 0xff00) == 0x8100):  # Undefined
            ret = '---'
        elif use_lcn_special_values and\
                ((self.native_value & 0xff00) == 0x7f00):  # Defective
            ret = '!!!'
        else:
            var = VarValue((self.native_value & 0x7ff)
                           if is_lockable_regulator_source
                           else self.native_value)
            if unit == VarUnit.NATIVE:
                ret = '{:.0f}'.format(var.to_native())
            elif unit == VarUnit.CELSIUS:
                ret = '{:.01f}'.format(var.to_celsius())
            elif unit == VarUnit.KELVIN:
                ret = '{:.01f}'.format(var.to_kelvin())
            elif unit == VarUnit.FAHRENHEIT:
                ret = '{:.01f}'.format(var.to_fahrenheit())
            elif unit == VarUnit.LUX_T:
                if var.to_native() > 1152:  # Max. value the HW can do
                    ret = '---'
                else:
                    ret = '{:.0f}'.format(var.to_lux_t())
            elif unit == VarUnit.LUX_I:
                if var.to_native() > 1152:  # Max. value the HW can do
                    ret = '---'
                else:
                    ret = '{:.0f}'.format(var.to_lux_i())
            elif unit == VarUnit.METERPERSECOND:
                ret = '{:.0f}'.format(var.to_meters_per_second())
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
        if is_lockable_regulator_source and self.is_locked_regulator():
            ret = '({:s})'.format(ret)

        return ret


class LedStatus(Enum):
    """Possible states for LCN LEDs
    """
    OFF = 'A'
    ON = 'E'
    BLINK = 'B'
    FLICKER = 'F'


class LogicOpStatus(Enum):
    """Possible states for LCN logic-operations.
    """
    NOT = 'N'
    OR = "T"  # Note: Actually not correct since AND won't be OR also
    AND = 'V'


class TimeUnit(Enum):
    """Time units used for several LCN commands.
    """
    SECONDS = 'S'
    MINUTES = 'M'
    HOURS = 'H'
    DAYS = 'D'

    @staticmethod
    def parse(time_unit):
        """Parses the given time_unit into a time unit.
        It supports several alternative terms.

        :param    str    time_unit:    The text to parse

        :return:    TimeUnit enum
        :rtype:    TimeUnit
        """
        time_unit = time_unit.upper()
        if time_unit in ['SECONDS', 'SECOND', 'SEC', 'S']:
            tu = TimeUnit.SECONDS
        elif time_unit in ['MINUTES', 'MINUTE', 'MIN', 'M']:
            tu = TimeUnit.MINUTES
        elif time_unit in ['HOURS', 'HOUR', 'H']:
            tu = TimeUnit.HOURS
        elif time_unit in ['DAYS', 'DAY', 'D']:
            tu = TimeUnit.DAYS
        else:
            raise ValueError('Bad time unit input.')
        return tu


class RelayStateModifier(Enum):
    """Relay-state modifiers used in LCN commands.
    """
    ON = '1'
    OFF = '0'
    TOGGLE = 'U'
    NOCHANGE = '-'


class MotorStateModifier(Enum):
    """Motor-state modifiers used in LCN commands.
    LCN module has to be configured for motors connected to relays.
    """
    UP = 'U'
    DOWN = 'D'
    STOP = 'S'
    TOGGLEONOFF = 'T'  # toggle on/off
    TOGGLEDIR = 'D'  # toggle direction
    CYCLE = 'C'  # up, stop, down, stop, ...
    NOCHANGE = '-'


class RelVarRef(Enum):
    """Value-reference for relative LCN variable commands.
    """
    CURRENT = auto()
    PROG = auto()  # Programmed value (LCN-PRO). Set-points and thresholds.


class SendKeyCommand(Enum):
    """Command types used when sending LCN keys.
    """
    HIT = 'K'
    MAKE = 'L'
    BREAK = 'O'
    DONTSEND = '-'


class KeyLockStateModifier(Enum):
    """Key-lock modifiers used in LCN commands.
    """
    ON = '1'
    OFF = '0'
    TOGGLE = 'U'
    NOCHANGE = '-'


default_connection_settings = \
    {'NUM_TRIES': 3,  # Total number of request to sent before going into
                      # failed-state.
     'SK_NUM_TRIES': 3,  # Total number of segment coupler scan tries
     'DIM_MODE': OutputPortDimMode.STEPS50,
     'PING_TIMEOUT': 600000,  # The default timeout for pings sent to PCHK.
     'MAX_STATUS_EVENTBASED_VALUEAGE_MSEC': 600000,  # Poll interval for
                                                     # status values that
                                                     # automatically send
                                                     # their values on change.
     'MAX_STATUS_POLLED_VALUEAGE_MSEC': 30000,  # Poll interval for status
                                                # values that do not send
                                                # their values on change
                                                # (always polled).
     'STATUS_REQUEST_DELAY_AFTER_COMMAND_MSEC': 2000  # Status request delay
                                                      # after a command has
                                                      # been send which
                                                      # potentially changed
                                                      # that status.
     }
