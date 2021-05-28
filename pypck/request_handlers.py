"""Copyright (c) 2006-2020 by the respective copyright holders.

See the NOTICE file(s) distributed with this work for additional
information.

This program and the accompanying materials are made available under the
terms of the Eclipse Public License 2.0 which is available at
http://www.eclipse.org/legal/epl-2.0

SPDX-License-Identifier: EPL-2.0

Contributors:
  Andre Lengwenus - Request handler logic
"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union

from pypck import inputs, lcn_defs
from pypck.lcn_addr import LcnAddr
from pypck.helpers import TaskRegistry
from pypck.pck_commands import PckGenerator
from pypck.timeout_retry import TimeoutRetryHandler

if TYPE_CHECKING:
    from pypck.module import ModuleConnection


class RequestHandler:
    """Base RequestHandler class."""

    def __init__(
        self,
        addr_conn: "ModuleConnection",
        num_tries: int = 3,
        timeout_msec: int = 1500,
    ):
        """Initialize class instance."""
        self.addr_conn = addr_conn

        self.trh = TimeoutRetryHandler(self.task_registry, num_tries, timeout_msec)
        self.trh.set_timeout_callback(self.timeout)

        # callback
        addr_conn.register_for_inputs(self.process_input)

    @property
    def task_registry(self) -> TaskRegistry:
        """Get the task registry."""
        return self.addr_conn.task_registry

    async def request(self) -> Any:
        """Request information from module."""
        raise NotImplementedError()

    def process_input(self, inp: inputs.Input) -> None:
        """Create a task to process the input object concurrently."""
        self.task_registry.create_task(self.async_process_input(inp))

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Process incoming input object.

        Method to handle incoming commands for this request handler.
        """
        raise NotImplementedError()

    async def timeout(self, failed: bool = False) -> None:
        """Is called on serial request timeout."""
        raise NotImplementedError()

    async def cancel(self) -> None:
        """Cancel request."""
        await self.trh.cancel()


