"""Copyright (c) 2006-2018 by the respective copyright holders.

All rights reserved. This program and the accompanying materials
are made available under the terms of the Eclipse Public License v1.0
which accompanies this distribution, and is available at
http://www.eclipse.org/legal/epl-v10.html

Contributors:
  Andre Lengwenus - port to Python and further improvements
  Tobias Juettner - initial LCN binding for openHAB (Java)
"""

import asyncio
from asyncio import Task
from collections import deque
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from pypck import inputs, lcn_defs
from pypck.lcn_addr import LcnAddr
from pypck.pck_commands import PckGenerator
from pypck.timeout_retry import DEFAULT_TIMEOUT_MSEC, TimeoutRetryHandler

if TYPE_CHECKING:
    from pypck.connection import PchkConnectionManager


class SerialRequestHandler:
    """Request handler to request serial number information from module."""

    def __init__(
        self,
        addr_conn: "ModuleConnection",
        num_tries: int = 3,
        timeout_msec: int = 1500,
        software_serial: Optional[int] = None,
    ):
        """Initialize class instance."""
        self.addr_conn = addr_conn

        self.hardware_serial = -1
        self.manu = -1
        if software_serial is None:
            software_serial = -1
        self.software_serial = software_serial
        self.hardware_type = -1

        # Serial Number request
        self.trh = TimeoutRetryHandler(num_tries, timeout_msec)
        self.trh.set_timeout_callback(self.timeout)

        # callback
        addr_conn.register_for_inputs(self.process_input)

        # events
        self.serial_known = asyncio.Event()

    def process_input(self, inp: inputs.Input) -> None:
        """Create a task to process the input object concurrently."""
        asyncio.create_task(self.async_process_input(inp))

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Process incoming input object.

        Method to handle incoming commands for this specific request handler.
        """
        if isinstance(inp, inputs.ModSn):
            self.hardware_serial = inp.serial
            self.manu = inp.manu
            self.software_serial = inp.sw_age
            self.hardware_type = inp.hw_type

            if not self.serial_known.is_set():
                self.serial_known.set()

            await self.cancel()

    def timeout(self, failed: bool = False) -> None:
        """Is called on serial request timeout."""
        if not failed:
            self.addr_conn.send_command(False, PckGenerator.request_serial())
        else:
            self.serial_known.set()

    async def request(self) -> Dict[str, int]:
        """Request serial number."""
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        self.serial_known.clear()
        self.trh.activate()
        await self.serial_known.wait()
        return self.serial

    async def cancel(self) -> None:
        """Cancel serial number request."""
        await self.trh.cancel()

    @property
    def serial(self) -> Dict[str, int]:
        """Return serial numbers of a module."""
        return {
            "hardware_serial": self.hardware_serial,
            "manu": self.manu,
            "software_serial": self.software_serial,
            "hardware_type": self.hardware_type,
        }


class NameCommentRequestHandler:
    """Request handler to request name, comment and OEM text of a module."""

    def __init__(
        self,
        addr_conn: "ModuleConnection",
        num_tries: int = 3,
        timeout_msec: int = 1500,
    ):
        """Initialize class instance."""
        self.addr_conn = addr_conn

        self._name: List[Optional[str]] = [None] * 2
        self._comment: List[Optional[str]] = [None] * 3
        self._oem_text: List[Optional[str]] = [None] * 4

        # Name requests
        self.name_trhs = []
        for block_id in range(2):
            trh = TimeoutRetryHandler(num_tries, timeout_msec)
            trh.set_timeout_callback(self.timeout_name, block_id=block_id)
            self.name_trhs.append(trh)

        self.comment_trhs = []
        for block_id in range(3):
            trh = TimeoutRetryHandler(num_tries, timeout_msec)
            trh.set_timeout_callback(self.timeout_comment, block_id=block_id)
            self.comment_trhs.append(trh)

        self.oem_text_trhs = []
        for block_id in range(4):
            trh = TimeoutRetryHandler(num_tries, timeout_msec)
            trh.set_timeout_callback(self.timeout_oem_text, block_id=block_id)
            self.oem_text_trhs.append(trh)

        # callback
        addr_conn.register_for_inputs(self.process_input)

        # events
        self.name_known = asyncio.Event()
        self.comment_known = asyncio.Event()
        self.oem_text_known = asyncio.Event()

    def process_input(self, inp: inputs.Input) -> None:
        """Create a task to process the input object concurrently."""
        asyncio.create_task(self.async_process_input(inp))

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Process incoming input object.

        Method to handle incoming commands for this specific request handler.
        """
        if isinstance(inp, inputs.ModNameComment):
            command = inp.command
            block_id = inp.block_id
            text = inp.text

            if command == "N":
                self._name[block_id] = f"{text:10s}"
                await self.cancel_name(block_id)
                if not self.name_known.is_set() and (None not in self._name):
                    self.name_known.set()
                    await self.cancel_name()

            elif command == "K":
                self._comment[block_id] = f"{text:12s}"
                await self.cancel_comment(block_id)
                if not self.comment_known.is_set() and (None not in self._comment):
                    self.comment_known.set()
                    await self.cancel_comment()

            elif command == "O":
                self._oem_text[block_id] = f"{text:12s}"
                await self.cancel_oem_text(block_id)
                if not self.oem_text_known.is_set() and (None not in self._oem_text):
                    self.oem_text_known.set()
                    await self.cancel_oem_text()

    def timeout_name(self, failed: bool = False, block_id: int = 0) -> None:
        """Is called on serial request timeout."""
        if not failed:
            self.addr_conn.send_command(False, PckGenerator.request_name(block_id))
        else:
            self.name_known.set()

    def timeout_comment(self, failed: bool = False, block_id: int = 0) -> None:
        """Is called on serial request timeout."""
        if not failed:
            self.addr_conn.send_command(False, PckGenerator.request_comment(block_id))
        else:
            self.comment_known.set()

    def timeout_oem_text(self, failed: bool = False, block_id: int = 0) -> None:
        """Is called on serial request timeout."""
        if not failed:
            self.addr_conn.send_command(False, PckGenerator.request_oem_text(block_id))
        else:
            self.oem_text_known.set()

    async def request_name(self) -> str:
        """Request name from a module."""
        self._name = [None] * 2
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        self.name_known.clear()
        for trh in self.name_trhs:
            trh.activate()
        await self.name_known.wait()
        return self.name

    async def request_comment(self) -> str:
        """Request comments from a module."""
        self._comment = [None] * 3
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        self.comment_known.clear()
        for trh in self.comment_trhs:
            trh.activate()
        await self.comment_known.wait()
        return self.comment

    async def request_oem_text(self) -> List[str]:
        """Request OEM text from a module."""
        self._oem_text = [None] * 4
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        self.oem_text_known.clear()
        for trh in self.oem_text_trhs:
            trh.activate()
        await self.oem_text_known.wait()
        return self.oem_text

    async def request(self) -> Tuple[str, str, List[str]]:
        """Request name, comments and OEM text from a module."""
        return await asyncio.gather(
            self.request_name(), self.request_comment(), self.request_oem_text()
        )

    async def cancel_name(self, block_id: Optional[int] = None) -> None:
        """Cancel name request task."""
        if block_id is None:  # cancel all
            for trh in self.name_trhs:
                await trh.cancel()
        else:
            await self.name_trhs[block_id].cancel()

    async def cancel_comment(self, block_id: Optional[int] = None) -> None:
        """Cancel comment request task."""
        if block_id is None:  # cancel all
            for trh in self.comment_trhs:
                await trh.cancel()
        else:
            await self.comment_trhs[block_id].cancel()

    async def cancel_oem_text(self, block_id: Optional[int] = None) -> None:
        """Cancel OEM text request task."""
        if block_id is None:  # cancel all
            for trh in self.oem_text_trhs:
                await trh.cancel()
        else:
            await self.oem_text_trhs[block_id].cancel()

    async def cancel(self) -> None:
        """Cancel all name, comment and OEM text request tasks."""
        await asyncio.gather(
            self.cancel_name(), self.cancel_comment(), self.cancel_oem_text()
        )

    @property
    def name(self) -> str:
        """Return stored name."""
        return "".join([block for block in self._name if block]).strip()

    @property
    def comment(self) -> str:
        """Return stored comment."""
        return "".join([block for block in self._comment if block]).strip()

    @property
    def oem_text(self) -> List[str]:
        """Return stored OEM text."""
        return [block.strip() if block else "" for block in self._oem_text]
        # return {'block{}'.format(idx):text
        #         for idx, text in enumerate(self._oem_text)}

        # return ''.join([block for block in self._oem_text if block])


