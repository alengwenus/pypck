"""LCN devices: Modules and groups."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from pypck import inputs, lcn_defs
from pypck.helpers import TaskRegistry
from pypck.lcn_addr import LcnAddr
from pypck.pck_commands import PckGenerator
from pypck.status_requester import StatusRequester

if TYPE_CHECKING:
    from pypck.connection import PchkConnectionManager

_LOGGER = logging.getLogger(__name__)


@dataclass
class Serials:
    """Data class for module serials."""

    hardware_serial: int
    manu: int
    software_serial: int
    hardware_type: lcn_defs.HardwareType


class DeviceConnection:
    """Organizes communication with a specific module/group.

    Sends status requests to the connection and handles status responses.
    """

    def __init__(
        self,
        conn: PchkConnectionManager,
        addr: LcnAddr,
        wants_ack: bool = False,
    ) -> None:
        """Construct AbstractConnection instance."""
        self.conn = conn
        self.addr = addr
        self.wants_ack = wants_ack
        self.serials = Serials(-1, -1, -1, lcn_defs.HardwareType.UNKNOWN)
        self._serials_known = asyncio.Event()

        self.input_callbacks: set[Callable[[inputs.Input], None]] = set()

        # List of queued acknowledge codes from the LCN modules.
        self.acknowledges: asyncio.Queue[lcn_defs.AcknowledgeErrorCode] = (
            asyncio.Queue()
        )

        # StatusRequester
        self.status_requester = StatusRequester(self)

        if self.addr.is_group:
            self.wants_ack = False  # groups do not send acks
            self._serials_known.set()
        else:
            self.task_registry.create_task(self._request_device_properties())

    @property
    def task_registry(self) -> TaskRegistry:
        """Get the task registry."""
        return self.conn.task_registry

    @property
    def seg_id(self) -> int:
        """Get the segment id."""
        return self.addr.seg_id

    @property
    def addr_id(self) -> int:
        """Get the module or group id."""
        return self.addr.addr_id

    @property
    def is_group(self) -> int:
        """Return whether this connection refers to a module or group."""
        return self.addr.is_group

    async def send_command(self, wants_ack: bool, pck: str | bytes) -> bool:
        """Send a command to the module represented by this class.

        :param    bool    wants_ack:    Also send a request for acknowledge.
        :param    str     pck:          PCK command (without header).
        """
        if not self.addr.is_group and wants_ack:
            return await self.send_command_with_ack(pck)

        return await self._send_command(wants_ack, pck)

    async def _send_command(self, wants_ack: bool, pck: str | bytes) -> bool:
        """Send a command to the module represented by this class.

        :param    bool    wants_ack:    Also send a request for acknowledge.
        :param    str     pck:          PCK command (without header).
        """
        header = PckGenerator.generate_address_header(
            self.addr, self.conn.local_seg_id, wants_ack
        )
        if isinstance(pck, str):
            return await self.conn.send_command(header + pck)
        return await self.conn.send_command(header.encode() + pck)

    async def serials_known(self) -> None:
        """Wait until the serials of this device are known."""
        await self._serials_known.wait()

    # ##
    # ## Retry logic if an acknowledge is requested
    # ##

    async def send_command_with_ack(self, pck: str | bytes) -> bool:
        """Send a PCK command and ensure receiving of an acknowledgement.

        Resends the PCK command if no acknowledgement has been received
        within timeout.

        :param    str     pck:          PCK command (without header).
        :returns:    True if acknowledge was received, False otherwise
        :rtype:      bool
        """
        count = 0
        while count < self.conn.settings["NUM_TRIES"]:
            await self._send_command(True, pck)
            try:
                code = await asyncio.wait_for(
                    self.acknowledges.get(),
                    timeout=self.conn.settings["DEFAULT_TIMEOUT"],
                )
            except asyncio.TimeoutError:
                count += 1
                continue
            if code == lcn_defs.AcknowledgeErrorCode.OK:
                return True
            break
        return False

    async def on_ack(
        self, code: lcn_defs.AcknowledgeErrorCode = lcn_defs.AcknowledgeErrorCode.OK
    ) -> None:
        """Is called whenever an acknowledge is received from the LCN module.

        :param     int    code:           The LCN internal code. -1 means
                                          "positive" acknowledge
        """
        await self.acknowledges.put(code)

    # ##
    # ## Methods for sending PCK commands
    # ##

    async def dim_output(self, output_id: int, percent: float, ramp: int) -> bool:
        """Send a dim command for a single output-port.

        :param    int      output_id:    Output id 0..3
        :param    float    percent:      Brightness in percent 0..100
        :param    int      ramp:         Ramp time in milliseconds

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack, PckGenerator.dim_output(output_id, percent, ramp)
        )

    async def dim_all_outputs(self, percent: float, ramp: int) -> bool:
        """Send a dim command for all output-ports.

        :param    float  percent:           Brightness in percent 0..100
        :param    int    ramp:              Ramp time in milliseconds.
        :param    int    software_serial:   The minimum firmware version expected by
                                            any receiving module.

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        await self._serials_known.wait()
        return await self.send_command(
            self.wants_ack,
            PckGenerator.dim_all_outputs(percent, ramp, self.serials.software_serial),
        )

    async def rel_output(self, output_id: int, percent: float) -> bool:
        """Send a command to change the value of an output-port.

        :param     int    output_id:    Output id 0..3
        :param     float    percent:      Relative brightness in percent
                                        -100..100

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack, PckGenerator.rel_output(output_id, percent)
        )

    async def toggle_output(
        self, output_id: int, ramp: int, to_memory: bool = False
    ) -> bool:
        """Send a command that toggles a single output-port.

        Toggle mode: (on->off, off->on).

        :param    int    output_id:    Output id 0..3
        :param    int    ramp:         Ramp time in milliseconds
        :param    bool   to_memory:    If True, the dimming status is stored

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack, PckGenerator.toggle_output(output_id, ramp, to_memory)
        )

    async def toggle_all_outputs(self, ramp: int) -> bool:
        """Generate a command that toggles all output-ports.

        Toggle Mode:  (on->off, off->on).

        :param    int    ramp:        Ramp time in milliseconds

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack, PckGenerator.toggle_all_outputs(ramp)
        )

    async def control_relays(self, states: list[lcn_defs.RelayStateModifier]) -> bool:
        """Send a command to control relays.

        :param    states:   The 8 modifiers for the relay states as alist
        :type     states:   list(:class:`~pypck.lcn_defs.RelayStateModifier`)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack, PckGenerator.control_relays(states)
        )

    async def control_relays_timer(
        self, time_msec: int, states: list[lcn_defs.RelayStateModifier]
    ) -> bool:
        """Send a command to control relays.

        :param      int     time_msec:  Duration of timer in milliseconds
        :param    states:   The 8 modifiers for the relay states as alist
        :type     states:   list(:class:`~pypck.lcn_defs.RelayStateModifier`)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack, PckGenerator.control_relays_timer(time_msec, states)
        )

    async def control_motor_relays(
        self,
        motor_id: int,
        state: lcn_defs.MotorStateModifier,
        mode: lcn_defs.MotorPositioningMode = lcn_defs.MotorPositioningMode.NONE,
    ) -> bool:
        """Send a command to control motors via relays.

        :param    int                    motor_id:    The motor id 0..3
        :param    MotorStateModifier     state:       The modifier for the
        :param    MotorPositioningMode   mode:        The motor positioning mode (ooptional)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack, PckGenerator.control_motor_relays(motor_id, state, mode)
        )

    async def control_motor_relays_position(
        self,
        motor_id: int,
        position: float,
        mode: lcn_defs.MotorPositioningMode,
    ) -> bool:
        """Control motor position via relays and BS4.

        :param    int                  motor_id:   The motor port of the LCN module
        :param    float                position:   The position to set in percentage (0..100)
        :param    MotorPositioningMode mode:       The motor positioning mode

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack,
            PckGenerator.control_motor_relays_position(motor_id, position, mode),
        )

    async def control_motor_outputs(
        self,
        state: lcn_defs.MotorStateModifier,
        reverse_time: lcn_defs.MotorReverseTime | None = None,
    ) -> bool:
        """Send a command to control a motor via output ports 1+2.

        :param    MotorStateModifier  state: The modifier for the cover state
        :param    MotorReverseTime    reverse_time: Reverse time for modules
                                                    with FW<190C
        :type     state:   :class: `~pypck.lcn-defs.MotorStateModifier`

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack,
            PckGenerator.control_motor_outputs(state, reverse_time),
        )

    async def activate_scene(
        self,
        register_id: int,
        scene_id: int,
        output_ports: Sequence[lcn_defs.OutputPort] = (),
        relay_ports: Sequence[lcn_defs.RelayPort] = (),
        ramp: int | None = None,
    ) -> bool:
        """Activate the stored states for the given scene.

        :param    int                register_id:    Register id 0..9
        :param    int                scene_id:       Scene id 0..9
        :param    list(OutputPort)   output_ports:   Output ports to activate
                                                     as list
        :param    list(RelayPort)    relay_ports:    Relay ports to activate
                                                     as list
        :param    int                ramp:           Ramp value

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        success = await self.send_command(
            self.wants_ack, PckGenerator.change_scene_register(register_id)
        )
        if not success:
            return False

        result = True
        if output_ports:
            result &= await self.send_command(
                self.wants_ack,
                PckGenerator.activate_scene_output(scene_id, output_ports, ramp),
            )
        if relay_ports:
            result &= await self.send_command(
                self.wants_ack,
                PckGenerator.activate_scene_relay(scene_id, relay_ports),
            )
        return result

    async def store_scene(
        self,
        register_id: int,
        scene_id: int,
        output_ports: Sequence[lcn_defs.OutputPort] = (),
        relay_ports: Sequence[lcn_defs.RelayPort] = (),
        ramp: int | None = None,
    ) -> bool:
        """Store states in the given scene.

        :param    int                register_id:    Register id 0..9
        :param    int                scene_id:       Scene id 0..9
        :param    list(OutputPort)   output_ports:   Output ports to store
                                                     as list
        :param    list(RelayPort)    relay_ports:    Relay ports to store
                                                     as list
        :param    int                ramp:           Ramp value

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        success = await self.send_command(
            self.wants_ack, PckGenerator.change_scene_register(register_id)
        )

        if not success:
            return False

        result = True
        if output_ports:
            result &= await self.send_command(
                self.wants_ack,
                PckGenerator.store_scene_output(scene_id, output_ports, ramp),
            )
        if relay_ports:
            result &= await self.send_command(
                self.wants_ack,
                PckGenerator.store_scene_relay(scene_id, relay_ports),
            )
        return result

    async def store_scene_outputs_direct(
        self,
        register_id: int,
        scene_id: int,
        percents: Sequence[float],
        ramps: Sequence[int],
    ) -> bool:
        """Store the given output values and ramps in the given scene.

        :param    int           register_id: Register id 0..9
        :param    int           scene_id:    Scene id 0..9
        :param    list(float)   percents:    Output values in percent as list
        :param    list(int)     ramp:        Ramp values as list

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack,
            PckGenerator.store_scene_outputs_direct(
                register_id, scene_id, percents, ramps
            ),
        )

    async def var_abs(
        self,
        var: lcn_defs.Var,
        value: float | lcn_defs.VarValue,
        unit: lcn_defs.VarUnit = lcn_defs.VarUnit.NATIVE,
        software_serial: int = -1,
    ) -> bool:
        """Send a command to set the absolute value to a variable.

        :param     Var        var:      Variable
        :param     float      value:    Absolute value to set
        :param     VarUnit    unit:     Unit of variable

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        if self.addr.is_group:
            result = True
            # for new modules (>=0x170206)
            result &= await self.var_abs(var, value, unit, 0x170206)

            # for old modules (<0x170206)
            if var in [
                lcn_defs.Var.TVAR,
                lcn_defs.Var.R1VAR,
                lcn_defs.Var.R2VAR,
                lcn_defs.Var.R1VARSETPOINT,
                lcn_defs.Var.R2VARSETPOINT,
            ]:
                result &= await self.var_abs(var, value, unit, 0x000000)
            return result

        if not isinstance(value, lcn_defs.VarValue):
            value = lcn_defs.VarValue.from_var_unit(value, unit, True)

        if software_serial == -1:
            await self._serials_known.wait()
            software_serial = self.serials.software_serial

        if lcn_defs.Var.to_var_id(var) != -1:
            # Absolute commands for variables 1-12 are not supported
            if self.addr_id == 4 and self.is_group:
                # group 4 are status messages
                return await self.send_command(
                    self.wants_ack,
                    PckGenerator.update_status_var(var, value.to_native()),
                )
            # We fake the missing command by using reset and relative
            # commands.
            success = await self.send_command(
                self.wants_ack,
                PckGenerator.var_reset(var, software_serial),
            )
            if not success:
                return False
            return await self.send_command(
                self.wants_ack,
                PckGenerator.var_rel(
                    var,
                    lcn_defs.RelVarRef.CURRENT,
                    value.to_native(),
                    software_serial,
                ),
            )
        return await self.send_command(
            self.wants_ack, PckGenerator.var_abs(var, value.to_native())
        )

    async def var_reset(self, var: lcn_defs.Var, software_serial: int = -1) -> bool:
        """Send a command to reset the variable value.

        :param    Var    var:    Variable

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        if self.addr.is_group:
            result = True
            result &= await self.var_reset(var, 0x170206)
            if var in [
                lcn_defs.Var.TVAR,
                lcn_defs.Var.R1VAR,
                lcn_defs.Var.R2VAR,
                lcn_defs.Var.R1VARSETPOINT,
                lcn_defs.Var.R2VARSETPOINT,
            ]:
                result &= await self.var_reset(var, 0)
            return result

        if software_serial == -1:
            await self._serials_known.wait()
            software_serial = self.serials.software_serial

        return await self.send_command(
            self.wants_ack, PckGenerator.var_reset(var, software_serial)
        )

    async def var_rel(
        self,
        var: lcn_defs.Var,
        value: float | lcn_defs.VarValue,
        unit: lcn_defs.VarUnit = lcn_defs.VarUnit.NATIVE,
        value_ref: lcn_defs.RelVarRef = lcn_defs.RelVarRef.CURRENT,
        software_serial: int = -1,
    ) -> bool:
        """Send a command to change the value of a variable.

        :param     Var        var:      Variable
        :param     float      value:    Relative value to add (may also be
                                        negative)
        :param     VarUnit    unit:     Unit of variable

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        if self.addr.is_group:
            result = True
            result &= await self.var_rel(var, value, software_serial=0x170206)
            if var in [
                lcn_defs.Var.TVAR,
                lcn_defs.Var.R1VAR,
                lcn_defs.Var.R2VAR,
                lcn_defs.Var.R1VARSETPOINT,
                lcn_defs.Var.R2VARSETPOINT,
                lcn_defs.Var.THRS1,
                lcn_defs.Var.THRS2,
                lcn_defs.Var.THRS3,
                lcn_defs.Var.THRS4,
                lcn_defs.Var.THRS5,
            ]:
                result &= await self.var_rel(var, value, software_serial=0)
            return result

        if not isinstance(value, lcn_defs.VarValue):
            value = lcn_defs.VarValue.from_var_unit(value, unit, False)

        if software_serial == -1:
            await self._serials_known.wait()
            software_serial = self.serials.software_serial

        return await self.send_command(
            self.wants_ack,
            PckGenerator.var_rel(var, value_ref, value.to_native(), software_serial),
        )

    async def lock_regulator(
        self, reg_id: int, state: bool, target_value: float = -1
    ) -> bool:
        """Send a command to lock a regulator.

        :param    int        reg_id:        Regulator id
        :param    bool       state:         Lock state (locked=True,
                                            unlocked=False)
        :param    float        target_value:  Target value in percent (use -1 to ignore)
        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack,
            PckGenerator.lock_regulator(
                reg_id, state, self.serials.software_serial, target_value
            ),
        )

    async def control_led(
        self, led: lcn_defs.LedPort, state: lcn_defs.LedStatus
    ) -> bool:
        """Send a command to control a led.

        :param    LedPort      led:        Led port
        :param    LedStatus    state:      Led status
        """
        return await self.send_command(
            self.wants_ack, PckGenerator.control_led(led.value, state)
        )

    async def send_keys(
        self, keys: list[list[bool]], cmd: lcn_defs.SendKeyCommand
    ) -> list[bool]:
        """Send a command to send keys.

        :param    list(bool)[4][8]    keys:    2d-list with [table_id][key_id]
                                               bool values, if command should
                                               be sent to specific key
        :param    SendKeyCommand      cmd:     command to send for each table

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      list of bool
        """
        results: list[bool] = []
        for table_id, key_states in enumerate(keys):
            if True in key_states:
                cmds = [lcn_defs.SendKeyCommand.DONTSEND] * 4
                cmds[table_id] = cmd
                results.append(
                    await self.send_command(
                        self.wants_ack, PckGenerator.send_keys(cmds, key_states)
                    )
                )
        return results

    async def send_keys_hit_deferred(
        self, keys: list[list[bool]], delay_time: int, delay_unit: lcn_defs.TimeUnit
    ) -> list[bool]:
        """Send a command to send keys deferred.

        :param    list(bool)[4][8]    keys:          2d-list with
                                                     [table_id][key_id] bool
                                                     values, if command should
                                                     be sent to specific key
        :param    int                 delay_time:    Delay time
        :param    TimeUnit            delay_unit:    Unit of time

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      list of bool
        """
        results: list[bool] = []
        for table_id, key_states in enumerate(keys):
            if True in key_states:
                results.append(
                    await self.send_command(
                        self.wants_ack,
                        PckGenerator.send_keys_hit_deferred(
                            table_id, delay_time, delay_unit, key_states
                        ),
                    ),
                )
        return results

    async def lock_keys(
        self, table_id: int, states: list[lcn_defs.KeyLockStateModifier]
    ) -> bool:
        """Send a command to lock keys.

        :param    int                     table_id:  Table id: 0..3
        :param    keyLockStateModifier    states:    The 8 modifiers for the
                                                     key lock states as a list

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack, PckGenerator.lock_keys(table_id, states)
        )

    async def lock_keys_tab_a_temporary(
        self,
        delay_time: int,
        delay_unit: lcn_defs.TimeUnit,
        states: list[lcn_defs.KeyLockStateModifier],
    ) -> bool:
        """Send a command to lock keys in table A temporary.

        :param    int        delay_time:    Time to lock keys
        :param    TimeUnit   delay_unit:    Unit of time
        :param    list(bool) states:        The 8 lock states of the keys as
                                            list (locked=True, unlocked=False)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            self.wants_ack,
            PckGenerator.lock_keys_tab_a_temporary(delay_time, delay_unit, states),
        )

    async def clear_dyn_text(self, row_id: int) -> bool:
        """Clear previously sent dynamic text.

        :param    int    row_id:    Row id 0..3

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.dyn_text(row_id, "")

    async def dyn_text(self, row_id: int, text: str) -> bool:
        """Send dynamic text to a module.

        :param    int    row_id:    Row id 0..3
        :param    str    text:      Text to send (up to 60 bytes)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        encoded_text = text.encode(lcn_defs.LCN_ENCODING)
        parts = [encoded_text[12 * part : 12 * part + 12] for part in range(5)]
        result = True
        for part_id, part in enumerate(parts):
            result &= await self.send_command(
                self.wants_ack,
                PckGenerator.dyn_text_part(row_id, part_id, part),
            )
        return result

    async def beep(self, sound: lcn_defs.BeepSound, count: int) -> bool:
        """Send a command to make count number of beep sounds.

        :param    BeepSound sound:  Beep sound style
        :param    int       count:  Number of beeps (1..15)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(self.wants_ack, PckGenerator.beep(sound, count))

    async def ping(self) -> bool:
        """Send a command that does nothing and request an acknowledgement."""
        return await self.send_command(True, PckGenerator.empty())

    async def pck(self, pck: str) -> bool:
        """Send arbitrary PCK command.

        :param    str    pck:    PCK command

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(self.wants_ack, pck)

    # ##
    # ## Methods for handling input objects
    # ##

    def register_for_inputs(
        self, callback: Callable[[inputs.Input], None]
    ) -> Callable[..., None]:
        """Register a function for callback on PCK message received.

        Returns a function to unregister the callback.
        """
        self.input_callbacks.add(callback)
        return lambda callback=callback: self.input_callbacks.remove(callback)

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Is called by input object's process method.

        Method to handle incoming commands for this specific module (status,
        toggle_output, switch_relays, ...)
        """
        if isinstance(inp, inputs.ModAck):
            await self.on_ack(inp.code)
            return None

        for input_callback in self.input_callbacks:
            input_callback(inp)

    async def dump_details(self) -> dict[str, Any]:
        """Dump detailed information about this module."""
        is_local_segment = self.addr.seg_id in (0, self.conn.local_seg_id)
        return {
            "segment": self.addr.seg_id,
            "address": self.addr.addr_id,
            "is_local_segment": is_local_segment,
            "serials": {
                "hardware_serial": f"{self.serials.hardware_serial:10X}",
                "manu": f"{self.serials.manu:02X}",
                "software_serial": f"{self.serials.software_serial:06X}",
                "hardware_type": f"{self.serials.hardware_type.value:d}",
                "hardware_name": self.serials.hardware_type.description,
            },
            "name": await self.request_name(),
            "comment": await self.request_comment(),
            "oem_text": await self.request_oem_text(),
            "groups": {
                "static": sorted(
                    addr.addr_id
                    for addr in await self.request_group_memberships(dynamic=False)
                ),
                "dynamic": sorted(
                    addr.addr_id
                    for addr in await self.request_group_memberships(dynamic=True)
                ),
            },
        }

    # ##
    # ## Methods for requesting module properties and status
    # ##

    async def _request_device_properties(self) -> None:
        """Request module properties (serials)."""
        self.serials = await self.request_serials()
        self._serials_known.set()

    # Request status methods

    async def request_status_output(
        self, output_port: lcn_defs.OutputPort, max_age: int = 0
    ) -> inputs.ModStatusOutput | None:
        """Request the status of an output port from a module."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return None

        result = await self.status_requester.request(
            response_type=inputs.ModStatusOutput,
            request_pck=PckGenerator.request_output_status(output_id=output_port.value),
            max_age=max_age,
            output_id=output_port.value,
        )

        return cast(inputs.ModStatusOutput, result)

    async def request_status_relays(
        self, max_age: int = 0
    ) -> inputs.ModStatusRelays | None:
        """Request the status of relays from a module."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return None

        result = await self.status_requester.request(
            response_type=inputs.ModStatusRelays,
            request_pck=PckGenerator.request_relays_status(),
            max_age=max_age,
        )

        return cast(inputs.ModStatusRelays, result)

    async def request_status_motor_position(
        self,
        motor: lcn_defs.MotorPort,
        positioning_mode: lcn_defs.MotorPositioningMode,
        max_age: int = 0,
    ) -> inputs.ModStatusMotorPositionBS4 | None:
        """Request the status of motor positions from a module."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return None

        if motor not in (
            lcn_defs.MotorPort.MOTOR1,
            lcn_defs.MotorPort.MOTOR2,
            lcn_defs.MotorPort.MOTOR3,
            lcn_defs.MotorPort.MOTOR4,
        ):
            _LOGGER.debug(
                "Only MOTOR1 to MOTOR4 are supported for motor position requests."
            )
            return None
        if positioning_mode != lcn_defs.MotorPositioningMode.BS4:
            _LOGGER.debug("Only BS4 mode is supported for motor position requests.")
            return None

        result = await self.status_requester.request(
            response_type=inputs.ModStatusMotorPositionBS4,
            request_pck=PckGenerator.request_motor_position_status(motor.value // 2),
            max_age=max_age,
            motor=motor.value,
        )

        return cast(inputs.ModStatusMotorPositionBS4, result)

    async def request_status_binary_sensors(
        self, max_age: int = 0
    ) -> inputs.ModStatusBinSensors | None:
        """Request the status of binary sensors from a module."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return None

        result = await self.status_requester.request(
            response_type=inputs.ModStatusBinSensors,
            request_pck=PckGenerator.request_bin_sensors_status(),
            max_age=max_age,
        )

        return cast(inputs.ModStatusBinSensors, result)

    async def request_status_variable(
        self,
        variable: lcn_defs.Var,
        max_age: int = 0,
    ) -> inputs.ModStatusVar | None:
        """Request the status of a variable from a module."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return None

        # do not use buffered response for old modules
        # (variable response is typeless)
        if self.serials.software_serial < 0x170206:
            max_age = 0

        result = await self.status_requester.request(
            response_type=inputs.ModStatusVar,
            request_pck=PckGenerator.request_var_status(
                variable, self.serials.software_serial
            ),
            max_age=max_age,
            var=variable,
        )

        result = cast(inputs.ModStatusVar, result)
        if result:
            if result.orig_var == lcn_defs.Var.UNKNOWN:
                # Response without type (%Msssaaa.wwwww)
                result.var = variable
        return result

    async def request_status_led_and_logic_ops(
        self, max_age: int = 0
    ) -> inputs.ModStatusLedsAndLogicOps | None:
        """Request the status of LEDs and logic operations from a module."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return None

        result = await self.status_requester.request(
            response_type=inputs.ModStatusLedsAndLogicOps,
            request_pck=PckGenerator.request_leds_and_logic_ops(),
            max_age=max_age,
        )

        return cast(inputs.ModStatusLedsAndLogicOps, result)

    async def request_status_locked_keys(
        self, max_age: int = 0
    ) -> inputs.ModStatusKeyLocks | None:
        """Request the status of locked keys from a module."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return None

        result = await self.status_requester.request(
            response_type=inputs.ModStatusKeyLocks,
            request_pck=PckGenerator.request_key_lock_status(),
            max_age=max_age,
        )

        return cast(inputs.ModStatusKeyLocks, result)

    # Request module properties

    async def request_serials(self, max_age: int = 0) -> Serials:
        """Request module serials."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return Serials(-1, -1, -1, lcn_defs.HardwareType.UNKNOWN)

        result = cast(
            inputs.ModSn | None,
            await self.status_requester.request(
                response_type=inputs.ModSn,
                request_pck=PckGenerator.request_serial(),
                max_age=max_age,
            ),
        )

        if result is None:
            return Serials(-1, -1, -1, lcn_defs.HardwareType.UNKNOWN)
        return Serials(
            result.hardware_serial,
            result.manu,
            result.software_serial,
            result.hardware_type,
        )

    async def request_name(self, max_age: int = 0) -> str | None:
        """Request module name."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return None

        coros = [
            self.status_requester.request(
                response_type=inputs.ModNameComment,
                request_pck=PckGenerator.request_name(block_id),
                max_age=max_age,
                command="N",
                block_id=block_id,
            )
            for block_id in [0, 1]
        ]

        coro_results = [await coro for coro in coros]
        if not all(coro_results):
            return None
        results = cast(list[inputs.ModNameComment], coro_results)
        name = "".join([result.text for result in results if result])
        return name

    async def request_comment(self, max_age: int = 0) -> str | None:
        """Request module name."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return None

        coros = [
            self.status_requester.request(
                response_type=inputs.ModNameComment,
                request_pck=PckGenerator.request_comment(block_id),
                max_age=max_age,
                command="K",
                block_id=block_id,
            )
            for block_id in [0, 1, 2]
        ]

        coro_results = [await coro for coro in coros]
        if not all(coro_results):
            return None
        results = cast(list[inputs.ModNameComment], coro_results)
        name = "".join([result.text for result in results if result])
        return name

    async def request_oem_text(self, max_age: int = 0) -> str | None:
        """Request module name."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return None

        coros = [
            self.status_requester.request(
                response_type=inputs.ModNameComment,
                request_pck=PckGenerator.request_oem_text(block_id),
                max_age=max_age,
                command="O",
                block_id=block_id,
            )
            for block_id in [0, 1, 2, 3]
        ]

        coro_results = [await coro for coro in coros]
        if not all(coro_results):
            return None
        results = cast(list[inputs.ModNameComment], coro_results)
        name = "".join([result.text for result in results if result])
        return name

    async def request_group_memberships(
        self, dynamic: bool = False, max_age: int = 0
    ) -> set[LcnAddr]:
        """Request module static/dynamic group memberships."""
        if self.addr.is_group:
            _LOGGER.info("Status requests are not supported for groups.")
            return set()

        result = await self.status_requester.request(
            response_type=inputs.ModStatusGroups,
            request_pck=(
                PckGenerator.request_group_membership_dynamic()
                if dynamic
                else PckGenerator.request_group_membership_static()
            ),
            max_age=max_age,
            dynamic=dynamic,
        )

        return set(cast(inputs.ModStatusGroups, result).groups)