class SerialRequestHandler(RequestHandler):
    """Request handler to request serial number information from module."""

    def __init__(
        self,
        addr_conn: "ModuleConnection",
        num_tries: int = 3,
        timeout_msec: int = 1500,
        software_serial: Optional[int] = None,
    ):
        """Initialize class instance."""
        self.hardware_serial = -1
        self.manu = -1
        if software_serial is None:
            software_serial = -1
        self.software_serial = software_serial
        self.hardware_type = lcn_defs.HardwareType.UNKNOWN

        # events
        self.serial_known = asyncio.Event()

        super().__init__(addr_conn, num_tries, timeout_msec)

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Process incoming input object.

        Method to handle incoming commands for this specific request handler.
        """
        if isinstance(inp, inputs.ModSn):
            self.hardware_serial = inp.hardware_serial
            self.manu = inp.manu
            self.software_serial = inp.software_serial
            self.hardware_type = inp.hardware_type

            self.serial_known.set()
            await self.cancel()

    async def timeout(self, failed: bool = False) -> None:
        """Is called on serial request timeout."""
        if not failed:
            await self.addr_conn.send_command(False, PckGenerator.request_serial())
        else:
            self.serial_known.set()

    async def request(self) -> Dict[str, Union[int, lcn_defs.HardwareType]]:
        """Request serial number."""
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        self.serial_known.clear()
        self.trh.activate()
        await self.serial_known.wait()
        return self.serials

    @property
    def serials(self) -> Dict[str, Union[int, lcn_defs.HardwareType]]:
        """Return serial numbers of a module."""
        return {
            "hardware_serial": self.hardware_serial,
            "manu": self.manu,
            "software_serial": self.software_serial,
            "hardware_type": self.hardware_type,
        }


class NameRequestHandler(RequestHandler):
    """Request handler to request name of a module."""

    def __init__(
        self,
        addr_conn: "ModuleConnection",
        num_tries: int = 3,
        timeout_msec: int = 1500,
    ):
        """Initialize class instance."""
        self._name: List[Optional[str]] = [None] * 2
        self.name_known = asyncio.Event()

        super().__init__(addr_conn, num_tries, timeout_msec)

        self.trhs = []
        for block_id in range(2):
            trh = TimeoutRetryHandler(self.task_registry, num_tries, timeout_msec)
            trh.set_timeout_callback(self.timeout, block_id=block_id)
            self.trhs.append(trh)

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
                await self.cancel(block_id)
                if None not in self._name:
                    self.name_known.set()
                    await self.cancel()

    # pylint: disable=arguments-differ
    async def timeout(self, failed: bool = False, block_id: int = 0) -> None:
        """Is called on name request timeout."""
        if not failed:
            await self.addr_conn.send_command(
                False, PckGenerator.request_name(block_id)
            )
        else:
            self.name_known.set()

    async def request(self) -> str:
        """Request name from a module."""
        self._name = [None] * 2
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        self.name_known.clear()
        for trh in self.trhs:
            trh.activate()
        await self.name_known.wait()
        return self.name

    # pylint: disable=arguments-differ
    async def cancel(self, block_id: Optional[int] = None) -> None:
        """Cancel name request task."""
        if block_id is None:  # cancel all
            for trh in self.trhs:
                await trh.cancel()
        else:
            await self.trhs[block_id].cancel()

    @property
    def name(self) -> str:
        """Return stored name."""
        return "".join([block for block in self._name if block]).strip()


class CommentRequestHandler(RequestHandler):
    """Request handler to request comment of a module."""

    def __init__(
        self,
        addr_conn: "ModuleConnection",
        num_tries: int = 3,
        timeout_msec: int = 1500,
    ):
        """Initialize class instance."""
        self._comment: List[Optional[str]] = [None] * 3
        self.comment_known = asyncio.Event()

        super().__init__(addr_conn, num_tries, timeout_msec)

        self.trhs = []
        for block_id in range(3):
            trh = TimeoutRetryHandler(self.task_registry, num_tries, timeout_msec)
            trh.set_timeout_callback(self.timeout, block_id=block_id)
            self.trhs.append(trh)

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Process incoming input object.

        Method to handle incoming commands for this specific request handler.
        """
        if isinstance(inp, inputs.ModNameComment):
            command = inp.command
            block_id = inp.block_id
            text = inp.text

            if command == "K":
                self._comment[block_id] = f"{text:12s}"
                await self.cancel(block_id)
                if None not in self._comment:
                    self.comment_known.set()
                    await self.cancel()

    # pylint: disable=arguments-differ
    async def timeout(self, failed: bool = False, block_id: int = 0) -> None:
        """Is called on comment request timeout."""
        if not failed:
            await self.addr_conn.send_command(
                False, PckGenerator.request_comment(block_id)
            )
        else:
            self.comment_known.set()

    async def request(self) -> str:
        """Request comments from a module."""
        self._comment = [None] * 3
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        self.comment_known.clear()
        for trh in self.trhs:
            trh.activate()
        await self.comment_known.wait()
        return self.comment

    # pylint: disable=arguments-differ
    async def cancel(self, block_id: Optional[int] = None) -> None:
        """Cancel comment request task."""
        if block_id is None:  # cancel all
            for trh in self.trhs:
                await trh.cancel()
        else:
            await self.trhs[block_id].cancel()

    @property
    def comment(self) -> str:
        """Return stored comment."""
        return "".join([block for block in self._comment if block]).strip()


