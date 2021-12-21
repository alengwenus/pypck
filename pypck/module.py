"""Copyright (c) 2006-2020 by the respective copyright holders.

See the NOTICE file(s) distributed with this work for additional
information.

This program and the accompanying materials are made available under the
terms of the Eclipse Public License 2.0 which is available at
http://www.eclipse.org/legal/epl-2.0

SPDX-License-Identifier: EPL-2.0

Contributors:
  Andre Lengwenus - port to Python and further improvements
  Tobias Juettner - initial LCN binding for openHAB (Java)
"""

import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Union,
    cast,
)

from pypck import inputs, lcn_defs
from pypck.helpers import TaskRegistry
from pypck.lcn_addr import LcnAddr
from pypck.pck_commands import PckGenerator
from pypck.request_handlers import (
    CommentRequestHandler,
    GroupMembershipDynamicRequestHandler,
    GroupMembershipStaticRequestHandler,
    NameRequestHandler,
    OemTextRequestHandler,
    SerialRequestHandler,
    StatusRequestsHandler,
)

if TYPE_CHECKING:
    from pypck.connection import PchkConnectionManager


class AbstractConnection:
    """Organizes communication with a specific module.

    Sends status requests to the connection and handles status responses.
    """

    def __init__(
        self,
        conn: "PchkConnectionManager",
        addr: LcnAddr,
        software_serial: Optional[int] = None,
    ):
        """Construct AbstractConnection instance."""
        self.conn = conn
        self.addr = addr

        if software_serial is None:
            software_serial = -1
        self._software_serial: int = software_serial

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

    @property
    def serials(self) -> Dict[str, Union[int, lcn_defs.HardwareType]]:
        """Return serial numbers of a module."""
        return {
            "hardware_serial": -1,
            "manu": -1,
            "software_serial": self._software_serial,
            "hardware_type": lcn_defs.HardwareType.UNKNOWN,
        }

    @property
    def hardware_serial(self) -> int:
        """Get the hardware serial number."""
        return cast(int, self.serials["hardware_serial"])

    @property
    def software_serial(self) -> int:
        """Get the software serial number."""
        return cast(int, self.serials["software_serial"])

    @property
    def manu(self) -> int:
        """Get the manufacturing number."""
        return cast(int, self.serials["manu"])

    @property
    def hardware_type(self) -> lcn_defs.HardwareType:
        """Get the hardware type."""
        return cast(lcn_defs.HardwareType, self.serials["hardware_type"])

    @property
    def serial_known(self) -> Awaitable[bool]:
        """Check if serials have already been received from module."""
        event = asyncio.Event()
        event.set()
        return event.wait()

    async def request_serials(self) -> Dict[str, Union[int, lcn_defs.HardwareType]]:
        """Request module serials."""
        return self.serials

    async def send_command(self, wants_ack: bool, pck: Union[str, bytes]) -> bool:
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
            not self.is_group, PckGenerator.dim_output(output_id, percent, ramp)
        )

    async def dim_all_outputs(
        self, percent: float, ramp: int, software_serial: Optional[int] = None
    ) -> bool:
        """Send a dim command for all output-ports.

        :param    float  percent:           Brightness in percent 0..100
        :param    int    ramp:              Ramp time in milliseconds.
        :param    int    software_serial:   The minimum firmware version expected by
                                            any receiving module.

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        if software_serial is None:
            await self.serial_known
            software_serial = self.software_serial

        return await self.send_command(
            not self.is_group,
            PckGenerator.dim_all_outputs(percent, ramp, software_serial),
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
            not self.is_group, PckGenerator.rel_output(output_id, percent)
        )

    async def toggle_output(self, output_id: int, ramp: int) -> bool:
        """Send a command that toggles a single output-port.

        Toggle mode: (on->off, off->on).

        :param    int    output_id:    Output id 0..3
        :param    int    ramp:         Ramp time in milliseconds

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            not self.is_group, PckGenerator.toggle_output(output_id, ramp)
        )

    async def toggle_all_outputs(self, ramp: int) -> bool:
        """Generate a command that toggles all output-ports.

        Toggle Mode:  (on->off, off->on).

        :param    int    ramp:        Ramp time in milliseconds

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            not self.is_group, PckGenerator.toggle_all_outputs(ramp)
        )

    async def control_relays(self, states: List[lcn_defs.RelayStateModifier]) -> bool:
        """Send a command to control relays.

        :param    states:   The 8 modifiers for the relay states as alist
        :type     states:   list(:class:`~pypck.lcn_defs.RelayStateModifier`)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            not self.is_group, PckGenerator.control_relays(states)
        )

    async def control_relays_timer(
        self, time_msec: int, states: List[lcn_defs.RelayStateModifier]
    ) -> bool:
        """Send a command to control relays.

        :param      int     time_msec:  Duration of timer in milliseconds
        :param    states:   The 8 modifiers for the relay states as alist
        :type     states:   list(:class:`~pypck.lcn_defs.RelayStateModifier`)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            not self.is_group, PckGenerator.control_relays_timer(time_msec, states)
        )

    async def control_motors_relays(
        self, states: List[lcn_defs.MotorStateModifier]
    ) -> bool:
        """Send a command to control motors via relays.

        :param    states:   The 4 modifiers for the cover states as a list
        :type     states:   list(:class: `~pypck.lcn-defs.MotorStateModifier`)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            not self.is_group, PckGenerator.control_motors_relays(states)
        )

    async def control_motors_outputs(
        self,
        state: lcn_defs.MotorStateModifier,
        reverse_time: Optional[lcn_defs.MotorReverseTime] = None,
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
            not self.is_group,
            PckGenerator.control_motors_outputs(state, reverse_time),
        )

    async def activate_scene(
        self,
        register_id: int,
        scene_id: int,
        output_ports: Sequence[lcn_defs.OutputPort] = (),
        relay_ports: Sequence[lcn_defs.RelayPort] = (),
        ramp: Optional[int] = None,
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
            not self.is_group, PckGenerator.change_scene_register(register_id)
        )
        if not success:
            return False

        coros = []
        if output_ports:
            coros.append(
                self.send_command(
                    not self.is_group,
                    PckGenerator.activate_scene_output(scene_id, output_ports, ramp),
                )
            )
        if relay_ports:
            coros.append(
                self.send_command(
                    not self.is_group,
                    PckGenerator.activate_scene_relay(scene_id, relay_ports),
                )
            )
        results = await asyncio.gather(*coros)
        return all(results)

    async def store_scene(
        self,
        register_id: int,
        scene_id: int,
        output_ports: Sequence[lcn_defs.OutputPort] = (),
        relay_ports: Sequence[lcn_defs.RelayPort] = (),
        ramp: Optional[int] = None,
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
            not self.is_group, PckGenerator.change_scene_register(register_id)
        )

        if not success:
            return False

        coros = []
        if output_ports:
            coros.append(
                self.send_command(
                    not self.is_group,
                    PckGenerator.store_scene_output(scene_id, output_ports, ramp),
                )
            )
        if relay_ports:
            coros.append(
                self.send_command(
                    not self.is_group,
                    PckGenerator.store_scene_relay(scene_id, relay_ports),
                )
            )
        results = await asyncio.gather(*coros)
        return all(results)

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
            not self.is_group,
            PckGenerator.store_scene_outputs_direct(
                register_id, scene_id, percents, ramps
            ),
        )

    async def var_abs(
        self,
        var: lcn_defs.Var,
        value: Union[float, lcn_defs.VarValue],
        unit: lcn_defs.VarUnit = lcn_defs.VarUnit.NATIVE,
        software_serial: Optional[int] = None,
    ) -> bool:
        """Send a command to set the absolute value to a variable.

        :param     Var        var:      Variable
        :param     float      value:    Absolute value to set
        :param     VarUnit    unit:     Unit of variable

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        if not isinstance(value, lcn_defs.VarValue):
            value = lcn_defs.VarValue.from_var_unit(value, unit, True)

        if software_serial is None:
            await self.serial_known
            software_serial = self.software_serial

        if lcn_defs.Var.to_var_id(var) != -1:
            # Absolute commands for variables 1-12 are not supported
            if self.addr_id == 4 and self.is_group:
                # group 4 are status messages
                return await self.send_command(
                    not self.is_group,
                    PckGenerator.update_status_var(var, value.to_native()),
                )
            # We fake the missing command by using reset and relative
            # commands.
            success = await self.send_command(
                not self.is_group, PckGenerator.var_reset(var, software_serial)
            )
            if not success:
                return False
            return await self.send_command(
                not self.is_group,
                PckGenerator.var_rel(
                    var, lcn_defs.RelVarRef.CURRENT, value.to_native(), software_serial
                ),
            )
        return await self.send_command(
            not self.is_group, PckGenerator.var_abs(var, value.to_native())
        )

    async def var_reset(
        self, var: lcn_defs.Var, software_serial: Optional[int] = None
    ) -> bool:
        """Send a command to reset the variable value.

        :param    Var    var:    Variable

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        if software_serial is None:
            await self.serial_known
            software_serial = self.software_serial

        return await self.send_command(
            not self.is_group, PckGenerator.var_reset(var, software_serial)
        )

    async def var_rel(
        self,
        var: lcn_defs.Var,
        value: Union[float, lcn_defs.VarValue],
        unit: lcn_defs.VarUnit = lcn_defs.VarUnit.NATIVE,
        value_ref: lcn_defs.RelVarRef = lcn_defs.RelVarRef.CURRENT,
        software_serial: Optional[int] = None,
    ) -> bool:
        """Send a command to change the value of a variable.

        :param     Var        var:      Variable
        :param     float      value:    Relative value to add (may also be
                                        negative)
        :param     VarUnit    unit:     Unit of variable

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        if not isinstance(value, lcn_defs.VarValue):
            value = lcn_defs.VarValue.from_var_unit(value, unit, True)

        if software_serial is None:
            await self.serial_known
            software_serial = self.software_serial

        return await self.send_command(
            not self.is_group,
            PckGenerator.var_rel(var, value_ref, value.to_native(), software_serial),
        )

    async def lock_regulator(self, reg_id: int, state: bool) -> bool:
        """Send a command to lock a regulator.

        :param    int        reg_id:        Regulator id
        :param    bool       state:         Lock state (locked=True,
                                            unlocked=False)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            not self.is_group, PckGenerator.lock_regulator(reg_id, state)
        )

    async def control_led(
        self, led: lcn_defs.LedPort, state: lcn_defs.LedStatus
    ) -> bool:
        """Send a command to control a led.

        :param    LedPort      led:        Led port
        :param    LedStatus    state:      Led status
        """
        return await self.send_command(
            not self.is_group, PckGenerator.control_led(led.value, state)
        )

    async def send_keys(
        self, keys: List[List[bool]], cmd: lcn_defs.SendKeyCommand
    ) -> List[bool]:
        """Send a command to send keys.

        :param    list(bool)[4][8]    keys:    2d-list with [table_id][key_id]
                                               bool values, if command should
                                               be sent to specific key
        :param    SendKeyCommand      cmd:     command to send for each table

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      list of bool
        """
        coros = []
        for table_id, key_states in enumerate(keys):
            if True in key_states:
                cmds = [lcn_defs.SendKeyCommand.DONTSEND] * 4
                cmds[table_id] = cmd
                coros.append(
                    self.send_command(
                        not self.is_group, PckGenerator.send_keys(cmds, key_states)
                    )
                )
        results = await asyncio.gather(*coros)
        return results

    async def send_keys_hit_deferred(
        self, keys: List[List[bool]], delay_time: int, delay_unit: lcn_defs.TimeUnit
    ) -> List[bool]:
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
        coros = []
        for table_id, key_states in enumerate(keys):
            if True in key_states:
                coros.append(
                    self.send_command(
                        not self.is_group,
                        PckGenerator.send_keys_hit_deferred(
                            table_id, delay_time, delay_unit, key_states
                        ),
                    )
                )
        results = await asyncio.gather(*coros)
        return results

    async def lock_keys(
        self, table_id: int, states: List[lcn_defs.KeyLockStateModifier]
    ) -> bool:
        """Send a command to lock keys.

        :param    int                     table_id:  Table id: 0..3
        :param    keyLockStateModifier    states:    The 8 modifiers for the
                                                     key lock states as a list

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            not self.is_group, PckGenerator.lock_keys(table_id, states)
        )

    async def lock_keys_tab_a_temporary(
        self, delay_time: int, delay_unit: lcn_defs.TimeUnit, states: List[bool]
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
            not self.is_group,
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
        coros = []
        parts = [encoded_text[12 * part : 12 * part + 12] for part in range(5)]
        for part_id, part in enumerate(parts):
            coros.append(
                self.send_command(
                    not self.is_group,
                    PckGenerator.dyn_text_part(row_id, part_id, part),
                )
            )
        results = await asyncio.gather(*coros)
        return all(results)

    async def beep(self, sound: lcn_defs.BeepSound, count: int) -> bool:
        """Send a command to make count number of beep sounds.

        :param    BeepSound sound:  Beep sound style
        :param    int       count:  Number of beeps (1..15)

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(
            not self.is_group, PckGenerator.beep(sound, count)
        )

    async def ping(self) -> bool:
        """Send a command that does nothing and request an acknowledgement."""
        return await self.send_command(True, PckGenerator.empty())

    async def pck(self, pck: str) -> bool:
        """Send arbitrary PCK command.

        :param    str    pck:    PCK command

        :returns:    True if command was sent successfully, False otherwise
        :rtype:      bool
        """
        return await self.send_command(not self.is_group, pck)


