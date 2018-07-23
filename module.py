from collections import deque

from pypck.lcn_addr import LcnAddrMod
from pypck import lcn_defs
from pypck.pck_commands import PckParser, PckGenerator
from pypck.timeout_retry import TimeoutRetryHandler
import pck_commands

# Total number of request to sent before going into failed-state.
NUM_TRIES = 3

# Poll interval for status values that automatically send their values on change.
MAX_STATUS_EVENTBASED_VALUEAGE_MSEC = 600000

# Poll interval for status values that do not send their values on change (always polled).
MAX_STATUS_POLLED_VALUEAGE_MSEC = 30000

# Status request delay after a command has been send which potentially changed that status.
STATUS_REQUEST_DELAY_AFTER_COMMAND_MSEC = 2000


class ModuleConnection(LcnAddrMod):
    '''
    Organizes communication with a specific module.
    Sends status requests to the connection and handles status responses.
    '''
    def __init__(self, loop, conn, seg_id, mod_id):
        self.loop = loop
        self.conn = conn
        super().__init__(seg_id = seg_id, mod_id = mod_id)
    
        self.sw_age = -1
        
        # Firmware version request status
        self.request_sw_age = TimeoutRetryHandler(self.loop, NUM_TRIES)
        self.request_sw_age.set_timeout_callback(self.request_sw_age_timeout)
    
        # Output-port request status (0..3)
        self.request_status_outputs = [TimeoutRetryHandler(self.loop, -1, MAX_STATUS_EVENTBASED_VALUEAGE_MSEC) for i in range(4)]
        #for output_id in range(4):
        self.request_status_outputs[0].set_timeout_callback(lambda failed: self.request_status_outputs_timeout(failed, 0))
        self.request_status_outputs[1].set_timeout_callback(lambda failed: self.request_status_outputs_timeout(failed, 1))
        self.request_status_outputs[2].set_timeout_callback(lambda failed: self.request_status_outputs_timeout(failed, 2))
        self.request_status_outputs[3].set_timeout_callback(lambda failed: self.request_status_outputs_timeout(failed, 3))
        
        # Relay request status (all 8)
        self.request_status_relays = TimeoutRetryHandler(self.loop, -1, MAX_STATUS_EVENTBASED_VALUEAGE_MSEC)
        self.request_status_relays.set_timeout_callback(self.request_status_relays_timeout)
        
        # Binary-sensors request status (all 8)
        self.request_status_bin_sensors = TimeoutRetryHandler(self.loop, -1, MAX_STATUS_EVENTBASED_VALUEAGE_MSEC)
        self.request_status_bin_sensors.set_timeout_callback(self.request_status_bin_sensors_timeout)
        
        # Variables request status.
        # Lazy initialization: Will be filled once the firmware version is known.
        self.request_status_vars = {}
     
        # LEDs and logic-operations request status (all 12+4).
        self.request_status_leds_and_logic_ops = TimeoutRetryHandler(self.loop, -1, MAX_STATUS_POLLED_VALUEAGE_MSEC)
        self.request_status_leds_and_logic_ops.set_timeout_callback(self.request_status_leds_and_logic_ops_timeout)
     
        # Key lock-states request status (all tables, A-D).
        self.request_status_locked_keys = TimeoutRetryHandler(self.loop, -1, MAX_STATUS_POLLED_VALUEAGE_MSEC)
        self.request_status_locked_keys.set_timeout_callback(self.request_status_locked_keys_timeout)    
        
        self.request_curr_pck_command_with_ack = TimeoutRetryHandler(self.loop, NUM_TRIES)
        self.request_curr_pck_command_with_ack.set_timeout_callback(self.request_curr_pck_command_with_ack_timeout)
        
#TODO: #        self.last_requested_var_without_type_in_response = LcnDefs.Var.UNKNOWN

        # List of queued PCK commands to be acknowledged by the LCN module.
        # Commands are always without address header.
        # Note that the first one might currently be "in progress".
        self.pck_commands_with_ack = deque()

    def activate_status_request_handlers(self):
        self.request_sw_age.activate()
        for output_id in range(4):
            self.request_status_outputs[output_id].activate()
        self.request_status_relays.activate()
        self.request_status_bin_sensors.activate()
    
        #TODO: status_vars, status_leds_and_logic_ops, status_locked_keys

    def initialize_variables(self):
        # Firmware version has to be set first
        if self.sw_age != -1:
            if len(self.request_status_vars) == 0:
                for var in lcn_defs.var.values():
                    if var != lcn_defs.var.UNKNOWN:
                        self.request_status_vars[var] = TimeoutRetryHandler(self.loop, -1, MAX_STATUS_EVENTBASED_VALUEAGE_MSEC if self.sw_age >= 0x170206 else MAX_STATUS_POLLED_VALUEAGE_MSEC)
    
    def get_sw_age(self):
        """
        Gets the LCN module's firmware date.
        """
        return self.sw_age

    def set_sw_age(self, sw_age):
        """
        Sets the LCN module's firmware date.
        
        @param swAge the date
        """
        self.sw_age = sw_age

    def reset_not_cached_status_requests(self):
        """
        Resets all status requests.
        Helpful to re-request initial data in case a new {@link LcnBindingConfig} has been loaded.
        """
        for rs in self.request_status_outputs:
            rs.reset()
        self.request_status_relays.reset()
        self.request_status_bin_sensors.reset()
        for rs in self.request_status_vars:
            rs.reset()
        self.request_status_leds_and_logic_ops.reset()
        self.request_status_locked_keys.reset()
