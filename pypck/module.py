import asyncio

from collections import deque

from pypck.lcn_addr import LcnAddrMod
from pypck import lcn_defs
from pypck.pck_commands import PckGenerator
from pypck.timeout_retry import TimeoutRetryHandler



class StatusRequestHandler(object):
    def __init__(self, loop, settings):
        self.loop = loop
        self.sw_age = -1
        self.settings = settings
        
        self.activate_backlog = []
   
        # Output-port request status (0..3)
        self.request_status_outputs = [TimeoutRetryHandler(self.loop, -1, self.settings['MAX_STATUS_EVENTBASED_VALUEAGE_MSEC']) for i in range(4)]
        for output_id in range(4):
            self.request_status_outputs[output_id].set_timeout_callback(lambda failed, id=output_id: self.request_status_outputs_timeout(failed, id))
            
        # Relay request status (all 8)
        self.request_status_relays = TimeoutRetryHandler(self.loop, -1, self.settings['MAX_STATUS_EVENTBASED_VALUEAGE_MSEC'])
        
        # Binary-sensors request status (all 8)
        self.request_status_bin_sensors = TimeoutRetryHandler(self.loop, -1, self.settings['MAX_STATUS_EVENTBASED_VALUEAGE_MSEC'])
        
        # Variables request status.
        # Lazy initialization: Will be filled once the firmware version is known.
        self.request_status_vars = {}
        for i, var in enumerate(lcn_defs.Var):
            if var != lcn_defs.Var.UNKNOWN:
                self.request_status_vars[var] = TimeoutRetryHandler(self.loop, -1, self.settings['MAX_STATUS_EVENTBASED_VALUEAGE_MSEC'])

        # LEDs and logic-operations request status (all 12+4).
        self.request_status_leds_and_logic_ops = TimeoutRetryHandler(self.loop, -1, self.settings['MAX_STATUS_POLLED_VALUEAGE_MSEC'])
     
        # Key lock-states request status (all tables, A-D).
        self.request_status_locked_keys = TimeoutRetryHandler(self.loop, -1, self.settings['MAX_STATUS_POLLED_VALUEAGE_MSEC'])

        self.sw_age_known = asyncio.Future()

    def get_sw_age(self):
        return self.sw_age

    def set_sw_age(self, sw_age):
        self.sw_age = sw_age
        self.sw_age_known.set_result(True)
        
    def set_output_timeout_callback(self, output_port, callback):
        self.request_status_outputs[output_port.value].set_timeout_callback(callback)
    
    def set_relays_timeout_callback(self, callback):
        self.request_status_relays.set_timeout_callback(callback)
    
    def set_bin_sensors_timeout_callback(self, callback):
        self.request_status_bin_sensors.set_timeout_callback(callback)
    
    def set_var_timeout_callback(self, var, callback):
        if var != lcn_defs.Var.UNKNOWN:
            self.request_status_vars[var].set_timeout_callback(callback)
    
    def set_leds_and_logic_opts_timeout_callback(self, callback):
        self.request_status_leds_and_logic_ops.set_timeout_callback(callback)
    
    def set_locked_keys_callback(self, callback):
        self.request_status_locked_keys.set_timeout_callback(callback)
    
    async def activate(self, item):
        if (item in lcn_defs.Var) and (item != lcn_defs.Var.UNKNOWN):   # handle variables independently
            await self.sw_age_known     # wait until we know the software version
            if self.sw_age >= 0x170206:
                timeout_msec = self.settings['MAX_STATUS_EVENTBASED_VALUEAGE_MSEC']
            else:
                timeout_msec = self.settings['MAX_STATUS_POLLED_VALUEAGE_MSEC']
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
                                                                             
    def cancel(self, item):
        if (item in lcn_defs.Var) and (item != lcn_defs.Var.UNKNOWN):   # handle variables independently
            self.request_status_vars[item].cancel()
        elif item in lcn_defs.OutputPort:
            self.request_status_outputs[item.value].cancel()
        elif item in lcn_defs.RelayPort:
            self.request_status_relays.cancel()
        elif item in lcn_defs.BinSensorPort:
            self.request_status_bin_sensors.cancel()
        elif item in lcn_defs.LedPort:
            self.request_status_leds_and_logic_ops.cancel()
        elif item in lcn_defs.Key:
            self.request_status_locked_keys.cancel()
    
    def activate_all(self, s0 = False):
        for item in list(lcn_defs.OutputPort) + list(lcn_defs.RelayPort) + list(lcn_defs.BinSensorPort) +\
                    list(lcn_defs.LedPort) + list(lcn_defs.Key) + list(lcn_defs.Var):
            if item == lcn_defs.Var.UNKNOWN:
                continue
            if (not s0) and (item in lcn_defs.Var._s0_id_to_var):
                continue
            self.loop.create_task(self.activate(item))
    
    def cancel_all(self):
        for item in lcn_defs.OutputPort + lcn_defs.RelayPort + lcn_defs.BinSensorPort + lcn_defs.LedPort + lcn_defs.Key + lcn_defs.Var:
            if item == lcn_defs.Var.UNKNOWN:
                continue
            self.cancel(item)
        
        


