from collections import OrderedDict

class Enum(OrderedDict):
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
output_port_dim_mode = Enum('STEPS50',      # 0..50 dimming steps (all LCN module generations)
                            'STEPS200')     # 0..200 dimming steps (since 170206)


"""
Tells LCN-PCHK how to format output-port status-messages.
PERCENT: allows to show the status in half-percent steps (e.g. "10.5").
NATIVE: is completely backward compatible and there are no restrictions
concerning the LCN module generations. It requires LCN-PCHK 2.3 or higher though.
"""
output_port_status_mode = Enum('PERCENT',   # Default (compatible with all versions of LCN-PCHK)
                               'NATIVE')    # 0..200 steps (since LCN-PCHK 2.3)


"""
Relay-state modifiers used in LCN commands.
"""
relay_state_modifier = Enum('ON',
                            'OFF',
                            'TOGGLE',
                            'NOCHANGE')


"""
LCN variable types.
"""
var = Enum('UNKNOWN',   # Used if the real type is not known (yet)
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

