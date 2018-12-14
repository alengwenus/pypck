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

from collections import deque

from pypck import lcn_defs
from pypck.lcn_addr import LcnAddr
from pypck.pck_commands import PckGenerator
from pypck.timeout_retry import DEFAULT_TIMEOUT_MSEC, TimeoutRetryHandler


class StatusRequestHandler():
    """Manages all status requests for variables, software version, ...
    """

    def __init__(self, loop, settings):
        self.loop = loop
        self.sw_age = -1
        self.settings = settings

        self.activate_backlog = []

        # Output-port request status (0..3)
        self.request_status_outputs = \
            [TimeoutRetryHandler(
                self.loop, -1,
                self.settings['MAX_STATUS_EVENTBASED_VALUEAGE_MSEC'])
             for i in range(4)]

        # Relay request status (all 8)
        self.request_status_relays = \
            TimeoutRetryHandler(
                self.loop, -1,
                self.settings['MAX_STATUS_EVENTBASED_VALUEAGE_MSEC'])

        # Binary-sensors request status (all 8)
        self.request_status_bin_sensors = \
            TimeoutRetryHandler(
                self.loop, -1,
                self.settings['MAX_STATUS_EVENTBASED_VALUEAGE_MSEC'])

        # Variables request status.
        # Lazy initialization: Will be filled once the firmware version is
        # known.
        self.request_status_vars = {}
        for var in lcn_defs.Var:
            if var != lcn_defs.Var.UNKNOWN:
                self.request_status_vars[var] = \
                    TimeoutRetryHandler(
                        self.loop, -1,
                        self.settings['MAX_STATUS_EVENTBASED_VALUEAGE_MSEC'])

        # LEDs and logic-operations request status (all 12+4).
        self.request_status_leds_and_logic_ops = \
            TimeoutRetryHandler(
                self.loop, -1,
                self.settings['MAX_STATUS_POLLED_VALUEAGE_MSEC'])

        # Key lock-states request status (all tables, A-D).
        self.request_status_locked_keys = \
            TimeoutRetryHandler(
                self.loop, -1,
                self.settings['MAX_STATUS_POLLED_VALUEAGE_MSEC'])

        self.sw_age_known = self.loop.create_future()

    def get_sw_age(self):
        """Returns the software firmware version.

        :return:    Software firmware version
        :rtype:     int
        """
        return self.sw_age

    def set_sw_age(self, sw_age):
        """Sets the software firmware version.

        :param    int    sw_age:    Software firmware version
        """
        self.sw_age = sw_age
        if not self.sw_age_known.done():
            self.sw_age_known.set_result(True)

    def set_output_timeout_callback(self, output_port, callback):
        """Sets callback for output status request timeouts.
        """
        self.request_status_outputs[output_port.value].set_timeout_callback(
            callback)

    def set_relays_timeout_callback(self, callback):
        """Sets callback for relay status request timeouts.
        """
        self.request_status_relays.set_timeout_callback(callback)

    def set_bin_sensors_timeout_callback(self, callback):
        """Sets callback for binary sensor status request timeouts.
        """
        self.request_status_bin_sensors.set_timeout_callback(callback)

    def set_var_timeout_callback(self, var, callback):
        """Sets callback for variable status request timeouts.
        """
        if var != lcn_defs.Var.UNKNOWN:
            self.request_status_vars[var].set_timeout_callback(callback)

    def set_leds_and_logic_opts_timeout_callback(self, callback):
        """Sets callback for leds and logic operations status request
        timeouts.
        """
        self.request_status_leds_and_logic_ops.set_timeout_callback(callback)

    def set_locked_keys_callback(self, callback):
        """Sets callback for locked keys status request timeouts.
        """
        self.request_status_locked_keys.set_timeout_callback(callback)

    async def activate(self, item):
        """Activates status requests for given item.
        """
        # handle variables independently
        if (item in lcn_defs.Var) and (item != lcn_defs.Var.UNKNOWN):
            await self.sw_age_known  # wait until we know the software version
            if self.sw_age >= 0x170206:
                timeout_msec = \
                    self.settings['MAX_STATUS_EVENTBASED_VALUEAGE_MSEC']
            else:
                timeout_msec = \
                    self.settings['MAX_STATUS_POLLED_VALUEAGE_MSEC']
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

    async def cancel(self, item):
        """Cancels status request for given item.
        """
        # handle variables independently
        if (item in lcn_defs.Var) and (item != lcn_defs.Var.UNKNOWN):
            await self.request_status_vars[item].cancel()
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

    async def activate_all(self, activate_s0=False):
        """Activates all status requests.
        """
        for item in list(lcn_defs.OutputPort) + list(lcn_defs.RelayPort) + \
                list(lcn_defs.BinSensorPort) + list(lcn_defs.LedPort) + \
                list(lcn_defs.Key) + list(lcn_defs.Var):
            if item == lcn_defs.Var.UNKNOWN:
                continue
            if (not activate_s0) and (item in lcn_defs.Var.s0s):
                continue
            await self.activate(item)
            # self.loop.create_task(self.activate(item))

    async def cancel_all(self):
        """Cancels all status requests.
        """
        for item in list(lcn_defs.OutputPort) + list(lcn_defs.RelayPort) + \
                list(lcn_defs.BinSensorPort) + list(lcn_defs.LedPort) + \
                list(lcn_defs.Key) + list(lcn_defs.Var):
            if item == lcn_defs.Var.UNKNOWN:
                continue
            await self.cancel(item)