class ModuleConnection(LcnAddrMod):
    """Organizes communication with a specific module.
    Sends status requests to the connection and handles status responses.
    """
    def __init__(self, loop, conn, seg_id, mod_id, activate_status_requests = False, has_s0_enabled = False):
        self.loop = loop
        self.conn = conn
        super().__init__(seg_id = seg_id, mod_id = mod_id)
    
        self.input_callbacks = []
    
        self.has_s0_enabled = has_s0_enabled

        # Firmware version request status
        self.request_sw_age = TimeoutRetryHandler(self.loop, conn.settings['NUM_TRIES'])
        self.request_sw_age.set_timeout_callback(self.request_sw_age_timeout)

        self.request_curr_pck_command_with_ack = TimeoutRetryHandler(self.loop, conn.settings['NUM_TRIES'])
        self.request_curr_pck_command_with_ack.set_timeout_callback(self.request_curr_pck_command_with_ack_timeout)
        
        self.status_requests = StatusRequestHandler(loop, self.conn.settings)
        
        for output_port in lcn_defs.OutputPort:
            self.status_requests.set_output_timeout_callback(output_port, lambda failed, output_port = output_port: self.request_status_outputs_timeout(failed, output_port))
        
        self.status_requests.set_relays_timeout_callback(self.request_status_relays_timeout)
        self.status_requests.set_bin_sensors_timeout_callback(self.request_status_bin_sensors_timeout)
        
        for var in lcn_defs.Var:
            self.status_requests.set_var_timeout_callback(var, lambda failed, v = var: self.request_status_var_timeout(failed, v))
        
        self.status_requests.set_leds_and_logic_opts_timeout_callback(self.request_status_leds_and_logic_ops_timeout)
        self.status_requests.set_locked_keys_callback(self.request_status_locked_keys_timeout)
        
        self.last_requested_var_without_type_in_response = lcn_defs.Var.UNKNOWN

        # List of queued PCK commands to be acknowledged by the LCN module.
        # Commands are always without address header.
        # Note that the first one might currently be "in progress".
        self.pck_commands_with_ack = deque()
        
        loop.create_task(self.get_module_sw())
        
        if activate_status_requests:
            loop.create_task(self.activate_status_request_handlers())

    async def get_module_sw(self):
        await self.conn.segment_scan_completed
        self.request_sw_age.activate()

    async def activate_status_request_handler(self, item):
        '''Activates a specific TimeoutRetryHandler for status requests.
        '''
        await self.conn.segment_scan_completed
        #await self.conn.lcn_connected
        self.loop.create_task(self.status_requests.activate(item))

    async def activate_status_request_handlers(self):
        """Activates all TimeoutRetryHandlers for status requests.
        """
        #self.request_sw_age.activate()
        await self.conn.segment_scan_completed
        # await self.conn.lcn_connected
        self.status_requests.activate_all(s0 = self.has_s0_enabled)

    def cancel_timeout_retries(self):
        """
        Cancels all TimeoutRetryHandlers for firmware request and status requests.
        """
        # module related handlers
        self.request_sw_age.cancel()
        self.status_requests.cancel_all()
        self.last_requested_var_without_type_in_response = lcn_defs.Var.UNKNOWN
    
    def set_s0_enabled(self, s0_enabled):
        """
        Sets the activation status for S0 variables.
        @param s0_enabled if True, a BU4L has to be connected to the hardware module and S0 mode
        has to be activated in LCN-PRO. 
        """
        self.has_s0_enabled = s0_enabled
    
    def get_s0_enabled(self):
        """
        Gets the activation status for S0 variables.
        """
        return self.has_s0_enabled
    
    def get_sw_age(self):
        """
        Gets the LCN module's firmware date.
        """
        return self.status_requests.get_sw_age()

    def set_sw_age(self, sw_age):
        """
        Sets the LCN module's firmware date.
        
        @param swAge the date
        """
        self.status_requests.set_sw_age(sw_age)


    def get_last_requested_var_without_type_in_response(self):
        return self.last_requested_var_without_type_in_response

    def set_last_requested_var_without_type_in_response(self, var):
        self.last_requested_var_without_type_in_response = var


    ###
    ### Retry logic if an acknowledge is requested 
    ###
    
    def schedule_command_with_ack(self, pck):
        self.pck_commands_with_ack.append(pck)  # add pck command to pck commands list
        # Try to process the new acknowledged command. Will do nothing if another one is still in progress.
        self.try_process_next_command_with_ack()

    def on_ack(self, code, timeout_msec):
        """
        Called whenever an acknowledge is received from the LCN module.
    
        @param code the LCN internal code. -1 means "positive" acknowledge
        @param timeoutMSec the time to wait for a response before retrying a request
        """
        if self.request_curr_pck_command_with_ack.is_active(): # Check if we wait for an ack.
            if len(self.pck_commands_with_ack) > 0:
                self.pck_commands_with_ack.popleft()
            self.request_curr_pck_command_with_ack.reset()
            # Try to process next acknowledged command
            self.try_process_next_command_with_ack()
    
    def try_process_next_command_with_ack(self):
        """
        Sends the next acknowledged command from the queue.

        @param conn the {@link Connection} belonging to this {@link ModInfo}
        @param timeoutMSec the time to wait for a response before retrying a request
        @return true if a new command was sent
        """
        if (len(self.pck_commands_with_ack) > 0) and (not self.request_curr_pck_command_with_ack.is_active()):
            self.request_curr_pck_command_with_ack.activate()
    
    def request_curr_pck_command_with_ack_timeout(self, failed):
        # Use the chance to remove a failed command first
        if failed:
            self.pck_commands_with_ack.popleft()
            self.try_process_next_command_with_ack()
        else:
            pck = self.pck_commands_with_ack[0]
            self.conn.send_command(PckGenerator.generate_address_header(self, self.conn.local_seg_id, True) + pck)
    
    ###
    ### End of acknowledge retry logic
    ###
    
    
    def send_command(self, wants_ack, pck):
        """
        Sends a command to the module represented by this class.
        """
        if (not self.is_group()) and wants_ack:
            self.schedule_command_with_ack(pck)
        else:
            self.conn.send_command(PckGenerator.generate_address_header(self, self.conn.local_seg_id, wants_ack) + pck)
    
    def new_input(self, input_obj):
        """
        Usually gets called by input object's process method.
        Method to handle incoming commands for this specific module (status, toggle_output, switch_relays, ...)
        """
        for input_callback in self.input_callbacks:
            input_callback(input_obj)
    
    def register_for_module_inputs(self, callback):
        self.input_callbacks.append(callback)
    

    ###
    ### Status requests timeout methods
    ###
    
    def request_sw_age_timeout(self, failed):
        if not failed:
            self.send_command(False, PckGenerator.request_sn())
    
    def request_status_outputs_timeout(self, failed, output_port):
        if not failed:
            self.send_command(False, PckGenerator.request_output_status(output_port.value))

    def request_status_relays_timeout(self, failed):
        if not failed:
            self.send_command(False, PckGenerator.request_relays_status())
        
    def request_status_bin_sensors_timeout(self, failed):
        if not failed:
            self.send_command(False, PckGenerator.request_bin_sensors_status())

    def request_status_var_timeout(self, failed, var):
        # Use the chance to remove a failed "typeless variable" request
        if self.last_requested_var_without_type_in_response == var:
            self.last_requested_var_without_type_in_response = lcn_defs.Var.UNKNOWN

        # Detect if we can send immediately or if we have to wait for a "typeless" request first
        has_type_in_response = lcn_defs.Var.has_type_in_response(var, self.get_sw_age())
        if has_type_in_response or (self.last_requested_var_without_type_in_response == lcn_defs.Var.UNKNOWN):
            self.send_command(False, PckGenerator.request_var_status(var, self.get_sw_age()))
            if not has_type_in_response:
                self.last_requested_var_without_type_in_response = var
        
    def request_status_leds_and_logic_ops_timeout(self, failed):
        if not failed:
            self.send_command(False, PckGenerator.request_leds_and_logic_ops())
    
    def request_status_locked_keys_timeout(self, failed):
        if not failed:
            self.send_command(False, PckGenerator.request_key_lock_status())


    ###
    ### Methods for sending PCK commands
    ###
    
    def dim_output(self, output_id, percent, ramp):
        """
        Creates a dim command for a single output-port and sends it to the connection.

        @param outputId 0..3
        @param percent 0..100
        @param ramp use {@link LcnDefs#timeToRampValue(int)}
        """
        self.send_command(not self.is_group(),
                          PckGenerator.dim_ouput(output_id, percent, ramp))
    
    def dim_all_outputs(self, percent, ramp, is1805=False):
        """
        Sends a dim command for all output-ports.

        @param percent 0..100
        @param ramp use {@link LcnDefs#timeToRampValue(int)} (might be ignored in some cases)
        @param is1805 true if the target module's firmware is 180501 or newer
        """
        self.send_command(not self.is_group(),
                          PckGenerator.dim_all_outputs(percent, ramp, is1805))
        
    def rel_output(self, output_id, percent):
        """
        Sends a command to change the value of an output-port.

        @param outputId 0..3
        @param percent -100..100
        """
        self.send_command(not self.is_group(),
                          PckGenerator.rel_output(output_id, percent))
        
    def toggle_output(self, output_id, ramp):
        """
        Sends a command that toggles a single output-port (on->off, off->on).

        @param outputId 0..3
        @param ramp see {@link LcnDefs#timeToRampValue(int)}
        """
        self.send_command(not self.is_group(),
                          PckGenerator.toggle_output(output_id, ramp))
        
    def toggle_all_outputs(self, ramp):
        """
        Generates a command that toggles all output-ports (on->off, off->on).

        @param ramp see {@link LcnDefs#timeToRampValue(int)}
        """
        self.send_command(not self.is_group(),
                          PckGenerator.toggle_all_outputs(ramp))
        
    def control_relays(self, states):
        """
        Sends a command to control relays.

        @param states the 8 modifiers for the relay states as a list
        """
        self.send_command(not self.is_group(),
                          PckGenerator.control_relays(states))
    
    def control_motors(self, states):
        """
        Sends a command to control motors via relays.
        
        @param states the 4 modifiers for the cover states as a list
        """
        self.send_command(not self.is_group(),
                          PckGenerator.control_motors(states))

    def var_abs(self, var, value, unit = lcn_defs.VarUnit.NATIVE):
        '''
        Sends a command to set the absolute value to a variable.
        
        @oaram var lcn_defs.Var instance
        @param value int or float
        @param unit lcn_defs.VarUnit instance
        '''
        if value != None and not isinstance(value, lcn_defs.VarValue):
            value = lcn_defs.VarValue.from_var_unit(value, unit, True)
        
        is2013 = self.get_sw_age() >= 0x170206
        if lcn_defs.Var.to_var_id(var) != -1:
            # Absolute commands for variables 1-12 are not supported
            if self.get_id() == 4 and self.is_group():
                # group 4 are status messages
                self.send_command(not self.is_group(),
                                  PckGenerator.update_status_var(var, value.to_native()))
            else:
                # We fake the missing command by using reset and relative commands.
                self.send_command(not self.is_group(),
                                  PckGenerator.var_reset(var, is2013))
                self.send_command(not self.is_group(),
                                  PckGenerator.var_rel(var, lcn_defs.RelVarRef.CURRENT, value.to_native(), is2013))
        else:
            self.send_command(not self.is_group(),
                              PckGenerator.var_abs(var, value.to_native()))
        
      