class ModulePropertiesRequestHandler:
    """Manages all property requestst for serial number, name, comments, ..."""

    def __init__(
        self, addr_conn: "ModuleConnection", software_serial: Optional[int] = None
    ):
        """Construct ModulePropertiesRequestHandler."""
        self.addr_conn = addr_conn
        self.settings = addr_conn.conn.settings

        self.serial_request_task: Optional[Task[Dict[str, int]]] = None

        num_tries: int = self.settings["NUM_TRIES"]
        timeout_msec: int = self.settings["DEFAULT_TIMEOUT_MSEC"]

        # Serial Number request
        self.serials = SerialRequestHandler(
            addr_conn,
            num_tries,
            timeout_msec=timeout_msec,
            software_serial=software_serial,
        )

        # NameComment request
        self.name_comment = NameCommentRequestHandler(
            addr_conn,
            num_tries,
            timeout_msec=timeout_msec,
        )

    async def activate_all(self) -> None:
        """Activate all properties requests."""
        # software_serial is not given externally
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        if self.serials.software_serial == -1:
            self.serial_request_task = asyncio.create_task(self.serials.request())

    async def cancel_all(self) -> None:
        """Cancel all properties requests."""
        if self.serial_request_task is not None:
            self.serial_request_task.cancel()
            try:
                await self.serial_request_task
            except asyncio.CancelledError:
                pass
        await self.serials.cancel()
        await self.name_comment.cancel()


