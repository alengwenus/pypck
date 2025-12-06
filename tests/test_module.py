"""Tests for module."""

import asyncio
from itertools import chain

import pytest
from pypck.device import Serials
from pypck.lcn_addr import LcnAddr
from pypck.pck_commands import PckGenerator

from pypck import inputs, lcn_defs

from .conftest import MockDeviceConnection, wait_until_called

RELAY_STATES = [True, False, True, False, True, False, True, False]
BINARY_SENSOR_STATES = [True, False, True, False, True, False, True, False]
LED_STATES = [
    lcn_defs.LedStatus.ON,
    lcn_defs.LedStatus.OFF,
    lcn_defs.LedStatus.BLINK,
    lcn_defs.LedStatus.FLICKER,
    lcn_defs.LedStatus.ON,
    lcn_defs.LedStatus.OFF,
    lcn_defs.LedStatus.BLINK,
    lcn_defs.LedStatus.FLICKER,
    lcn_defs.LedStatus.ON,
    lcn_defs.LedStatus.OFF,
    lcn_defs.LedStatus.BLINK,
    lcn_defs.LedStatus.FLICKER,
]
LOGIC_OPS_STATES = [
    lcn_defs.LogicOpStatus.ALL,
    lcn_defs.LogicOpStatus.NONE,
    lcn_defs.LogicOpStatus.SOME,
    lcn_defs.LogicOpStatus.NONE,
]
LOCKED_KEY_STATES = [
    [True, False, True, False, True, False, True, False],
    [False, True, False, True, False, True, False, True],
    [True, True, True, True, False, False, False, False],
    [False, False, False, False, True, True, True, True],
]
RANDOM_NAME = "IC77J3jmk5326OQl4zWpuENm"
RANDOM_COMMENT = "29nCynSxzn0mrJ6kt99zsl88azVaCAFv79sh"
RANDOM_OEM_TEXT = "8Zmt98YjYY6ksAGNIdxNOLSOjgJpOd1SWFVLaAGpsW5BPbJJ"

#
# Status requests
#


@pytest.mark.parametrize(
    "output_port",
    [
        lcn_defs.OutputPort.OUTPUT1,
        lcn_defs.OutputPort.OUTPUT2,
        lcn_defs.OutputPort.OUTPUT3,
        lcn_defs.OutputPort.OUTPUT4,
    ],
)
async def test_request_status_output(
    module10: MockDeviceConnection, output_port: lcn_defs.OutputPort
) -> None:
    """Test requesting the output status of a module."""
    request_task = asyncio.create_task(module10.request_status_output(output_port))

    await wait_until_called(module10.send_command)
    await module10.async_process_input(
        inputs.ModStatusOutput(module10.addr, output_port.value, 50.0)
    )

    result = await request_task

    assert isinstance(result, inputs.ModStatusOutput)
    assert result.physical_source_addr == module10.addr
    assert result.output_id == output_port.value
    assert result.percent == 50.0


async def test_request_status_relays(module10: MockDeviceConnection) -> None:
    """Test requesting the relays status of a module."""
    request_task = asyncio.create_task(module10.request_status_relays())

    await wait_until_called(module10.send_command)
    await module10.async_process_input(
        inputs.ModStatusRelays(module10.addr, RELAY_STATES)
    )

    result = await request_task

    assert isinstance(result, inputs.ModStatusRelays)
    assert result.physical_source_addr == module10.addr
    assert result.states == RELAY_STATES


@pytest.mark.parametrize(
    "motor",
    [
        lcn_defs.MotorPort.MOTOR1,
        lcn_defs.MotorPort.MOTOR2,
        lcn_defs.MotorPort.MOTOR3,
        lcn_defs.MotorPort.MOTOR4,
    ],
)
async def test_request_status_motor_position(
    module10: MockDeviceConnection, motor: lcn_defs.MotorPort
) -> None:
    """Test requesting the motors status of a module."""
    request_task = asyncio.create_task(
        module10.request_status_motor_position(motor, lcn_defs.MotorPositioningMode.BS4)
    )

    await wait_until_called(module10.send_command)
    await module10.async_process_input(
        inputs.ModStatusMotorPositionBS4(module10.addr, motor.value, 50.0)
    )

    result = await request_task

    assert isinstance(result, inputs.ModStatusMotorPositionBS4)
    assert result.physical_source_addr == module10.addr
    assert result.motor == motor.value
    assert result.position == 50.0


async def test_request_status_binary_sensors(module10: MockDeviceConnection) -> None:
    """Test requesting the binary sensors status of a module."""
    request_task = asyncio.create_task(module10.request_status_binary_sensors())

    await wait_until_called(module10.send_command)
    await module10.async_process_input(
        inputs.ModStatusBinSensors(module10.addr, BINARY_SENSOR_STATES)
    )

    result = await request_task

    assert isinstance(result, inputs.ModStatusBinSensors)
    assert result.physical_source_addr == module10.addr
    assert result.states == BINARY_SENSOR_STATES