class AbstractConnection(LcnAddr):
    """Organizes communication with a specific module.
    Sends status requests to the connection and handles status responses.
    """

    def __init__(self, loop, conn, seg_id, addr_id, is_group, sw_age=None):
        self.loop = loop
        self.conn = conn
        super().__init__(seg_id=seg_id, addr_id=addr_id, is_group=is_group)

        if sw_age is not None:
            self.set_sw_age(sw_age)

        self.input_callbacks = []
        self.last_requested_var_without_type_in_response = \
            lcn_defs.Var.UNKNOWN

    def set_sw_age(self, sw_age):
        """Sets the software firmware date.

        :param     int    swAge:    The firmware date
        """
        self._sw_age = sw_age

    def get_sw_age(self):
        """Returns standard sw_age.
        """
        return self._sw_age

    def send_command(self, wants_ack, pck):
        """Sends a command to the module represented by this class.

        :param    bool    wants_ack:    Also send a request for acknowledge.
        :param    str     pck:          PCK command (without header).
        """
        self.conn.send_command(PckGenerator.generate_address_header(
            self, self.conn.local_seg_id, wants_ack) + pck)

    # ##
    # ## Status requests timeout methods
    # ##

    def request_sw_age_timeout(self, failed=False):
        """Callback method for sw_age request timeout.
        """
        if not failed:
            self.send_command(False, PckGenerator.request_sn())

    def request_status_outputs_timeout(self, failed=False, output_port=0):
        """Callback method for output status request timeout.
        """
        if not failed:
            self.send_command(False, PckGenerator.request_output_status(
                output_port.value))

    def request_status_relays_timeout(self, failed=False):
        """Callback method for relay status request timeout.
        """
        if not failed:
            self.send_command(False, PckGenerator.request_relays_status())

    def request_status_bin_sensors_timeout(self, failed=False):
        """Callback method for binary sensor status request timeout.
        """
        if not failed:
            self.send_command(False,
                              PckGenerator.request_bin_sensors_status())

    def request_status_var_timeout(self, failed=False, var=None):
        """Callback method for variable status request timeout.
        """
        # Use the chance to remove a failed "typeless variable" request
        if self.last_requested_var_without_type_in_response == var:
            self.last_requested_var_without_type_in_response = \
                lcn_defs.Var.UNKNOWN

        # Detect if we can send immediately or if we have to wait for a
        # "typeless" request first
        has_type_in_response = lcn_defs.Var.has_type_in_response(
            var, self.get_sw_age())
        if has_type_in_response or\
            (self.last_requested_var_without_type_in_response ==
             lcn_defs.Var.UNKNOWN):
            self.send_command(False, PckGenerator.request_var_status(
                var, self.get_sw_age()))
            if not has_type_in_response:
                self.last_requested_var_without_type_in_response = var

    def request_status_leds_and_logic_ops_timeout(self, failed=False):
        """Callback method for leds and logical operations status request
        timeout.
        """
        if not failed:
            self.send_command(False,
                              PckGenerator.request_leds_and_logic_ops())

    def request_status_locked_keys_timeout(self, failed=False):
        """Callback method for locked keys status request timeout.
        """
        if not failed:
            self.send_command(False, PckGenerator.request_key_lock_status())

    # ##
    # ## Methods for handling input objects
    # ##

    def new_input(self, input_obj):
        """Usually gets called by input object's process method.
        Method to handle incoming commands for this specific module (status,
        toggle_output, switch_relays, ...)
        """
        for input_callback in self.input_callbacks:
            input_callback(input_obj)

    def register_for_inputs(self, callback):
        """Registers a function for callback on PCK message received.
        """
        self.input_callbacks.append(callback)

    # ##
    # ## Methods for sending PCK commands
    # ##

    def dim_output(self, output_id, percent, ramp):
        """Creates a dim command for a single output-port and sends it to the
        connection.

        :param    int    output_id:    Output id 0..3
        :param    int    percent:      Brightness in percent 0..100
        :param    int    ramp:         Ramp time in milliseconds
        """
        self.send_command(not self.is_group(),
                          PckGenerator.dim_ouput(output_id, percent, ramp))

    def dim_all_outputs(self, percent, ramp, is1805=False):
        """Sends a dim command for all output-ports.

        :param    int    percent:    Brightness in percent 0..100
        :param    int    ramp:       Ramp time in milliseconds.
        :param    bool   is1805:     True if the target module's firmware is
                                     180501 or newer, otherwise False
        """
        self.send_command(not self.is_group(),
                          PckGenerator.dim_all_outputs(percent, ramp, is1805))

    def rel_output(self, output_id, percent):
        """Sends a command to change the value of an output-port.

        :param     int    output_id:    Output id 0..3
        :param     int    percent:      Relative brightness in percent
                                        -100..100
        """
        self.send_command(not self.is_group(),
                          PckGenerator.rel_output(output_id, percent))

    def toggle_output(self, output_id, ramp):
        """Sends a command that toggles a single output-port (on->off,
        off->on).

        :param    int    output_id:    Output id 0..3
        :param    int    ramp:         Ramp time in milliseconds
        """
        self.send_command(not self.is_group(),
                          PckGenerator.toggle_output(output_id, ramp))

    def toggle_all_outputs(self, ramp):
        """Generates a command that toggles all output-ports (on->off,
        off->on).

        :param    int    ramp:        Ramp time in milliseconds
        """
        self.send_command(not self.is_group(),
                          PckGenerator.toggle_all_outputs(ramp))

    def control_relays(self, states):
        """Sends a command to control relays.

        :param    states:   The 8 modifiers for the relay states as alist
        :type     states:   list(:class:`~pypck.lcn_defs.RelayStateModifier`)
        """
        self.send_command(not self.is_group(),
                          PckGenerator.control_relays(states))

    def control_motors(self, states):
        """Sends a command to control motors via relays.

        :param    states:   The 4 modifiers for the cover states as a list
        :type     states:   list(:class: `~pypck.cln-defs.MotorStateModifier`)
        """
        self.send_command(not self.is_group(),
                          PckGenerator.control_motors(states))

    def var_abs(self, var, value, unit=lcn_defs.VarUnit.NATIVE, is2013=None):
        """Sends a command to set the absolute value to a variable.

        :param     Var        var:      Variable
        :param     float      value:    Absolute value to set
        :param     VarUnit    unit:     Unit of variable
        """
        if value is not None and not isinstance(value, lcn_defs.VarValue):
            value = lcn_defs.VarValue.from_var_unit(value, unit, True)

        if is2013 is None:
            is2013 = self.get_sw_age() >= 0x170206
        if lcn_defs.Var.to_var_id(var) != -1:
            # Absolute commands for variables 1-12 are not supported
            if self.get_id() == 4 and self.is_group():
                # group 4 are status messages
                self.send_command(not self.is_group(),
                                  PckGenerator.update_status_var(
                                      var, value.to_native()))
            else:
                # We fake the missing command by using reset and relative
                # commands.
                self.send_command(not self.is_group(),
                                  PckGenerator.var_reset(var, is2013))
                self.send_command(not self.is_group(),
                                  PckGenerator.var_rel(
                                      var, lcn_defs.RelVarRef.CURRENT,
                                      value.to_native(), is2013))
        else:
            self.send_command(not self.is_group(),
                              PckGenerator.var_abs(var, value.to_native()))

    def var_reset(self, var, is2013=None):
        """Sends a command to reset the variable value.

        :param    Var    var:    Variable
        """
        if is2013 is None:
            is2013 = self.get_sw_age() >= 0x170206

        self.send_command(not self.is_group(),
                          PckGenerator.var_reset(var, is2013))

    def var_rel(self, var, value, unit=lcn_defs.VarUnit.NATIVE,
                value_ref=lcn_defs.RelVarRef.CURRENT, is2013=None):
        """Sends a command to change the value of a variable.

        :param     Var        var:      Variable
        :param     float      value:    Relative value to add (may also be
                                        negative)
        :param     VarUnit    unit:     Unit of variable
        """
        if value is not None and not isinstance(value, lcn_defs.VarValue):
            value = lcn_defs.VarValue.from_var_unit(value, unit, True)

        if is2013 is None:
            is2013 = self.get_sw_age() >= 0x170206
        self.send_command(not self.is_group(),
                          PckGenerator.var_rel(var, value_ref,
                                               value.to_native(), is2013))

    def lock_regulator(self, reg_id, state):
        """Sends a command to lock a regulator.

        :param    int        reg_id:        Regulator id
        :param    bool       state:         Lock state (locked=True,
                                            unlocked=False)
        """
        if reg_id != -1:
            self.send_command(not self.is_group(),
                              PckGenerator.lock_regulator(reg_id, state))

    def control_led(self, led, state):
        """Sends a command to control a led.

        :param    LedPort      led:        Led port
        :param    LedStatus    state:      Led status
        """
        self.send_command(not self.is_group(),
                          PckGenerator.control_led(led.value, state))

    def send_keys(self, keys, cmd):
        """Sends a command to send keys.

        :param    list(bool)[4][8]    keys:    2d-list with [table_id][key_id]
                                               bool values, if command should
                                               be sent to specific key
        :param    SendKeyCommand      cmd:     command to send for each table
        """
        for table_id, key_states in enumerate(keys):
            if True in key_states:
                cmds = [lcn_defs.SendKeyCommand.DONTSEND] * 4
                cmds[table_id] = cmd
                self.send_command(not self.is_group(),
                                  PckGenerator.send_keys(cmds, key_states))

    def send_keys_hit_deferred(self, keys, delay_time, delay_unit):
        """Sends a command to send keys deferred.

        :param    list(bool)[4][8]    keys:          2d-list with
                                                     [table_id][key_id] bool
                                                     values, if command should
                                                     be sent to specific key
        :param    int                 delay_time:    Delay time
        :param    TimeUnit            delay_unit:    Unit of time
        """
        for table_id, key_states in enumerate(keys):
            if True in key_states:
                self.send_command(not self.is_group(),
                                  PckGenerator.send_keys_hit_deferred(
                                      table_id, delay_time, delay_unit,
                                      key_states))

    def lock_keys(self, table_id, states):
        """Sends a command to lock keys.

        :param    int                     table_id:  Table id: 0..3
        :param    keyLockStateModifier    states:    The 8 modifiers for the
                                                     key lock states as a list
        """
        self.send_command(not self.is_group(),
                          PckGenerator.lock_keys(table_id, states))

    def lock_keys_tab_a_temporary(self, delay_time, delay_unit, states):
        """Sends a command to lock keys in table A temporary.

        :param    int        delay_time:    Time to lock keys
        :param    TimeUnit   delay_unit:    Unit of time
        :param    list(bool) states:        The 8 lock states of the keys as
                                            list (locked=True, unlocked=False)
        """
        self.send_command(not self.is_group(),
                          PckGenerator.lock_keys_tab_a_temporary(
                              delay_time, delay_unit, states))

    def dyn_text(self, row_id, text):
        """Send dynamic text to a module.

        :param    int    row_id:    Row id 0..3
        :param    str    text:      Text to send (up to 60 bytes)
        """
        encoded_text = text.encode(lcn_defs.LCN_ENCODING)

        parts = [encoded_text[12 * p:12 * p + 12] for p in range(5)]
        for part_id, part in enumerate(parts):
            if part:
                self.send_command(not self.is_group(),
                                  PckGenerator.dyn_text_part(row_id, part_id,
                                                             part))

    def pck(self, pck):
        """Send arbitrary PCK command.

        :param    str    pck:    PCK command
        """
        self.send_command(not self.is_group(), pck)