class GroupConnection(AbstractConnection):
    """Organizes communication with a specific group.

    It is assumed that all modules within this group are newer than FW170206
    """

    def __init__(
        self,
        conn: "PchkConnectionManager",
        addr: LcnAddr,
        software_serial: int = 0x170206,
    ):
        """Construct GroupConnection instance."""
        assert addr.is_group
        super().__init__(conn, addr, software_serial=software_serial)

    async def var_abs(
        self,
        var: lcn_defs.Var,
        value: Union[float, lcn_defs.VarValue],
        unit: lcn_defs.VarUnit = lcn_defs.VarUnit.NATIVE,
        software_serial: Optional[int] = None,
    ) -> bool:
        """Send a command to set the absolute value to a variable.

        :param     Var        var:      Variable
        :param     float      value:    Absolute value to set
        :param     VarUnit    unit:     Unit of variable
        """
        coros = []
        # for new modules (>=0x170206)
        coros.append(super().var_abs(var, value, unit, 0x170206))

        # for old modules (<0x170206)
        if var in [
            lcn_defs.Var.TVAR,
            lcn_defs.Var.R1VAR,
            lcn_defs.Var.R2VAR,
            lcn_defs.Var.R1VARSETPOINT,
            lcn_defs.Var.R2VARSETPOINT,
        ]:
            coros.append(super().var_abs(var, value, unit, 0x000000))
        results = await asyncio.gather(*coros)
        return all(results)

    async def var_reset(
        self, var: lcn_defs.Var, software_serial: Optional[int] = None
    ) -> bool:
        """Send a command to reset the variable value.

        :param    Var    var:    Variable
        """
        coros = []
        coros.append(super().var_reset(var, 0x170206))
        if var in [
            lcn_defs.Var.TVAR,
            lcn_defs.Var.R1VAR,
            lcn_defs.Var.R2VAR,
            lcn_defs.Var.R1VARSETPOINT,
            lcn_defs.Var.R2VARSETPOINT,
        ]:
            coros.append(super().var_reset(var, 0))
        results = await asyncio.gather(*coros)
        return all(results)

    async def var_rel(
        self,
        var: lcn_defs.Var,
        value: Union[float, lcn_defs.VarValue],
        unit: lcn_defs.VarUnit = lcn_defs.VarUnit.NATIVE,
        value_ref: lcn_defs.RelVarRef = lcn_defs.RelVarRef.CURRENT,
        software_serial: Optional[int] = None,
    ) -> bool:
        """Send a command to change the value of a variable.

        :param     Var        var:      Variable
        :param     float      value:    Relative value to add (may also be
                                        negative)
        :param     VarUnit    unit:     Unit of variable
        """
        coros = []
        coros.append(super().var_rel(var, value, software_serial=0x170206))
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
            coros.append(super().var_rel(var, value, software_serial=0))
        results = await asyncio.gather(*coros)
        return all(results)

    async def activate_status_request_handler(self, item: Any) -> None:
        """Activate a specific TimeoutRetryHandler for status requests."""
        await self.conn.segment_scan_completed_event.wait()

    async def activate_status_request_handlers(self) -> None:
        """Activate all TimeoutRetryHandlers for status requests."""
        # self.request_serial.activate()
        await self.conn.segment_scan_completed_event.wait()


