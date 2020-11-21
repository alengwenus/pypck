"""Tests for command generation directed at bus modules and groups."""

import pytest
from pypck.lcn_defs import (
    BeepSound,
    KeyLockStateModifier,
    LedStatus,
    MotorReverseTime,
    MotorStateModifier,
    OutputPort,
    RelayPort,
    RelayStateModifier,
    RelVarRef,
    SendKeyCommand,
    TimeUnit,
    Var,
)
from pypck.pck_commands import PckGenerator

NEW_VAR_SW_AGE = 0x170206

COMMANDS = {
    # Other module commands
    "LEER": (PckGenerator.empty,),
    **{
        f"PIN{count:03d}": (PckGenerator.beep, BeepSound.NORMAL, count)
        for count in range(1, 16)
    },
    **{
        f"PIS{count:03d}": (PckGenerator.beep, BeepSound.SPECIAL, count)
        for count in range(1, 16)
    },
    # General status commands
    "SK": (PckGenerator.segment_coupler_scan,),
    "SN": (PckGenerator.request_serial,),
    **{f"NMN{block+1}": (PckGenerator.request_name, block) for block in range(2)},
    **{f"NMK{block+1}": (PckGenerator.request_comment, block) for block in range(3)},
    **{f"NMO{block+1}": (PckGenerator.request_oem_text, block) for block in range(4)},
    "GP": (PckGenerator.request_group_membership_static,),
    "GD": (PckGenerator.request_group_membership_dynamic,),
    # Output, relay, binsensors, ... status commands
    "SMA1": (PckGenerator.request_output_status, 0),
    "SMA2": (PckGenerator.request_output_status, 1),
    "SMA3": (PckGenerator.request_output_status, 2),
    "SMA4": (PckGenerator.request_output_status, 3),
    "SMR": (PckGenerator.request_relays_status,),
    "SMB": (PckGenerator.request_bin_sensors_status,),
    "SMT": (PckGenerator.request_leds_and_logic_ops,),
    "STX": (PckGenerator.request_key_lock_status,),
    # Variable status (new commands)
    **{
        f"MWT{Var.to_var_id(var)+1:03d}": (
            PckGenerator.request_var_status,
            var,
            NEW_VAR_SW_AGE,
        )
        for var in Var.variables
    },
    **{
        f"MWS{Var.to_set_point_id(var)+1:03d}": (
            PckGenerator.request_var_status,
            var,
            NEW_VAR_SW_AGE,
        )
        for var in Var.set_points
    },
    **{
        f"MWC{Var.to_s0_id(var)+1:03d}": (
            PckGenerator.request_var_status,
            var,
            NEW_VAR_SW_AGE,
        )
        for var in Var.s0s
    },
    **{
        f"SE{Var.to_thrs_register_id(var)+1:03d}": (
            PckGenerator.request_var_status,
            var,
            NEW_VAR_SW_AGE,
        )
        for reg in Var.thresholds
        for var in reg
    },
    # Variable status (legacy commands)
    "MWV": (PckGenerator.request_var_status, Var.TVAR, NEW_VAR_SW_AGE - 1),
    "MWTA": (PckGenerator.request_var_status, Var.R1VAR, NEW_VAR_SW_AGE - 1),
    "MWTB": (PckGenerator.request_var_status, Var.R2VAR, NEW_VAR_SW_AGE - 1),
    "MWSA": (PckGenerator.request_var_status, Var.R1VARSETPOINT, NEW_VAR_SW_AGE - 1),
    "MWSB": (PckGenerator.request_var_status, Var.R2VARSETPOINT, NEW_VAR_SW_AGE - 1),
    **{
        "SL1": (PckGenerator.request_var_status, var, NEW_VAR_SW_AGE - 1)
        for var in Var.thresholds[0]
    },
    # Output manipulation
    **{
        f"A{output+1:d}DI050123": (PckGenerator.dim_output, output, 50.0, 123)
        for output in range(4)
    },
    **{
        f"O{output+1:d}DI101123": (PckGenerator.dim_output, output, 50.5, 123)
        for output in range(4)
    },
    "OY100100100100123": (PckGenerator.dim_all_outputs, 50.0, 123, True),
    "OY000000000000123": (PckGenerator.dim_all_outputs, 0.0, 123, True),
    "OY200200200200123": (PckGenerator.dim_all_outputs, 100.0, 123, True),
    "AA123": (PckGenerator.dim_all_outputs, 0.0, 123),
    "AE123": (PckGenerator.dim_all_outputs, 100.0, 123),
    "AH050": (PckGenerator.dim_all_outputs, 50.0, 123),
    **{
        f"A{output+1:d}AD050": (PckGenerator.rel_output, output, 50.0)
        for output in range(4)
    },
    **{
        f"A{output+1:d}SB050": (PckGenerator.rel_output, output, -50.0)
        for output in range(4)
    },
    **{
        f"O{output+1:d}AD101": (PckGenerator.rel_output, output, 50.5)
        for output in range(4)
    },
    **{
        f"O{output+1:d}SB101": (PckGenerator.rel_output, output, -50.5)
        for output in range(4)
    },
    **{
        f"A{output+1:d}TA123": (PckGenerator.toggle_output, output, 123)
        for output in range(4)
    },
    "AU123": (PckGenerator.toggle_all_outputs, 123),
    # Relay state manipulation
    "R80-1U1-U0": (
        PckGenerator.control_relays,
        [
            RelayStateModifier.OFF,
            RelayStateModifier.NOCHANGE,
            RelayStateModifier.ON,
            RelayStateModifier.TOGGLE,
            RelayStateModifier.ON,
            RelayStateModifier.NOCHANGE,
            RelayStateModifier.TOGGLE,
            RelayStateModifier.OFF,
        ],
    ),
    "R8T03210011100": (
        PckGenerator.control_relays_timer,
        30 * 32,
        [
            RelayStateModifier.ON,
            RelayStateModifier.OFF,
            RelayStateModifier.OFF,
            RelayStateModifier.ON,
            RelayStateModifier.ON,
            RelayStateModifier.ON,
            RelayStateModifier.OFF,
            RelayStateModifier.OFF,
        ],
    ),
    "R810110---": (
        PckGenerator.control_motors_relays,
        [
            MotorStateModifier.UP,
            MotorStateModifier.DOWN,
            MotorStateModifier.STOP,
            MotorStateModifier.NOCHANGE,
        ],
    ),
    "R8U--UUU--": (
        PckGenerator.control_motors_relays,
        [
            MotorStateModifier.TOGGLEONOFF,
            MotorStateModifier.TOGGLEDIR,
            MotorStateModifier.CYCLE,
            MotorStateModifier.NOCHANGE,
        ],
    ),
    "X2001228000": (
        PckGenerator.control_motors_outputs,
        MotorStateModifier.UP,
        MotorReverseTime.RT70,
    ),
    "X2004200008": (
        PckGenerator.control_motors_outputs,
        MotorStateModifier.UP,
        MotorReverseTime.RT600,
    ),
    "X2004200011": (
        PckGenerator.control_motors_outputs,
        MotorStateModifier.UP,
        MotorReverseTime.RT1200,
    ),
    "X2001000228": (
        PckGenerator.control_motors_outputs,
        MotorStateModifier.DOWN,
        MotorReverseTime.RT70,
    ),
    "X2005200008": (
        PckGenerator.control_motors_outputs,
        MotorStateModifier.DOWN,
        MotorReverseTime.RT600,
    ),
    "X2005200011": (
        PckGenerator.control_motors_outputs,
        MotorStateModifier.DOWN,
        MotorReverseTime.RT1200,
    ),
    "AY000000": (
        PckGenerator.control_motors_outputs,
        MotorStateModifier.STOP,
    ),
    "JE": (
        PckGenerator.control_motors_outputs,
        MotorStateModifier.CYCLE,
    ),
    # Variable manipulation
    **{
        f"X2{var.value | 0x40:03d}016225": (PckGenerator.update_status_var, var, 4321)
        for var in Var.variables
    },
    "X2030044129": (PckGenerator.var_abs, Var.R1VARSETPOINT, 4201),
    "X2030108129": (PckGenerator.var_abs, Var.R2VARSETPOINT, 4201),
    "X2030032000": (PckGenerator.var_reset, Var.R1VARSETPOINT),
    "X2030096000": (PckGenerator.var_reset, Var.R2VARSETPOINT),
    "ZS30000": (PckGenerator.var_reset, Var.TVAR, False),
    **{
        f"Z-{var.value + 1:03d}4090": (PckGenerator.var_reset, var)
        for var in Var.variables
    },
    "ZA23423": (PckGenerator.var_rel, Var.TVAR, RelVarRef.CURRENT, 23423, False),
    "ZS23423": (PckGenerator.var_rel, Var.TVAR, RelVarRef.CURRENT, -23423, False),
    **{
        f"Z-{var.value + 1:03d}3000": (
            PckGenerator.var_rel,
            var,
            RelVarRef.CURRENT,
            -3000,
            True,
        )
        for var in Var.variables
        if var != Var.TVAR
    },
    **{
        f"RE{('A','B')[nvar]}S{('A','P')[nref]}-500": (
            PckGenerator.var_rel,
            var,
            ref,
            -500,
            new,
        )
        for nvar, var in enumerate(Var.set_points)
        for nref, ref in enumerate(RelVarRef)
        for new in (True, False)
    },
    **{
        f"RE{('A','B')[nvar]}S{('A','P')[nref]}+500": (
            PckGenerator.var_rel,
            var,
            ref,
            500,
            new,
        )
        for nvar, var in enumerate(Var.set_points)
        for nref, ref in enumerate(RelVarRef)
        for new in (True, False)
    },
    **{
        f"SS{('R','E')[nref]}0500SR{r+1}{i+1}": (
            PckGenerator.var_rel,
            Var.thresholds[r][i],
            ref,
            -500,
            True,
        )
        for r in range(4)
        for i in range(4)
        for nref, ref in enumerate(RelVarRef)
    },
    **{
        f"SS{('R','E')[nref]}0500AR{r+1}{i+1}": (
            PckGenerator.var_rel,
            Var.thresholds[r][i],
            ref,
            500,
            True,
        )
        for r in range(4)
        for i in range(4)
        for nref, ref in enumerate(RelVarRef)
    },
    **{
        f"SS{('R','E')[nref]}0500S{1<<(4-i):05b}": (
            PckGenerator.var_rel,
            Var.thresholds[0][i],
            ref,
            -500,
            False,
        )
        for i in range(5)
        for nref, ref in enumerate(RelVarRef)
    },
    **{
        f"SS{('R','E')[nref]}0500A{1<<(4-i):05b}": (
            PckGenerator.var_rel,
            Var.thresholds[0][i],
            ref,
            500,
            False,
        )
        for i in range(5)
        for nref, ref in enumerate(RelVarRef)
    },
    # Led manipulation
    **{
        f"LA{led+1:03d}{state.value}": (PckGenerator.control_led, led, state)
        for led in range(12)
        for state in LedStatus
    },
    # Send keys
    **{
        f"TS{acmd.value}{bcmd.value}{ccmd.value}10011100": (
            PckGenerator.send_keys,
            [acmd, bcmd, ccmd, SendKeyCommand.DONTSEND],
            [True, False, False, True, True, True, False, False],
        )
        for acmd in SendKeyCommand
        for bcmd in SendKeyCommand
        for ccmd in SendKeyCommand
    },
    **{
        f"TS---{dcmd.value}10011100": (
            PckGenerator.send_keys,
            [
                SendKeyCommand.DONTSEND,
                SendKeyCommand.DONTSEND,
                SendKeyCommand.DONTSEND,
                dcmd,
            ],
            [True, False, False, True, True, True, False, False],
        )
        for dcmd in SendKeyCommand
        if dcmd != SendKeyCommand.DONTSEND
    },
    **{
        f"TV{('A','B','C','D')[table]}040{unit.value}11001110": (
            PckGenerator.send_keys_hit_deferred,
            table,
            40,
            unit,
            [True, True, False, False, True, True, True, False],
        )
        for table in range(4)
        for unit in TimeUnit
    },
    # Lock keys
    **{
        f"TX{('A','B','C','D')[table]}10U--01U": (
            PckGenerator.lock_keys,
            table,
            [
                KeyLockStateModifier.ON,
                KeyLockStateModifier.OFF,
                KeyLockStateModifier.TOGGLE,
                KeyLockStateModifier.NOCHANGE,
                KeyLockStateModifier.NOCHANGE,
                KeyLockStateModifier.OFF,
                KeyLockStateModifier.ON,
                KeyLockStateModifier.TOGGLE,
            ],
        )
        for table in range(4)
    },
    **{
        f"TXZA040{unit.value}11001110": (
            PckGenerator.lock_keys_tab_a_temporary,
            40,
            unit,
            [True, True, False, False, True, True, True, False],
        )
        for unit in TimeUnit
    },
    # Lock regulator
    **{
        f"RE{('A','B')[reg]:s}XS": (PckGenerator.lock_regulator, reg, True)
        for reg in range(2)
    },
    **{
        f"RE{('A','B')[reg]:s}XA": (PckGenerator.lock_regulator, reg, False)
        for reg in range(2)
    },
    # scenes
    "SZR003007": (PckGenerator.request_status_scene, 3, 7),
    "SZW004": (PckGenerator.change_scene_register, 4),
    "SZA7001": (PckGenerator.activate_scene_output, 1, OutputPort),
    "SZA7001133": (PckGenerator.activate_scene_output, 1, OutputPort, 133),
    "SZS7002": (PckGenerator.store_scene_output, 2, OutputPort),
    "SZS7002133": (PckGenerator.store_scene_output, 2, OutputPort, 133),
    "SZA7005": (PckGenerator.activate_scene_output, 5, OutputPort),
    "SZA7005133": (PckGenerator.activate_scene_output, 5, OutputPort, 133),
    "SZS7008": (PckGenerator.store_scene_output, 8, OutputPort),
    "SZS7008133": (PckGenerator.store_scene_output, 8, OutputPort, 133),
    "SZA000810001110": (
        PckGenerator.activate_scene_relay,
        8,
        (
            RelayPort.RELAY1,
            RelayPort.RELAY5,
            RelayPort.RELAY6,
            RelayPort.RELAY7,
        ),
    ),
    "SZS000810001110": (
        PckGenerator.store_scene_relay,
        8,
        (
            RelayPort.RELAY1,
            RelayPort.RELAY5,
            RelayPort.RELAY6,
            RelayPort.RELAY7,
        ),
    ),
}


@pytest.mark.parametrize("expected, command", COMMANDS.items())
def test_command_generation_single_mod_noack(expected, command):
    """Test if InputMod parses message correctly."""
    assert expected == command[0](*command[1:])