class GroupConnection(AbstractConnection):
    """Organizes communication with a specific group.
    It is assumed that all modules within this group are newer than FW170206
    """

    def __init__(self, loop, conn, seg_id, grp_id, sw_age=0x170206):
        super().__init__(loop, conn, seg_id, grp_id, True, sw_age=sw_age)

    def var_abs(self, var, value, unit=lcn_defs.VarUnit.NATIVE, is2013=None):
        # for new modules (>=0x170206)
        super().var_abs(var, value, unit, is2013=True)

        # for old modules (<0x170206)
        if var in [lcn_defs.Var.TVAR, lcn_defs.Var.R1VAR, lcn_defs.Var.R2VAR,
                   lcn_defs.Var.R1VARSETPOINT, lcn_defs.Var.R2VARSETPOINT]:
            super().var_abs(var, value, unit, is2013=False)

    def var_reset(self, var, is2013=None):
        super().var_reset(var, is2013=True)
        if var in [lcn_defs.Var.TVAR, lcn_defs.Var.R1VAR, lcn_defs.Var.R2VAR,
                   lcn_defs.Var.R1VARSETPOINT, lcn_defs.Var.R2VARSETPOINT]:
            super().var_reset(var, is2013=False)

    def var_rel(self, var, value, unit=lcn_defs.VarUnit.NATIVE,
                value_ref=lcn_defs.RelVarRef.CURRENT, is2013=None):
        super().var_rel(var, value, is2013=True)
        if var in [lcn_defs.Var.TVAR, lcn_defs.Var.R1VAR, lcn_defs.Var.R2VAR,
                   lcn_defs.Var.R1VARSETPOINT, lcn_defs.Var.R2VARSETPOINT,
                   lcn_defs.Var.THRS1, lcn_defs.Var.THRS2, lcn_defs.Var.THRS3,
                   lcn_defs.Var.THRS4, lcn_defs.Var.THRS5]:
            super().var_rel(var, value, is2013=False)

    async def activate_status_request_handler(self, item):
        '''Activates a specific TimeoutRetryHandler for status requests.
        '''
        await self.conn.segment_scan_completed

    async def activate_status_request_handlers(self):
        """Activates all TimeoutRetryHandlers for status requests.
        """
        # self.request_sw_age.activate()
        await self.conn.segment_scan_completed


