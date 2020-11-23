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

        self.trh = TimeoutRetryHandler(num_tries, timeout_msec)
        self.trh.set_timeout_callback(self.timeout)

        # callback
        addr_conn.register_for_inputs(self.process_input)

    async def request(self) -> Any:
        """Request information from module."""
        raise NotImplementedError()

    def process_input(self, inp: inputs.Input) -> None:
        """Create a task to process the input object concurrently."""
        asyncio.create_task(self.async_process_input(inp))

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
        return self.serial

    @property
    def serial(self) -> Dict[str, Union[int, lcn_defs.HardwareType]]:
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

        self.trhs = []
        for block_id in range(2):
            trh = TimeoutRetryHandler(num_tries, timeout_msec)
            trh.set_timeout_callback(self.timeout, block_id=block_id)
            self.trhs.append(trh)

        # events
        self.name_known = asyncio.Event()

        super().__init__(addr_conn, num_tries, timeout_msec)

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

        self.trhs = []
        for block_id in range(3):
            trh = TimeoutRetryHandler(num_tries, timeout_msec)
            trh.set_timeout_callback(self.timeout, block_id=block_id)
            self.trhs.append(trh)

        # events
        self.comment_known = asyncio.Event()

        super().__init__(addr_conn, num_tries, timeout_msec)

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

        self.trhs = []
        for block_id in range(4):
            trh = TimeoutRetryHandler(num_tries, timeout_msec)
            trh.set_timeout_callback(self.timeout, block_id=block_id)
            self.trhs.append(trh)

        # events
        self.oem_text_known = asyncio.Event()

        super().__init__(addr_conn, num_tries, timeout_msec)

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

        # events
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

        # events
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
