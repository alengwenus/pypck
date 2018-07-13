def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

   
"""
LCN dimming mode.
If solely modules with firmware 170206 or newer are present, LCN-PRO automatically programs STEPS200.
Otherwise the default is STEPS50.
Since LCN-PCHK doesn't know the current mode, it must explicitly be set.
"""    
output_port_dim_mode = enum('STEPS50',      # 0..50 dimming steps (all LCN module generations)
                            'STEPS200')     # 0..200 dimming steps (since 170206)


"""
Tells LCN-PCHK how to format output-port status-messages.
PERCENT: allows to show the status in half-percent steps (e.g. "10.5").
NATIVE: is completely backward compatible and there are no restrictions
concerning the LCN module generations. It requires LCN-PCHK 2.3 or higher though.
"""
output_port_status_mode = enum('PERCENT',   # Default (compatible with all versions of LCN-PCHK)
                               'NATIVE')    # 0..200 steps (since LCN-PCHK 2.3)


"""
Relay-state modifiers used in LCN commands.
"""
relay_state_modifier = enum('ON',
                            'OFF',
                            'TOGGLE',
                            'NOCHANGE')


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