class ModuleConnection(AbstractConnection):
    """Organizes communication with a specific module or group.
    """

    def __init__(self, loop, conn, seg_id, mod_id,
                 activate_status_requests=False, has_s0_enabled=False,
                 sw_age=None):

        self.has_s0_enabled = has_s0_enabled

        # Firmware version request status
        self.request_sw_age = TimeoutRetryHandler(loop,
                                                  conn.settings['NUM_TRIES'])
        self.request_sw_age.set_timeout_callback(self.request_sw_age_timeout)

        self.request_curr_pck_command_with_ack = \
            TimeoutRetryHandler(loop, conn.settings['NUM_TRIES'])
        self.request_curr_pck_command_with_ack.set_timeout_callback(
            self.request_curr_pck_command_with_ack_timeout)

        self.status_requests = StatusRequestHandler(loop, conn.settings)

        for output_port in lcn_defs.OutputPort:
            self.status_requests.set_output_timeout_callback(
                output_port, lambda failed, output_port=output_port:
                self.request_status_outputs_timeout(failed, output_port))

        self.status_requests.set_relays_timeout_callback(
            self.request_status_relays_timeout)
        self.status_requests.set_bin_sensors_timeout_callback(
            self.request_status_bin_sensors_timeout)

        for var in lcn_defs.Var:
            self.status_requests.set_var_timeout_callback(
                var, lambda failed, v=var: self.request_status_var_timeout(
                    failed, v))

        self.status_requests.set_leds_and_logic_opts_timeout_callback(
            self.request_status_leds_and_logic_ops_timeout)
        self.status_requests.set_locked_keys_callback(
            self.request_status_locked_keys_timeout)

        # List of queued PCK commands to be acknowledged by the LCN module.
        # Commands are always without address header.
        # Note that the first one might currently be "in progress".
        self.pck_commands_with_ack = deque()

        super().__init__(loop, conn, seg_id, mod_id, False, sw_age=sw_age)

        if sw_age is None:
            loop.create_task(self.get_module_sw())

        if activate_status_requests:
            loop.create_task(self.activate_status_request_handlers())

    def send_command(self, wants_ack, pck):
        """Sends a command to the module represented by this class.

        :param    bool    wants_ack:    Also send a request for acknowledge.
        :param    str     pck:          PCK command (without header).
        """
        if wants_ack:
            self.schedule_command_with_ack(pck)
        else:
            super().send_command(False, pck)

    async def get_module_sw(self):
        """Activates the software firmware request handler.
        """
        await self.conn.segment_scan_completed
        self.request_sw_age.activate()

    async def activate_status_request_handler(self, item):
        """Activates a specific TimeoutRetryHandler for status requests.
        """
        await self.conn.segment_scan_completed
        # await self.conn.lcn_connected
        await self.status_requests.activate(item)

    async def activate_status_request_handlers(self):
        """Activates all TimeoutRetryHandlers for status requests.
        """
        # self.request_sw_age.activate()
        await self.conn.segment_scan_completed
        # await self.conn.lcn_connected
        await self.status_requests.activate_all(
            activate_s0=self.has_s0_enabled)

    async def cancel_status_request_handler(self, item):
        """Cancels a specific TimeoutRetryHandler for status requests.
        """
        await self.status_requests.cancel(item)

    async def cancel_status_request_handlers(self):
        """Canecls all TimeoutRetryHandlers for status requests.
        """
        await self.status_requests.cancel_all()

    async def cancel_timeout_retries(self):
        """
        Cancels all TimeoutRetryHandlers for firmware request and status
        requests.
        """
        # module related handlers
        await self.request_sw_age.cancel()
        await self.status_requests.cancel_all()
        await self.request_curr_pck_command_with_ack.cancel()
        self.pck_commands_with_ack.clear()
        self.last_requested_var_without_type_in_response = \
            lcn_defs.Var.UNKNOWN

    def set_s0_enabled(self, s0_enabled):
        """
        Sets the activation status for S0 variables.
        :param     bool    s0_enabled:   If True, a BU4L has to be connected
        to the hardware module and S0 mode has to be activated in LCN-PRO.
        """
        self.has_s0_enabled = s0_enabled

    def get_s0_enabled(self):
        """
        Gets the activation status for S0 variables.
        """
        return self.has_s0_enabled

    def get_sw_age(self):
        """Gets the LCN module's firmware date.
        """
        return self.status_requests.get_sw_age()

    def set_sw_age(self, sw_age):
        """Sets the LCN module's firmware date.

        :param     int    swAge:    The firmware date
        """
        self.status_requests.set_sw_age(sw_age)

    def get_last_requested_var_without_type_in_response(self):
        """Returns the last requested variable without type in response.
        """
        return self.last_requested_var_without_type_in_response

    def set_last_requested_var_without_type_in_response(self, var):
        """Sets the last requested variable without type in response.
        """
        self.last_requested_var_without_type_in_response = var

    # ##
    # ## Retry logic if an acknowledge is requested
    # ##

    def schedule_command_with_ack(self, pck):
        """Schedules the next command which requests an acknowledge.
        """
        # add pck command to pck commands list
        self.pck_commands_with_ack.append(pck)
        # Try to process the new acknowledged command.
        # Will do nothing if another one is still in progress.
        self.try_process_next_command_with_ack()

    async def on_ack(self, code=-1, timeout_msec=DEFAULT_TIMEOUT_MSEC):
        """Called whenever an acknowledge is received from the LCN module.

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

    def try_process_next_command_with_ack(self):
        """Sends the next acknowledged command from the queue.
        """
        if self.pck_commands_with_ack and \
           (not self.request_curr_pck_command_with_ack.is_active()):
            self.request_curr_pck_command_with_ack.activate()

    def request_curr_pck_command_with_ack_timeout(self, failed):
        """Callback for command with acknowledge timeout.
        """
        # Use the chance to remove a failed command first
        if failed:
            self.pck_commands_with_ack.popleft()
            self.try_process_next_command_with_ack()
        else:
            pck = self.pck_commands_with_ack[0]
            self.conn.send_command(PckGenerator.generate_address_header(
                self, self.conn.local_seg_id, True) + pck)

    # ##
    # ## End of acknowledge retry logic
    # ##
