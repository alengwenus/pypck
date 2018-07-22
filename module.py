from collections import deque

from pypck.lcn_addr import LcnAddrMod
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
        self.request_sw_age = TimeoutRetryHandler(NUM_TRIES)
    
        # Output-port request status (0..3)
        self.request_status_outputs = [TimeoutRetryHandler(NUM_TRIES, MAX_STATUS_EVENTBASED_VALUEAGE_MSEC) for i in range(4)]
    
        # Relay request status (all 8)
        self.request_status_relays = TimeoutRetryHandler(NUM_TRIES, MAX_STATUS_EVENTBASED_VALUEAGE_MSEC)
        
        # Binary-sensors request status (all 8)
        self.request_status_bin_sensors = TimeoutRetryHandler(NUM_TRIES, MAX_STATUS_EVENTBASED_VALUEAGE_MSEC)
    
        # Variables request status.
        # Lazy initialization: Will be filled once the firmware version is known.
        self.request_status_vars = []
     
        # LEDs and logic-operations request status (all 12+4).
        self.request_status_leds_and_logic_ops = TimeoutRetryHandler(NUM_TRIES, MAX_STATUS_POLLED_VALUEAGE_MSEC)
     
        # Key lock-states request status (all tables, A-D).
        self.request_status_locked_keys = TimeoutRetryHandler(NUM_TRIES, MAX_STATUS_POLLED_VALUEAGE_MSEC)
    
        self.request_curr_pck_command_with_ack = TimeoutRetryHandler(NUM_TRIES)
        self.request_curr_pck_command_with_ack.set_timeout_callback(self.request_curr_pck_command_with_ack_timeout)
        
#TODO: #        self.last_requested_var_without_type_in_response = LcnDefs.Var.UNKNOWN

        # List of queued PCK commands to be acknowledged by the LCN module.
        # Commands are always without address header.
        # Note that the first one might currently be "in progress".
        self.pck_commands_with_ack = deque()
    
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
        if self.request_curr_pck_command_with_ack.is_active(): # Check if we wait for an ack.
            if len(self.pck_commands_with_ack.maxlen) > 0:
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
        if (len(self.pck_commands_with_ack) > 0) & (not self.request_curr_pck_command_with_ack.is_active()):
            self.request_curr_pck_command_with_ack.activate()
    
    def request_curr_pck_command_with_ack_timeout(self, num_retry):
        # Use the chance to remove a failed command first
        if num_retry == 0:
            self.pck_commands_with_ack.popleft()
            self.request_curr_pck_command_with_ack.reset()
            self.try_process_next_command_with_ack()
        else:
            pck = self.pck_commands_with_ack[0]
            self.conn.send_module_command(self.addr, False, pck)
    
    def new_input(self, input_obj):
        """
        Usually gets called by input object's process method.
        Method to handle incoming commands for this specific module (status, toggle_output, switch_relays, ...)
        """
        pass
    
    def dim_output(self, output_id, percent, ramp):
        """
        Generates a dim command for a single output-port and sends it to the connection.

        @param outputId 0..3
        @param percent 0..100
        @param ramp use {@link LcnDefs#timeToRampValue(int)}
        """
        if output_id < 0 or output_id > 3:
            raise ValueError('Invalid output_id.')
        n = round(percent*2)
        if (n % 2) == 0:    # Use the percent command (supported by all LCN-PCHK versions)
            cmd = 'A{:d}DI{:03d}{:03d}'.format(output_id + 1, n / 2, ramp)
        else:               # We have a ".5" value. Use the native command (supported since LCN-PCHK 2.3)
            cmd = 'O{:d}DI{:03d}{:03d}'.format(output_id + 1, n, ramp)
        
        header = PckGenerator.generate_address_header(self, self.get_seg_id(), False)
        self.conn.queue(header + cmd)

    
    