#TODO:        self.last_requested_var_without_type_in_response = LcnDefs.Var.UNKNOWN

    def get_last_requested_var_without_type_in_response(self):
        pass
#TODO:        return self.last_requested_var_without_type_in_response

    def set_last_requested_var_without_type_in_response(self, var):
        pass
#TODO:        self.last_requested_var_without_type_in_response = var

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
        #print('Ack received!')
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
        #print('AckTimeout', failed)
        if failed:
            self.pck_commands_with_ack.popleft()
            # self.request_curr_pck_command_with_ack.reset()
            self.try_process_next_command_with_ack()
        else:
            pck = self.pck_commands_with_ack[0]
            self.conn.send_command(PckGenerator.generate_address_header(self, self.conn.local_seg_id, True) + pck)
    
    def new_input(self, input_obj):
        """
        Usually gets called by input object's process method.
        Method to handle incoming commands for this specific module (status, toggle_output, switch_relays, ...)
        """
        #print(input_obj)
        pass
    

    ### Status requests timeout methods
    def request_sw_age_timeout(self, failed):
        if not failed:
            cmd = PckGenerator.request_sn()
            self.conn.send_module_command(self, False, cmd)
    
    def request_status_outputs_timeout(self, failed, output_id):
        if not failed:
            cmd = PckGenerator.request_output_status(output_id)
            self.conn.send_module_command(self, not self.is_group(), cmd)

    def request_status_relays_timeout(self, failed):
        if not failed:
            cmd = PckGenerator.request_relays_status()
            self.conn.send_module_command(self, not self.is_group(), cmd)
        
    def request_status_bin_sensors_timeout(self, failed):
        if not failed:
            cmd = PckGenerator.request_bin_sensors_status()
            self.conn.send_module_command(self, not self.is_group(), cmd)

    def request_status_leds_and_logic_ops_timeout(self, failed):
        pass
    
    def request_status_locked_keys_timeout(self, failed):
        pass


    ### Methods for sending PCK commands
    
    def dim_output(self, output_id, percent, ramp):
        """
        Sends a dim command for a single output-port and sends it to the connection.

        @param outputId 0..3
        @param percent 0..100
        @param ramp use {@link LcnDefs#timeToRampValue(int)}
        """
        cmd = PckGenerator.dim_ouput(output_id, percent, ramp)       
        self.conn.send_module_command(self, not self.is_group(), cmd)
    
    def dim_all_outputs(self, percent, ramp, is1805=False):
        """
        Sends a dim command for all output-ports.

        @param percent 0..100
        @param ramp use {@link LcnDefs#timeToRampValue(int)} (might be ignored in some cases)
        @param is1805 true if the target module's firmware is 180501 or newer
        """
        cmd = PckGenerator.dim_all_outputs(percent, ramp, is1805)
        self.conn.send_module_command(self, not self.is_group(), cmd)
        
    def rel_output(self, output_id, percent):
        """
        Sends a command to change the value of an output-port.

        @param outputId 0..3
        @param percent -100..100
        """
        cmd = PckGenerator.rel_output(output_id, percent)
        self.conn.send_module_command(self, not self.is_group(), cmd)
        
    def toggle_output(self, output_id, ramp):
        """
        Sends a command that toggles a single output-port (on->off, off->on).

        @param outputId 0..3
        @param ramp see {@link LcnDefs#timeToRampValue(int)}
        """
        cmd = PckGenerator.toggle_output(output_id, ramp)
        self.conn.send_module_command(self, not self.is_group(), cmd)
        
    def toggle_all_outputs(self, ramp):
        """
        Generates a command that toggles all output-ports (on->off, off->on).

        @param ramp see {@link LcnDefs#timeToRampValue(int)}
        """
        cmd = PckGenerator.toggle_all_outputs(ramp)
        self.conn.send_module_command(self, not self.is_group(), cmd)
        
    def control_relays(self, states):
        """
        Sends a command to control relays.

        @param states the 8 modifiers for the relay states as a list
        """
        cmd = PckGenerator.control_relays(states)
        self.conn.send_module_command(self, not self.is_group(), cmd)
        
    