class OemTextRequestHandler(RequestHandler):
    """Request handler to request OEM text of a module."""

    def __init__(
        self,
        addr_conn: "ModuleConnection",
        num_tries: int = 3,
        timeout_msec: int = 1500,
    ):
        """Initialize class instance."""
        self._oem_text: List[Optional[str]] = [None] * 4
        self.oem_text_known = asyncio.Event()

        super().__init__(addr_conn, num_tries, timeout_msec)

        self.trhs = []
        for block_id in range(4):
            trh = TimeoutRetryHandler(self.task_registry, num_tries, timeout_msec)
            trh.set_timeout_callback(self.timeout, block_id=block_id)
            self.trhs.append(trh)

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Process incoming input object.

        Method to handle incoming commands for this specific request handler.
        """
        if isinstance(inp, inputs.ModNameComment):
            command = inp.command
            block_id = inp.block_id
            text = inp.text

            if command == "O":
                self._oem_text[block_id] = f"{text:12s}"
                await self.cancel(block_id)
                if None not in self._oem_text:
                    self.oem_text_known.set()
                    await self.cancel()

    # pylint: disable=arguments-differ
    async def timeout(self, failed: bool = False, block_id: int = 0) -> None:
        """Is called on OEM text request timeout."""
        if not failed:
            await self.addr_conn.send_command(
                False, PckGenerator.request_oem_text(block_id)
            )
        else:
            self.oem_text_known.set()

    async def request(self) -> List[str]:
        """Request OEM text from a module."""
        self._oem_text = [None] * 4
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        self.oem_text_known.clear()
        for trh in self.trhs:
            trh.activate()
        await self.oem_text_known.wait()
        return self.oem_text

    # pylint: disable=arguments-differ
    async def cancel(self, block_id: Optional[int] = None) -> None:
        """Cancel OEM text request task."""
        if block_id is None:  # cancel all
            for trh in self.trhs:
                await trh.cancel()
        else:
            await self.trhs[block_id].cancel()

    @property
    def oem_text(self) -> List[str]:
        """Return stored OEM text."""
        return [block.strip() if block else "" for block in self._oem_text]
        # return {'block{}'.format(idx):text
        #         for idx, text in enumerate(self._oem_text)}

        # return ''.join([block for block in self._oem_text if block])


class GroupMembershipStaticRequestHandler(RequestHandler):
    """Request handler to request static group membership of a module."""

    def __init__(
        self,
        addr_conn: "ModuleConnection",
        num_tries: int = 3,
        timeout_msec: int = 1500,
    ):
        """Initialize class instance."""
        self.groups: Set[LcnAddr] = set()
        self.groups_known = asyncio.Event()

        super().__init__(addr_conn, num_tries, timeout_msec)

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Process incoming input object.

        Method to handle incoming commands for this specific request handler.
        """
        if isinstance(inp, inputs.ModStatusGroups):
            if not inp.dynamic:  # static
                self.groups.update(inp.groups)
                self.groups_known.set()
                await self.cancel()

    async def timeout(self, failed: bool = False) -> None:
        """Is called on static group membership request timeout."""
        if not failed:
            await self.addr_conn.send_command(
                False, PckGenerator.request_group_membership_static()
            )
        else:
            self.groups_known.set()

    async def request(self) -> Set[LcnAddr]:
        """Request static group membership from a module."""
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        self.groups_known.clear()
        self.trh.activate()
        await self.groups_known.wait()
        return self.groups