class StatusRequestsHandler:
    """Manages all status requests for variables, software version, ..."""

    def __init__(self, addr_conn: "ModuleConnection"):
        """Construct StatusRequestHandler instance."""
        self.addr_conn = addr_conn
        self.settings = addr_conn.conn.settings

        self.last_requested_var_without_type_in_response = lcn_defs.Var.UNKNOWN
        self.last_var_lock = asyncio.Lock()

        # Output-port request status (0..3)
        self.request_status_outputs = []
        for output_port in range(4):
            trh = TimeoutRetryHandler(
                -1, self.settings["MAX_STATUS_EVENTBASED_VALUEAGE_MSEC"]
            )
            trh.set_timeout_callback(self.request_status_outputs_timeout, output_port)
            self.request_status_outputs.append(trh)

        # Relay request status (all 8)
        self.request_status_relays = TimeoutRetryHandler(
            -1, self.settings["MAX_STATUS_EVENTBASED_VALUEAGE_MSEC"]
        )
        self.request_status_relays.set_timeout_callback(
            self.request_status_relays_timeout
        )

        # Binary-sensors request status (all 8)
        self.request_status_bin_sensors = TimeoutRetryHandler(
            -1, self.settings["MAX_STATUS_EVENTBASED_VALUEAGE_MSEC"]
        )
        self.request_status_bin_sensors.set_timeout_callback(
            self.request_status_bin_sensors_timeout
        )

        # Variables request status.
        # Lazy initialization: Will be filled once the firmware version is
        # known.
        self.request_status_vars = {}
        for var in lcn_defs.Var:
            if var != lcn_defs.Var.UNKNOWN:
                self.request_status_vars[var] = TimeoutRetryHandler(
                    -1, self.settings["MAX_STATUS_EVENTBASED_VALUEAGE_MSEC"]
                )
                self.request_status_vars[var].set_timeout_callback(
                    self.request_status_var_timeout, var=var
                )

        # LEDs and logic-operations request status (all 12+4).
        self.request_status_leds_and_logic_ops = TimeoutRetryHandler(
            -1, self.settings["MAX_STATUS_POLLED_VALUEAGE_MSEC"]
        )
        self.request_status_leds_and_logic_ops.set_timeout_callback(
            self.request_status_leds_and_logic_ops_timeout
        )

        # Key lock-states request status (all tables, A-D).
        self.request_status_locked_keys = TimeoutRetryHandler(
            -1, self.settings["MAX_STATUS_POLLED_VALUEAGE_MSEC"]
        )
        self.request_status_locked_keys.set_timeout_callback(
            self.request_status_locked_keys_timeout
        )

    def preprocess_modstatusvar(self, inp: inputs.ModStatusVar) -> inputs.Input:
        """Fill typeless response with last requested variable type."""
        if inp.orig_var == lcn_defs.Var.UNKNOWN:
            # Response without type (%Msssaaa.wwwww)
            inp.var = self.last_requested_var_without_type_in_response

            self.last_requested_var_without_type_in_response = lcn_defs.Var.UNKNOWN

            if self.last_var_lock.locked():
                self.last_var_lock.release()
        else:
            # Response with variable type (%Msssaaa.Avvvwww)
            inp.var = inp.orig_var

        return inp

    def request_status_outputs_timeout(
        self, failed: bool = False, output_port: int = 0
    ) -> None:
        """Is called on output status request timeout."""
        if not failed:
            self.addr_conn.send_command(
                False, PckGenerator.request_output_status(output_port)
            )

    def request_status_relays_timeout(self, failed: bool = False) -> None:
        """Is called on relay status request timeout."""
        if not failed:
            self.addr_conn.send_command(False, PckGenerator.request_relays_status())

    def request_status_bin_sensors_timeout(self, failed: bool = False) -> None:
        """Is called on binary sensor status request timeout."""
        if not failed:
            self.addr_conn.send_command(
                False, PckGenerator.request_bin_sensors_status()
            )

    async def request_status_var_timeout(
        self, failed: bool = False, var: Optional[lcn_defs.Var] = None
    ) -> None:
        """Is called on variable status request timeout."""
        assert var is not None
        # Detect if we can send immediately or if we have to wait for a
        # "typeless" response first
        has_type_in_response = lcn_defs.Var.has_type_in_response(
            var, self.addr_conn.software_serial
        )
        if not has_type_in_response:
            # Use the chance to remove a failed "typeless variable" request
            try:
                await asyncio.wait_for(self.last_var_lock.acquire(), timeout=3.0)
            except asyncio.TimeoutError:
                pass
            self.last_requested_var_without_type_in_response = var

        # Send variable request
        self.addr_conn.send_command(
            False,
            PckGenerator.request_var_status(var, self.addr_conn.software_serial),
        )

    def request_status_leds_and_logic_ops_timeout(self, failed: bool = False) -> None:
        """Is called on leds/logical ops status request timeout."""
        if not failed:
            self.addr_conn.send_command(
                False, PckGenerator.request_leds_and_logic_ops()
            )

    def request_status_locked_keys_timeout(self, failed: bool = False) -> None:
        """Is called on locked keys status request timeout."""
        if not failed:
            self.addr_conn.send_command(False, PckGenerator.request_key_lock_status())

    async def activate(self, item: Any) -> None:
        """Activate status requests for given item."""
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        # handle variables independently
        if (item in lcn_defs.Var) and (item != lcn_defs.Var.UNKNOWN):
            # wait until we know the software version
            await self.addr_conn.serial_known
            if self.addr_conn.software_serial >= 0x170206:
                timeout_msec = self.settings["MAX_STATUS_EVENTBASED_VALUEAGE_MSEC"]
            else:
                timeout_msec = self.settings["MAX_STATUS_POLLED_VALUEAGE_MSEC"]
            self.request_status_vars[item].set_timeout_msec(timeout_msec)
            self.request_status_vars[item].activate()
        elif item in lcn_defs.OutputPort:
            self.request_status_outputs[item.value].activate()
        elif item in lcn_defs.RelayPort:
            self.request_status_relays.activate()
        elif item in lcn_defs.MotorPort:
            self.request_status_relays.activate()
        elif item in lcn_defs.BinSensorPort:
            self.request_status_bin_sensors.activate()
        elif item in lcn_defs.LedPort:
            self.request_status_leds_and_logic_ops.activate()
        elif item in lcn_defs.Key:
            self.request_status_locked_keys.activate()

    async def cancel(self, item: Any) -> None:
        """Cancel status request for given item."""
        # handle variables independently
        if (item in lcn_defs.Var) and (item != lcn_defs.Var.UNKNOWN):
            await self.request_status_vars[item].cancel()
            self.last_requested_var_without_type_in_response = lcn_defs.Var.UNKNOWN
        elif item in lcn_defs.OutputPort:
            await self.request_status_outputs[item.value].cancel()
        elif item in lcn_defs.RelayPort:
            await self.request_status_relays.cancel()
        elif item in lcn_defs.MotorPort:
            await self.request_status_relays.cancel()
        elif item in lcn_defs.BinSensorPort:
            await self.request_status_bin_sensors.cancel()
        elif item in lcn_defs.LedPort:
            await self.request_status_leds_and_logic_ops.cancel()
        elif item in lcn_defs.Key:
            await self.request_status_locked_keys.cancel()

    async def activate_all(self, activate_s0: bool = False) -> None:
        """Activate all status requests."""
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        for item in (
            list(lcn_defs.OutputPort)
            + list(lcn_defs.RelayPort)
            + list(lcn_defs.BinSensorPort)
            + list(lcn_defs.LedPort)
            + list(lcn_defs.Key)
            + list(lcn_defs.Var)
        ):
            if isinstance(item, lcn_defs.Var) and item == lcn_defs.Var.UNKNOWN:
                continue
            if (
                (not activate_s0)
                and isinstance(item, lcn_defs.Var)
                and (item in lcn_defs.Var.s0s)  # type: ignore
            ):
                continue
            await self.activate(item)

    async def cancel_all(self) -> None:
        """Cancel all status requests."""
        for item in (
            list(lcn_defs.OutputPort)
            + list(lcn_defs.RelayPort)
            + list(lcn_defs.BinSensorPort)
            + list(lcn_defs.LedPort)
            + list(lcn_defs.Key)
            + list(lcn_defs.Var)
        ):
            if isinstance(item, lcn_defs.Var) and item == lcn_defs.Var.UNKNOWN:
                continue
            await self.cancel(item)