class ModuleConnection(AbstractConnection):
    """Organizes communication with a specific module or group."""

    def __init__(
        self,
        conn: "PchkConnectionManager",
        addr: LcnAddr,
        activate_status_requests: bool = False,
        has_s0_enabled: bool = False,
        software_serial: Optional[int] = None,
    ):
        """Construct ModuleConnection instance."""
        assert not addr.is_group
        super().__init__(conn, addr, software_serial=software_serial)
        self.activate_status_requests = activate_status_requests
        self.has_s0_enabled = has_s0_enabled

        self.input_callbacks: Set[Callable[[inputs.Input], None]] = set()

        # List of queued acknowledge codes from the LCN modules.
        self.acknowledges: "asyncio.Queue[int]" = asyncio.Queue()

        # RequestHandlers
        num_tries: int = self.conn.settings["NUM_TRIES"]
        timeout_msec: int = self.conn.settings["DEFAULT_TIMEOUT_MSEC"]

        # Serial Number request
        self.serials_request_handler = SerialRequestHandler(
            self,
            num_tries,
            timeout_msec,
            software_serial=software_serial,
        )

        # Name, Comment, OemText requests
        self.name_request_handler = NameRequestHandler(self, num_tries, timeout_msec)
        self.comment_request_handler = CommentRequestHandler(
            self, num_tries, timeout_msec
        )
        self.oem_text_request_handler = OemTextRequestHandler(
            self, num_tries, timeout_msec
        )

        # Group membership request
        self.static_groups_request_handler = GroupMembershipStaticRequestHandler(
            self, num_tries, timeout_msec
        )
        self.dynamic_groups_request_handler = GroupMembershipDynamicRequestHandler(
            self, num_tries, timeout_msec
        )

        self.status_requests_handler = StatusRequestsHandler(self)
        if self.activate_status_requests:
            self.task_registry.create_task(self.activate_status_request_handlers())

    async def send_command(self, wants_ack: bool, pck: Union[str, bytes]) -> bool:
        """Send a command to the module represented by this class.

        :param    bool    wants_ack:    Also send a request for acknowledge.
        :param    str     pck:          PCK command (without header).
        """
        if wants_ack:
            return await self.send_command_with_ack(pck)

        return await super().send_command(False, pck)

    # ##
    # ## Retry logic if an acknowledge is requested
    # ##

    async def send_command_with_ack(self, pck: Union[str, bytes]) -> bool:
        """Send a PCK command and ensure receiving of an acknowledgement.

        Resends the PCK command if no acknowledgement has been received
        within timeout.

        :param    str     pck:          PCK command (without header).
        :returns:    True if acknowledge was received, False otherwise
        :rtype:      bool
        """
        count = 0
        while count < self.conn.settings["NUM_TRIES"]:
            await super().send_command(True, pck)
            try:
                code = await asyncio.wait_for(
                    self.acknowledges.get(),
                    timeout=self.conn.settings["DEFAULT_TIMEOUT_MSEC"] / 1000,
                )
            except asyncio.TimeoutError:
                count += 1
                continue
            if code == -1:
                return True
            break
        return False

    async def on_ack(self, code: int = -1) -> None:
        """Is called whenever an acknowledge is received from the LCN module.

        :param     int    code:           The LCN internal code. -1 means
                                          "positive" acknowledge
        """
        await self.acknowledges.put(code)

    async def activate_status_request_handler(self, item: Any) -> None:
        """Activate a specific TimeoutRetryHandler for status requests."""
        self.task_registry.create_task(self.status_requests_handler.activate(item))

    async def activate_status_request_handlers(self) -> None:
        """Activate all TimeoutRetryHandlers for status requests."""
        self.task_registry.create_task(
            self.status_requests_handler.activate_all(activate_s0=self.has_s0_enabled)
        )

    async def cancel_status_request_handler(self, item: Any) -> None:
        """Cancel a specific TimeoutRetryHandler for status requests."""
        await self.status_requests_handler.cancel(item)

    async def cancel_status_request_handlers(self) -> None:
        """Canecl all TimeoutRetryHandlers for status requests."""
        await self.status_requests_handler.cancel_all()

    async def cancel_requests(self) -> None:
        """Cancel all TimeoutRetryHandlers."""
        await self.cancel_status_request_handlers()
        await self.serials_request_handler.cancel()
        await self.name_request_handler.cancel()
        await self.oem_text_request_handler.cancel()
        await self.static_groups_request_handler.cancel()
        await self.dynamic_groups_request_handler.cancel()

    def set_s0_enabled(self, s0_enabled: bool) -> None:
        """Set the activation status for S0 variables.

        :param     bool    s0_enabled:   If True, a BU4L has to be connected
                                         to the hardware module and S0 mode
                                         has to be activated in LCN-PRO.
        """
        self.has_s0_enabled = s0_enabled

    def get_s0_enabled(self) -> bool:
        """Get the activation status for S0 variables."""
        return self.has_s0_enabled

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

        # handle typeless variable responses
        if isinstance(inp, inputs.ModStatusVar):
            inp = self.status_requests_handler.preprocess_modstatusvar(inp)

        for input_callback in self.input_callbacks:
            input_callback(inp)

    def dump_details(self) -> Dict[str, Any]:
        """Dump detailed information about this module."""
        is_local_segment = self.addr.seg_id in (0, self.conn.local_seg_id)
        return {
            "segment": self.addr.seg_id,
            "address": self.addr.addr_id,
            "is_local_segment": is_local_segment,
            "serials": {
                "hardware_serial": f"{self.hardware_serial:10X}",
                "manu": f"{self.manu:02X}",
                "software_serial": f"{self.software_serial:06X}",
                "hardware_type": f"{self.hardware_type.value:d}",
                "hardware_name": self.hardware_type.description,
            },
            "name": self.name,
            "comment": self.comment,
            "oem_text": self.oem_text,
            "groups": {
                "static": sorted(addr.addr_id for addr in self.static_groups),
                "dynamic": sorted(addr.addr_id for addr in self.dynamic_groups),
            },
        }

    # ##
    # ## Requests
    # ##

    # ## properties

    @property
    def serials(self) -> Dict[str, Union[int, lcn_defs.HardwareType]]:
        """Return serials number information."""
        return self.serials_request_handler.serials

    @property
    def name(self) -> str:
        """Return stored name."""
        return self.name_request_handler.name

    @property
    def comment(self) -> str:
        """Return stored comments."""
        return self.comment_request_handler.comment

    @property
    def oem_text(self) -> List[str]:
        """Return stored OEM text."""
        return self.oem_text_request_handler.oem_text

    @property
    def static_groups(self) -> Set[LcnAddr]:
        """Return static group membership."""
        return self.static_groups_request_handler.groups

    @property
    def dynamic_groups(self) -> Set[LcnAddr]:
        """Return dynamic group membership."""
        return self.dynamic_groups_request_handler.groups

    @property
    def groups(self) -> Set[LcnAddr]:
        """Return static and dynamic group membership."""
        return self.static_groups | self.dynamic_groups

    # ## future properties

    @property
    def serial_known(self) -> Awaitable[bool]:
        """Check if serials have already been received from module."""
        return self.serials_request_handler.serial_known.wait()

    async def request_serials(self) -> Dict[str, Union[int, lcn_defs.HardwareType]]:
        """Request module serials."""
        return await self.serials_request_handler.request()

    async def request_name(self) -> str:
        """Request module name."""
        return await self.name_request_handler.request()

    async def request_comment(self) -> str:
        """Request comments from a module."""
        return await self.comment_request_handler.request()

    async def request_oem_text(self) -> List[str]:
        """Request OEM text from a module."""
        return await self.oem_text_request_handler.request()

    async def request_static_groups(self) -> Set[LcnAddr]:
        """Request module static group memberships."""
        return set(await self.static_groups_request_handler.request())

    async def request_dynamic_groups(self) -> Set[LcnAddr]:
        """Request module dynamic group memberships."""
        return set(await self.dynamic_groups_request_handler.request())

    async def request_groups(self) -> Set[LcnAddr]:
        """Request module group memberships."""
        static_groups, dynamic_groups = await asyncio.gather(
            self.static_groups_request_handler.request(),
            self.dynamic_groups_request_handler.request(),
        )
        return static_groups | dynamic_groups