class GroupMembershipDynamicRequestHandler(RequestHandler):
    """Request handler to request static group membership of a module."""

    def __init__(
        self,
        addr_conn: "ModuleConnection",
        num_tries: int = 3,
        timeout_msec: int = 1500,
    ):
        """Initialize class instance."""
        self.groups: Set[LcnAddr] = set()
        self.groups_known = asyncio.Event()

        super().__init__(addr_conn, num_tries, timeout_msec)

    async def async_process_input(self, inp: inputs.Input) -> None:
        """Process incoming input object.

        Method to handle incoming commands for this specific request handler.
        """
        if isinstance(inp, inputs.ModStatusGroups):
            if inp.dynamic:  # dynamic
                self.groups.update(inp.groups)
                self.groups_known.set()
                await self.cancel()

    async def timeout(self, failed: bool = False) -> None:
        """Is called on dynamic group membership request timeout."""
        if not failed:
            await self.addr_conn.send_command(
                False, PckGenerator.request_group_membership_dynamic()
            )
        else:
            self.groups_known.set()

    async def request(self) -> Set[LcnAddr]:
        """Request dynamic group membership from a module."""
        await self.addr_conn.conn.segment_scan_completed_event.wait()
        self.groups_known.clear()
        self.trh.activate()
        await self.groups_known.wait()
        return self.groups


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
                self.task_registry,
                -1,
                self.settings["MAX_STATUS_EVENTBASED_VALUEAGE_MSEC"],
            )
            trh.set_timeout_callback(self.request_status_outputs_timeout, output_port)
            self.request_status_outputs.append(trh)

        # Relay request status (all 8)
        self.request_status_relays = TimeoutRetryHandler(
            self.task_registry, -1, self.settings["MAX_STATUS_EVENTBASED_VALUEAGE_MSEC"]
        )
        self.request_status_relays.set_timeout_callback(
            self.request_status_relays_timeout
        )

        # Binary-sensors request status (all 8)
        self.request_status_bin_sensors = TimeoutRetryHandler(
            self.task_registry, -1, self.settings["MAX_STATUS_EVENTBASED_VALUEAGE_MSEC"]
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
                    self.task_registry,
                    -1,
                    self.settings["MAX_STATUS_EVENTBASED_VALUEAGE_MSEC"],
                )
                self.request_status_vars[var].set_timeout_callback(
                    self.request_status_var_timeout, var=var
                )

        # LEDs and logic-operations request status (all 12+4).
        self.request_status_leds_and_logic_ops = TimeoutRetryHandler(
            self.task_registry, -1, self.settings["MAX_STATUS_POLLED_VALUEAGE_MSEC"]
        )
        self.request_status_leds_and_logic_ops.set_timeout_callback(
            self.request_status_leds_and_logic_ops_timeout
        )

        # Key lock-states request status (all tables, A-D).
        self.request_status_locked_keys = TimeoutRetryHandler(
            self.task_registry, -1, self.settings["MAX_STATUS_POLLED_VALUEAGE_MSEC"]
        )
        self.request_status_locked_keys.set_timeout_callback(
            self.request_status_locked_keys_timeout
        )

    @property
    def task_registry(self) -> TaskRegistry:
        """Get the task registry."""
        return self.addr_conn.task_registry

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

    async def request_status_outputs_timeout(
        self, failed: bool = False, output_port: int = 0
    ) -> None:
        """Is called on output status request timeout."""
        if not failed:
            await self.addr_conn.send_command(
                False, PckGenerator.request_output_status(output_port)
            )

    async def request_status_relays_timeout(self, failed: bool = False) -> None:
        """Is called on relay status request timeout."""
        if not failed:
            await self.addr_conn.send_command(
                False, PckGenerator.request_relays_status()
            )

    async def request_status_bin_sensors_timeout(self, failed: bool = False) -> None:
        """Is called on binary sensor status request timeout."""
        if not failed:
            await self.addr_conn.send_command(
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
        await self.addr_conn.send_command(
            False,
            PckGenerator.request_var_status(var, self.addr_conn.software_serial),
        )

    async def request_status_leds_and_logic_ops_timeout(
        self, failed: bool = False
    ) -> None:
        """Is called on leds/logical ops status request timeout."""
        if not failed:
            await self.addr_conn.send_command(
                False, PckGenerator.request_leds_and_logic_ops()
            )

    async def request_status_locked_keys_timeout(self, failed: bool = False) -> None:
        """Is called on locked keys status request timeout."""
        if not failed:
            await self.addr_conn.send_command(
                False, PckGenerator.request_key_lock_status()
            )

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
