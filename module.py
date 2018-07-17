from pypck.lcn_addr import LcnAddrMod
from pypck.pck_commands import PckParser
from pip._vendor.cachecontrol import _cmd

class ModuleConnection(LcnAddrMod):
    '''
    Organizes communication with a specific module.
    Each output, relay, variable, ... is represented by it's own class, which can be set externally.
    Sends status requests to the connection and handles status responses.
    '''
    def __init__(self, loop, conn, seg_id, mod_id):
        self.loop = loop
        self.conn = conn
        super().__init__(seg_id = seg_id, mod_id = mod_id)
    
        self.status_update_callbacks = {'output': [],
                                        'relay': [],
                                        'binary': []}

    def register_for_status_updates(self, port, callback_func):
        if 'output' in port:
            port = output
        if 'relay' in port:
            port = 'relay'
        if 'binary' in port:
            port = 'binary'
        self.status_update_callbacks[port].append(callback_func)
    
    @staticmethod
    def generate_address_header(addr, local_seg_id, wants_ack):
        return '>{:s}{:03d}{:03d}{%s}'.format('G' if addr.is_group() else 'M',
                                              addr.get_physical_seg_id(local_seg_id),
                                              addr.get_id(),
                                              '!' if wants_ack else '.')    
    
    def process_command(self, cmd):
        """
        Is called by connection object.
        """
        output_status = PckParser.PATTERN_STATUS_OUTPUT_NATIVE.match(cmd) 
        if output_status:
            for callback in self.status_update_callbacks['output']:
                callback(**output_status.groupdict())
        
        relay_status = PckParser.PATTERN_STATUS_RELAYS.match(cmd)
        if relay_status:
            for callback in self.status_update_callbacks['relay']:
                callback(**relay_status.groupdict())
        
        binary_status = PckParser.PATTERN_STATUS_BINSENSORS.match(cmd)
        if binary_status:
            for callback in self.status_update_callbacks['binary']:
                callback(**binary_status.groupdict())
        # TODO: variables, thresholds, leds, ...
    
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
        
        header = self.generate_address_header(self, self.get_seg_id(), False)
        self.conn.queue(header + cmd)

    
    