class AbstractConnection(LcnAddr):
    """Organizes communication with a specific module.

    Sends status requests to the connection and handles status responses.
    """

    def __init__(
        self,
        conn: "PchkConnectionManager",
        seg_id: int,
        addr_id: int,
        is_group: bool,
        sw_age: Optional[int] = None,
    ):
        """Construct AbstractConnection instance."""
        self.conn = conn
        super().__init__(seg_id=seg_id, addr_id=addr_id, is_group=is_group)

        self._sw_age: Optional[int] = sw_age
        self._serial: Optional[int] = None
        self._manu: Optional[int] = None
        self._hw_type: Optional[int] = None

        self.input_callbacks: List[Callable[[inputs.Input], None]] = []

    def get_sw_age(self) -> Optional[int]:
        """Return standard sw_age."""
        return self._sw_age

    def send_command(self, wants_ack: bool, pck: str) -> None:
        """Send a command to the module represented by this class.

        :param    bool    wants_ack:    Also send a request for acknowledge.
        :param    str     pck:          PCK command (without header).
        """
        self.conn.send_command(
            PckGenerator.generate_address_header(
                self, self.conn.local_seg_id, wants_ack
            )
            + pck
        )

    # ##
    # ## Methods for handling input objects
    # ##

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Is called by input object's process method.

        Method to handle incoming commands for this specific module (status,
        toggle_output, switch_relays, ...)
        """
        for input_callback in self.input_callbacks:
            input_callback(inp)

    def register_for_inputs(
        self, callback: Callable[[inputs.Input], None]
    ) -> Callable[..., None]:
        """Register a function for callback on PCK message received.

        Returns a function to unregister the callback.
        """
        self.input_callbacks.append(callback)
        return lambda callback=callback: self.input_callbacks.remove(callback)

    # ##
    # ## Methods for sending PCK commands
    # ##

    def dim_output(self, output_id: int, percent: float, ramp: int) -> None:
        """Send a dim command for a single output-port.

        :param    int    output_id:    Output id 0..3
        :param    float    percent:      Brightness in percent 0..100
        :param    int    ramp:         Ramp time in milliseconds
        """
        self.send_command(
            not self.is_group(), PckGenerator.dim_ouput(output_id, percent, ramp)
        )

    def dim_all_outputs(self, percent: float, ramp: int, is1805: bool = False) -> None:
        """Send a dim command for all output-ports.

        :param    float    percent:    Brightness in percent 0..100
        :param    int    ramp:       Ramp time in milliseconds.
        :param    bool   is1805:     True if the target module's firmware is
                                     180501 or newer, otherwise False
        """
        self.send_command(
            not self.is_group(), PckGenerator.dim_all_outputs(percent, ramp, is1805)
        )

    def rel_output(self, output_id: int, percent: float) -> None:
        """Send a command to change the value of an output-port.

        :param     int    output_id:    Output id 0..3
        :param     float    percent:      Relative brightness in percent
                                        -100..100
        """
        self.send_command(
            not self.is_group(), PckGenerator.rel_output(output_id, percent)
        )

    def toggle_output(self, output_id: int, ramp: int) -> None:
        """Send a command that toggles a single output-port.

        Toggle mode: (on->off, off->on).

        :param    int    output_id:    Output id 0..3
        :param    int    ramp:         Ramp time in milliseconds
        """
        self.send_command(
            not self.is_group(), PckGenerator.toggle_output(output_id, ramp)
        )

    def toggle_all_outputs(self, ramp: int) -> None:
        """Generate a command that toggles all output-ports.

        Toggle Mode:  (on->off, off->on).

        :param    int    ramp:        Ramp time in milliseconds
        """
        self.send_command(not self.is_group(), PckGenerator.toggle_all_outputs(ramp))

    def control_relays(self, states: List[lcn_defs.RelayStateModifier]) -> None:
        """Send a command to control relays.

        :param    states:   The 8 modifiers for the relay states as alist
        :type     states:   list(:class:`~pypck.lcn_defs.RelayStateModifier`)
        """
        self.send_command(not self.is_group(), PckGenerator.control_relays(states))

    def control_motors_relays(self, states: List[lcn_defs.MotorStateModifier]) -> None:
        """Send a command to control motors via relays.

        :param    states:   The 4 modifiers for the cover states as a list
        :type     states:   list(:class: `~pypck.lcn-defs.MotorStateModifier`)
        """
        self.send_command(
            not self.is_group(), PckGenerator.control_motors_relays(states)
        )

    def control_motors_outputs(
        self,
        state: lcn_defs.MotorStateModifier,
        reverse_time: Optional[lcn_defs.MotorReverseTime] = None,
    ) -> None:
        """Send a command to control a motor via output ports 1+2.

        :param    MotorStateModifier  state: The modifier for the cover state
        :param    MotorReverseTime    reverse_time: Reverse time for modules
                                                    with FW<190C
        :type     state:   :class: `~pypck.lcn-defs.MotorStateModifier`
        """
        self.send_command(
            not self.is_group(),
            PckGenerator.control_motors_outputs(state, reverse_time),
        )

    def activate_scene(
        self,
        register_id: int,
        scene_id: int,
        output_ports: Sequence[lcn_defs.OutputPort] = (),
        relay_ports: Sequence[lcn_defs.RelayPort] = (),
        ramp: Optional[int] = None,
    ) -> None:
        """Activate the stored states for the given scene.

        :param    int                register_id:    Register id 0..9
        :param    int                scene_id:       Scene id 0..9
        :param    list(OutputPort)   output_ports:   Output ports to activate
                                                     as list
        :param    list(RelayPort)    relay_ports:    Relay ports to activate
                                                     as list
        :param    int                ramp:           Ramp value
        """
        self.send_command(
            not self.is_group(), PckGenerator.change_scene_register(register_id)
        )
        if output_ports:
            self.send_command(
                not self.is_group(),
                PckGenerator.activate_scene_output(scene_id, output_ports, ramp),
            )
        if relay_ports:
            self.send_command(
                not self.is_group(),
                PckGenerator.activate_scene_relay(scene_id, relay_ports),
            )

    def store_scene(
        self,
        register_id: int,
        scene_id: int,
        output_ports: Sequence[lcn_defs.OutputPort] = (),
        relay_ports: Sequence[lcn_defs.RelayPort] = (),
        ramp: Optional[int] = None,
    ) -> None:
        """Store states in the given scene.

        :param    int                register_id:    Register id 0..9
        :param    int                scene_id:       Scene id 0..9
        :param    list(OutputPort)   output_ports:   Output ports to store
                                                     as list
        :param    list(RelayPort)    relay_ports:    Relay ports to store
                                                     as list
        :param    int                ramp:           Ramp value
        """
        self.send_command(
            not self.is_group(), PckGenerator.change_scene_register(register_id)
        )
        if output_ports:
            self.send_command(
                not self.is_group(),
                PckGenerator.store_scene_output(scene_id, output_ports, ramp),
            )
        if relay_ports:
            self.send_command(
                not self.is_group(),
                PckGenerator.store_scene_relay(scene_id, relay_ports),
            )

    def var_abs(
        self,
        var: lcn_defs.Var,
        value_or_float: Union[float, lcn_defs.VarValue],
        unit: lcn_defs.VarUnit = lcn_defs.VarUnit.NATIVE,
        is2013: Optional[bool] = None,
    ) -> None:
        """Send a command to set the absolute value to a variable.

        :param     Var        var:      Variable
        :param     float      value:    Absolute value to set
        :param     VarUnit    unit:     Unit of variable
        """
        if isinstance(value_or_float, lcn_defs.VarValue):
            value = value_or_float
        else:
            value = lcn_defs.VarValue.from_var_unit(value_or_float, unit, True)

        if is2013 is not None:
            sw_is2013 = is2013
        elif self._sw_age is not None:
            sw_is2013 = self._sw_age >= 0x170206
        else:
            sw_is2013 = False

        if lcn_defs.Var.to_var_id(var) != -1:
            # Absolute commands for variables 1-12 are not supported
            if self.get_id() == 4 and self.is_group():
                # group 4 are status messages
                self.send_command(
                    not self.is_group(),
                    PckGenerator.update_status_var(var, value.to_native()),
                )
            else:
                # We fake the missing command by using reset and relative
                # commands.
                self.send_command(
                    not self.is_group(), PckGenerator.var_reset(var, sw_is2013)
                )
                self.send_command(
                    not self.is_group(),
                    PckGenerator.var_rel(
                        var, lcn_defs.RelVarRef.CURRENT, value.to_native(), sw_is2013
                    ),
                )
        else:
            self.send_command(
                not self.is_group(), PckGenerator.var_abs(var, value.to_native())
            )

    def var_reset(self, var: lcn_defs.Var, is2013: Optional[bool] = None) -> None:
        """Send a command to reset the variable value.

        :param    Var    var:    Variable
        """
        if is2013 is not None:
            sw_is2013 = is2013
        elif self._sw_age is not None:
            sw_is2013 = self._sw_age >= 0x170206
        else:
            sw_is2013 = False

        self.send_command(not self.is_group(), PckGenerator.var_reset(var, sw_is2013))

    def var_rel(
        self,
        var: lcn_defs.Var,
        value_or_float: Union[float, lcn_defs.VarValue],
        unit: lcn_defs.VarUnit = lcn_defs.VarUnit.NATIVE,
        value_ref: lcn_defs.RelVarRef = lcn_defs.RelVarRef.CURRENT,
        is2013: Optional[bool] = None,
    ) -> None:
        """Send a command to change the value of a variable.

        :param     Var        var:      Variable
        :param     float      value:    Relative value to add (may also be
                                        negative)
        :param     VarUnit    unit:     Unit of variable
        """
        if isinstance(value_or_float, lcn_defs.VarValue):
            value = value_or_float
        else:
            value = lcn_defs.VarValue.from_var_unit(value_or_float, unit, True)

        if is2013 is not None:
            sw_is2013 = is2013
        elif self._sw_age is not None:
            sw_is2013 = self._sw_age >= 0x170206
        else:
            sw_is2013 = False

        self.send_command(
            not self.is_group(),
            PckGenerator.var_rel(var, value_ref, value.to_native(), sw_is2013),
        )

    def lock_regulator(self, reg_id: int, state: bool) -> None:
        """Send a command to lock a regulator.

        :param    int        reg_id:        Regulator id
        :param    bool       state:         Lock state (locked=True,
                                            unlocked=False)
        """
        if reg_id != -1:
            self.send_command(
                not self.is_group(), PckGenerator.lock_regulator(reg_id, state)
            )

    def control_led(self, led: lcn_defs.LedPort, state: lcn_defs.LedStatus) -> None:
        """Send a command to control a led.

        :param    LedPort      led:        Led port
        :param    LedStatus    state:      Led status
        """
        self.send_command(
            not self.is_group(), PckGenerator.control_led(led.value, state)
        )

    def send_keys(self, keys: List[List[bool]], cmd: lcn_defs.SendKeyCommand) -> None:
        """Send a command to send keys.

        :param    list(bool)[4][8]    keys:    2d-list with [table_id][key_id]
                                               bool values, if command should
                                               be sent to specific key
        :param    SendKeyCommand      cmd:     command to send for each table
        """
        for table_id, key_states in enumerate(keys):
            if True in key_states:
                cmds = [lcn_defs.SendKeyCommand.DONTSEND] * 4
                cmds[table_id] = cmd
                self.send_command(
                    not self.is_group(), PckGenerator.send_keys(cmds, key_states)
                )

    def send_keys_hit_deferred(
        self, keys: List[List[bool]], delay_time: int, delay_unit: lcn_defs.TimeUnit
    ) -> None:
        """Send a command to send keys deferred.

        :param    list(bool)[4][8]    keys:          2d-list with
                                                     [table_id][key_id] bool
                                                     values, if command should
                                                     be sent to specific key
        :param    int                 delay_time:    Delay time
        :param    TimeUnit            delay_unit:    Unit of time
        """
        for table_id, key_states in enumerate(keys):
            if True in key_states:
                self.send_command(
                    not self.is_group(),
                    PckGenerator.send_keys_hit_deferred(
                        table_id, delay_time, delay_unit, key_states
                    ),
                )

    def lock_keys(
        self, table_id: int, states: List[lcn_defs.KeyLockStateModifier]
    ) -> None:
        """Send a command to lock keys.

        :param    int                     table_id:  Table id: 0..3
        :param    keyLockStateModifier    states:    The 8 modifiers for the
                                                     key lock states as a list
        """
        self.send_command(not self.is_group(), PckGenerator.lock_keys(table_id, states))

    def lock_keys_tab_a_temporary(
        self, delay_time: int, delay_unit: lcn_defs.TimeUnit, states: List[bool]
    ) -> None:
        """Send a command to lock keys in table A temporary.

        :param    int        delay_time:    Time to lock keys
        :param    TimeUnit   delay_unit:    Unit of time
        :param    list(bool) states:        The 8 lock states of the keys as
                                            list (locked=True, unlocked=False)
        """
        self.send_command(
            not self.is_group(),
            PckGenerator.lock_keys_tab_a_temporary(delay_time, delay_unit, states),
        )

    def dyn_text(self, row_id: int, text: str) -> None:
        """Send dynamic text to a module.

        :param    int    row_id:    Row id 0..3
        :param    str    text:      Text to send (up to 60 bytes)
        """
        encoded_text = text.encode(lcn_defs.LCN_ENCODING)

        parts = [encoded_text[12 * p : 12 * p + 12] for p in range(5)]
        for part_id, part in enumerate(parts):
            if part:
                self.send_command(
                    not self.is_group(),
                    PckGenerator.dyn_text_part(row_id, part_id, part),
                )

    def beep(self, sound: lcn_defs.BeepSound, count: int) -> None:
        """Send a command to make count number of beep sounds.

        :param    BeepSound sound:  Beep sound style
        :param    int       count:  Number of beeps (1..15)
        """
        self.send_command(not self.is_group(), PckGenerator.beep(sound, count))

    def ping(self) -> None:
        """Send a command that does nothing and request an acknowledgement."""
        self.send_command(True, PckGenerator.empty())

    def pck(self, pck: str) -> None:
        """Send arbitrary PCK command.

        :param    str    pck:    PCK command
        """
        self.send_command(not self.is_group(), pck)


class GroupConnection(AbstractConnection):
    """Organizes communication with a specific group.

    It is assumed that all modules within this group are newer than FW170206
    """

    def __init__(
        self,
        conn: "PchkConnectionManager",
        seg_id: int,
        grp_id: int,
        sw_age: int = 0x170206,
    ):
        """Construct GroupConnection instance."""
        super().__init__(conn, seg_id, grp_id, True, sw_age=sw_age)

    def var_abs(
        self,
        var: lcn_defs.Var,
        value: Union[float, lcn_defs.VarValue],
        unit: lcn_defs.VarUnit = lcn_defs.VarUnit.NATIVE,
        is2013: Optional[bool] = None,
    ) -> None:
        """Send a command to set the absolute value to a variable.

        :param     Var        var:      Variable
        :param     float      value:    Absolute value to set
        :param     VarUnit    unit:     Unit of variable
        """
        # for new modules (>=0x170206)
        super().var_abs(var, value, unit, is2013=True)

        # for old modules (<0x170206)
        if var in [
            lcn_defs.Var.TVAR,
            lcn_defs.Var.R1VAR,
            lcn_defs.Var.R2VAR,
            lcn_defs.Var.R1VARSETPOINT,
            lcn_defs.Var.R2VARSETPOINT,
        ]:
            super().var_abs(var, value, unit, is2013=False)

    def var_reset(self, var: lcn_defs.Var, is2013: Optional[bool] = None) -> None:
        """Send a command to reset the variable value.

        :param    Var    var:    Variable
        """
        super().var_reset(var, is2013=True)
        if var in [
            lcn_defs.Var.TVAR,
            lcn_defs.Var.R1VAR,
            lcn_defs.Var.R2VAR,
            lcn_defs.Var.R1VARSETPOINT,
            lcn_defs.Var.R2VARSETPOINT,
        ]:
            super().var_reset(var, is2013=False)

    def var_rel(
        self,
        var: lcn_defs.Var,
        value: Union[float, lcn_defs.VarValue],
        unit: lcn_defs.VarUnit = lcn_defs.VarUnit.NATIVE,
        value_ref: lcn_defs.RelVarRef = lcn_defs.RelVarRef.CURRENT,
        is2013: Optional[bool] = None,
    ) -> None:
        """Send a command to change the value of a variable.

        :param     Var        var:      Variable
        :param     float      value:    Relative value to add (may also be
                                        negative)
        :param     VarUnit    unit:     Unit of variable
        """
        super().var_rel(var, value, is2013=True)
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
            super().var_rel(var, value, is2013=False)

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
        seg_id: int,
        mod_id: int,
        activate_status_requests: bool = False,
        has_s0_enabled: bool = False,
        sw_age: Optional[int] = None,
    ):
        """Construct ModuleConnection instance."""
        super().__init__(conn, seg_id, mod_id, False, sw_age=sw_age)
        self.activate_status_requests = activate_status_requests
        self.has_s0_enabled = has_s0_enabled

        # List of queued PCK commands to be acknowledged by the LCN module.
        # Commands are always without address header.
        # Note that the first one might currently be "in progress".
        self.pck_commands_with_ack: Deque[str] = deque()

        self.request_curr_pck_command_with_ack = TimeoutRetryHandler(
            conn.settings["NUM_TRIES"], conn.settings["DEFAULT_TIMEOUT_MSEC"]
        )
        self.request_curr_pck_command_with_ack.set_timeout_callback(
            self.request_curr_pck_command_with_ack_timeout
        )

        self.properties_requests = ModulePropertiesRequestHandler(
            self, software_serial=sw_age
        )
        self.status_requests = StatusRequestsHandler(self)

        self.activate_prh_task = asyncio.create_task(
            self.activate_properties_request_handlers()
        )
        if self.activate_status_requests:
            self.activate_srh_task = asyncio.create_task(
                self.activate_status_request_handlers()
            )

    def send_command(self, wants_ack: bool, pck: str) -> None:
        """Send a command to the module represented by this class.

        :param    bool    wants_ack:    Also send a request for acknowledge.
        :param    str     pck:          PCK command (without header).
        """
        if wants_ack:
            self.schedule_command_with_ack(pck)
        else:
            super().send_command(False, pck)

    async def activate_properties_request_handlers(self) -> None:
        """Activate all TimeoutRetryHandlers for property requests."""
        await self.properties_requests.activate_all()

    async def activate_status_request_handler(self, item: Any) -> None:
        """Activate a specific TimeoutRetryHandler for status requests."""
        await self.status_requests.activate(item)

    async def activate_status_request_handlers(self) -> None:
        """Activate all TimeoutRetryHandlers for status requests."""
        await self.status_requests.activate_all(activate_s0=self.has_s0_enabled)

    async def cancel_properties_request_handlers(self) -> None:
        """Canecl all TimeoutRetryHandlers for status requests."""
        await self.properties_requests.cancel_all()
        self.activate_prh_task.cancel()
        await self.activate_prh_task

    async def cancel_status_request_handler(self, item: Any) -> None:
        """Cancel a specific TimeoutRetryHandler for status requests."""
        await self.status_requests.cancel(item)
        if self.activate_status_requests:
            self.activate_srh_task.cancel()
            await self.activate_srh_task

    async def cancel_status_request_handlers(self) -> None:
        """Canecl all TimeoutRetryHandlers for status requests."""
        await self.status_requests.cancel_all()

    async def cancel_requests(self) -> None:
        """Cancel all TimeoutRetryHandlers."""
        await self.cancel_status_request_handlers()
        await self.cancel_properties_request_handlers()
        await self.request_curr_pck_command_with_ack.cancel()
        self.pck_commands_with_ack.clear()

    def set_s0_enabled(self, s0_enabled: bool) -> None:
        """Set the activation status for S0 variables.

        :param     bool    s0_enabled:   If True, a BU4L has to be connected
        to the hardware module and S0 mode has to be activated in LCN-PRO.
        """
        self.has_s0_enabled = s0_enabled

    def get_s0_enabled(self) -> bool:
        """Get the activation status for S0 variables."""
        return self.has_s0_enabled

    def get_sw_age(self) -> int:
        """Get the LCN module's firmware date."""
        return self.properties_requests.serials.software_serial

    # ##
    # ## Retry logic if an acknowledge is requested
    # ##

    def schedule_command_with_ack(self, pck: str) -> None:
        """Schedule the next command which requests an acknowledge."""
        # add pck command to pck commands list
        self.pck_commands_with_ack.append(pck)
        # Try to process the new acknowledged command.
        # Will do nothing if another one is still in progress.
        self.try_process_next_command_with_ack()

    async def on_ack(
        self, code: int = -1, timeout_msec: int = DEFAULT_TIMEOUT_MSEC
    ) -> None:
        """Is called whenever an acknowledge is received from the LCN module.

        :param     int    code:           The LCN internal code. -1 means
                                          "positive" acknowledge
        :param     intt   timeout_mSec:   The time to wait for a response
                                          before retrying a request
        """
        # Check if we wait for an ack.
        if self.request_curr_pck_command_with_ack.is_active():
            if self.pck_commands_with_ack:
                self.pck_commands_with_ack.popleft()
            await self.request_curr_pck_command_with_ack.cancel()
            # Try to process next acknowledged command
            self.try_process_next_command_with_ack()

    def try_process_next_command_with_ack(self) -> None:
        """Send the next acknowledged command from the queue."""
        if self.pck_commands_with_ack and (
            not self.request_curr_pck_command_with_ack.is_active()
        ):
            self.request_curr_pck_command_with_ack.activate()

    def request_curr_pck_command_with_ack_timeout(self, failed: bool) -> None:
        """I called on command with acknowledge timeout."""
        # Use the chance to remove a failed command first
        if failed:
            self.pck_commands_with_ack.popleft()
            self.try_process_next_command_with_ack()
        else:
            pck = self.pck_commands_with_ack[0]
            self.conn.send_command(
                PckGenerator.generate_address_header(self, self.conn.local_seg_id, True)
                + pck
            )

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Is called by input object's process method.

        Method to handle incoming commands for this specific module (status,
        toggle_output, switch_relays, ...)
        """
        if isinstance(inp, inputs.ModAck):
            asyncio.create_task(self.on_ack(inp.code, DEFAULT_TIMEOUT_MSEC))
            return None

        # handle typeless variable responses
        if isinstance(inp, inputs.ModStatusVar):
            inp = self.status_requests.preprocess_modstatusvar(inp)

        await super().async_process_input(inp)

    # ##
    # ## Requests
    # ##

    # ## properties

    @property
    def hardware_serial(self) -> int:
        """Return hardware serial of module."""
        return self.properties_requests.serials.hardware_serial

    @property
    def manu(self) -> int:
        """Return manufacturing of module."""
        return self.properties_requests.serials.manu

    @property
    def software_serial(self) -> int:
        """Return software serial of module."""
        return self.properties_requests.serials.software_serial

    @property
    def hw_type(self) -> int:
        """Return hardware type of module."""
        return self.properties_requests.serials.hardware_type

    @property
    def serial(self) -> Tuple[int, int, int, int]:
        """Return serials number information."""
        return (self.hardware_serial, self.manu, self.software_serial, self.hw_type)

    @property
    def name(self) -> str:
        """Retrun stored name."""
        return self.properties_requests.name_comment.name

    @property
    def comment(self) -> str:
        """Return stored comments."""
        return self.properties_requests.name_comment.comment

    @property
    def oem_text(self) -> List[str]:
        """Return stored OEM text."""
        return self.properties_requests.name_comment.oem_text

    # ## future properties

    @property
    def serial_known(self) -> Awaitable[bool]:
        """Check if serials have already been received from module."""
        return self.properties_requests.serials.serial_known.wait()

    async def request_name(self) -> str:
        """Request module name."""
        return await self.properties_requests.name_comment.request_name()

    async def request_comment(self) -> str:
        """Request comments from a module."""
        return await self.properties_requests.name_comment.request_comment()

    async def request_oem_text(self) -> List[str]:
        """Request OEM text from a module."""
        return await self.properties_requests.name_comment.request_oem_text()