@pytest.mark.parametrize(
    "variable, software_serial",
    [
        *[
            (variable, 0x170206)
            for variable in lcn_defs.Var.variables_new()
            + lcn_defs.Var.set_points()
            + list(chain(*lcn_defs.Var.thresholds_new()))
            + lcn_defs.Var.s0s()
        ],
        *[
            (variable, 0x170000)
            for variable in lcn_defs.Var.variables_old()
            + lcn_defs.Var.set_points()
            + list(chain(*lcn_defs.Var.thresholds_old()))
        ],
    ],
)
async def test_request_status_variable(
    module10: MockDeviceConnection, variable: lcn_defs.Var, software_serial: int
) -> None:
    """Test requesting the variable status of a module."""
    module10.serials.software_serial = software_serial
    request_task = asyncio.create_task(module10.request_status_variable(variable))

    await wait_until_called(module10.send_command)
    await module10.async_process_input(
        inputs.ModStatusVar(module10.addr, variable, lcn_defs.VarValue.from_native(50))
    )

    result = await request_task

    assert isinstance(result, inputs.ModStatusVar)
    assert result.physical_source_addr == module10.addr
    assert result.var == variable
    assert result.value == lcn_defs.VarValue.from_native(50)


async def test_request_status_led_and_logic_ops(module10: MockDeviceConnection) -> None:
    """Test requesting the LED and logic operations status of a module."""
    request_task = asyncio.create_task(module10.request_status_led_and_logic_ops())

    await wait_until_called(module10.send_command)
    await module10.async_process_input(
        inputs.ModStatusLedsAndLogicOps(module10.addr, LED_STATES, LOGIC_OPS_STATES)
    )

    result = await request_task

    assert isinstance(result, inputs.ModStatusLedsAndLogicOps)
    assert result.physical_source_addr == module10.addr
    assert result.states_led == LED_STATES
    assert result.states_logic_ops == LOGIC_OPS_STATES


async def test_request_status_locked_keys(module10: MockDeviceConnection) -> None:
    """Test requesting the locker keys status of a module."""
    request_task = asyncio.create_task(module10.request_status_locked_keys())

    await wait_until_called(module10.send_command)
    await module10.async_process_input(
        inputs.ModStatusKeyLocks(module10.addr, LOCKED_KEY_STATES)
    )

    result = await request_task

    assert isinstance(result, inputs.ModStatusKeyLocks)
    assert result.physical_source_addr == module10.addr
    assert result.states == LOCKED_KEY_STATES


async def test_request_serials(module10: MockDeviceConnection) -> None:
    """Test requesting serials of a module."""
    request_task = asyncio.create_task(module10.request_serials())

    await wait_until_called(module10.send_command, False, PckGenerator.request_serial())
    await module10.async_process_input(
        inputs.ModSn(
            module10.addr,
            hardware_serial=0x1A20A1234,
            manu=0x1,
            software_serial=0x190B11,
            hardware_type=lcn_defs.HardwareType.SH_PLUS,
        )
    )
    result = await request_task

    assert isinstance(result, Serials)
    assert result.hardware_serial == 0x1A20A1234
    assert result.manu == 0x1
    assert result.software_serial == 0x190B11
    assert result.hardware_type == lcn_defs.HardwareType.SH_PLUS


@pytest.mark.parametrize(
    "command, blocks, text",
    [
        ("N", 2, RANDOM_NAME),
        ("K", 3, RANDOM_COMMENT),
        ("O", 4, RANDOM_OEM_TEXT),
    ],
)
async def test_request_name(
    command: str, blocks: int, text: str, module10: MockDeviceConnection
) -> None:
    """Test requesting the name, comment or oem_text of a module."""
    match command:
        case "N":
            request_task = asyncio.create_task(module10.request_name())
        case "K":
            request_task = asyncio.create_task(module10.request_comment())
        case "O":
            request_task = asyncio.create_task(module10.request_oem_text())

    for idx in range(blocks):
        await wait_until_called(module10.send_command)
        await module10.async_process_input(
            inputs.ModNameComment(
                module10.addr,
                command=command,
                block_id=idx,
                text=text[idx * 12 : (idx + 1) * 12],
            )
        )

    result = await request_task

    assert isinstance(result, str)
    assert result == text


@pytest.mark.parametrize("dynamic", [True, False])
async def test_request_group_memberships(
    dynamic: bool, module10: MockDeviceConnection
) -> None:
    """Test requesting group memberships of a module."""
    addresses = [LcnAddr(0, 7 + id, False) for id in range(3)]
    request_task = asyncio.create_task(module10.request_group_memberships(dynamic))

    await wait_until_called(module10.send_command)
    await module10.async_process_input(
        inputs.ModStatusGroups(module10.addr, dynamic, 12, addresses)
    )
    result = await request_task

    assert isinstance(result, set)
    assert result == set(addresses)
