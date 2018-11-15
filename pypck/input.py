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

import logging
import re

from pypck import lcn_defs
from pypck.lcn_addr import LcnAddr
from pypck.pck_commands import PckParser, PckGenerator
from pypck.timeout_retry import DEFAULT_TIMEOUT_MSEC

_LOGGER = logging.getLogger(__name__)


class Input(object):
    """
    Parent class for all input data read from LCN-PCHK.
    
    An implementation of :class:`~pypck.input.Input` has to provide easy accessible attributes
    and/or methods to expose the PCK command properties to the user.
    Each Input object provides an implementation of :func:`~pypck.input.Input.try_parse`
    static method, to parse the given plain text PCK command. If the command can be parsed by
    the Input object, a list of instances of :class:`~pypck.input.Input` is returned. 
    If parsing is successful, the :func:`~pypck.input.Input.process` method can be called
    to trigger further actions.
    """

    def __init__(self):
        pass

    @staticmethod
    def try_parse(input):
        """
        Tries to parse the given input text.
        Will return a list of parsed Inputs. The list might be empty (but not null).
       
        :param    input:     the input data received from LCN-PCHK
        :type     input:     :class:`~pypck.input.Input`
        :return:             The parsed Inputs (never null)
        :rtype:              List with instances of :class:`~pypck.input.Input`
        """
        raise NotImplementedError

    def process(self, conn):
        """
        Processes the :class:`~pypck.input.Input` instance and triggers further actions.
        
        :param ~pypck.connection.PchkConnectionManager conn: Connection manager object 
        """
        raise NotImplementedError


class ModInput(Input):
    """
    Parent class of all inputs having an LCN module as its source.
    
    The class in inherited from :class:`~pypck.input.Input`
    """

    def __init__(self, physical_source_addr):
        super().__init__()
        self.physical_source_addr = physical_source_addr
        self.logical_source_addr = LcnAddr()

    def get_logical_source_addr(self):
        return self.logical_source_addr

    def process(self, conn):
        if conn.is_ready():  # Skip if we don't have all necessary bus info yet
            self.logical_source_addr = conn.physical_to_logical(self.physical_source_addr)

# ## Plain text inputs


class AuthOk(Input):

    @staticmethod
    def try_parse(input):
        if input == PckParser.AUTH_OK:
            return [AuthOk()]

    def process(self, conn):
        conn.on_auth_ok()


class AuthPassword(Input):

    @staticmethod
    def try_parse(input):
        if input == PckParser.AUTH_PASSWORD:
            return [AuthPassword()]

    def process(self, conn):
        conn.send_command(conn.password)


class AuthUsername(Input):

    @staticmethod
    def try_parse(input):
        if input == PckParser.AUTH_USERNAME:
            return [AuthUsername()]

    def process(self, conn):
        conn.send_command(conn.username)


class LcnConnState(Input):

    def __init__(self, is_lcn_connected):
        super().__init__()
        self._is_lcn_connected = is_lcn_connected

    @property
    def is_lcn_connected(self):
        return self._is_lcn_connected

    @staticmethod
    def try_parse(input):
        if input == PckParser.LCNCONNSTATE_CONNECTED:
            return [LcnConnState(True)]
        elif input == PckParser.LCNCONNSTATE_DISCONNECTED:
            return [LcnConnState(False)]

    def process(self, conn):
        if self.is_lcn_connected:
            _LOGGER.debug('{}: LCN is connected.'.format(conn.connection_id))
            conn.on_successful_login()
            conn.send_command(PckGenerator.set_operation_mode(conn.dim_mode, conn.status_mode))
        else:
            _LOGGER.debug('{}: LCN is not connected.'.format(conn.connection_id))

# ## Inputs received from modules


class ModAck(ModInput):

    def __init__(self, physical_source_addr, code):
        super().__init__(physical_source_addr)
        self.code = code

    def get_code(self):
        return self.code

    @staticmethod
    def try_parse(input):
        matcher_pos = PckParser.PATTERN_ACK_POS.match(input)
        if matcher_pos:
            addr = LcnAddr(int(matcher_pos.group('seg_id')),
                           int(matcher_pos.group('mod_id')))
            return [ModAck(addr, -1)]

        matcher_neg = PckParser.PATTERN_ACK_NEG.match(input)
        if matcher_neg:
            addr = LcnAddr(int(matcher_neg.group('seg_id')),
                           int(matcher_neg.group('mod_id')))
            return [ModAck(addr, matcher_neg.group('code'))]

    def process(self, conn):
        super().process(conn)  # Will replace source segment 0 with the local segment id
        module_conn = conn.get_address_conn(self.logical_source_addr)
        module_conn.on_ack(self.code, DEFAULT_TIMEOUT_MSEC)


class ModSk(ModInput):
    """Segment information received from an LCN segment coupler.
    """

    def __init__(self, physical_source_addr, reported_seg_id):
        super().__init__(physical_source_addr)
        self.reported_seg_id = reported_seg_id

    def get_reported_seg_id(self):
        return self.reported_seg_id

    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_SK_RESPONSE.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            return [ModSk(addr, int(matcher.group('id')))]

    def process(self, conn):
        if self.physical_source_addr.seg_id == 0:
            conn.set_local_seg_id(self.reported_seg_id)
        super().process(conn)  # Will replace source segment 0 with the local segment id
        conn.status_segment_scan.cancel()
        for module_conn in conn.address_conns.values():
            conn.loop.create_task(module_conn.activate_status_request_handlers())


class ModSn(ModInput):
    """Serial number and firmware version received from an LCN module.
    """

    def __init__(self, physical_source_addr, sw_age):
        super().__init__(physical_source_addr)
        self.sw_age = sw_age

    def get_sw_age(self):
        return self.sw_age

    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_SN.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            return [ModSn(addr, int(matcher.group('sw_age'), 16))]

    def process(self, conn):
        super().process(conn)  # Will replace source segment 0 with the local segment id
        module_conn = conn.get_address_conn(self.logical_source_addr)
        module_conn.set_sw_age(self.sw_age)
        module_conn.request_sw_age.cancel()


class ModStatusOutput(ModInput):
    """Status of an output-port received from an LCN module.
    """

    def __init__(self, physical_source_addr, output_id, percent):
        super().__init__(physical_source_addr)
        self.output_id = output_id
        self.percent = percent

    def get_output_id(self):
        return self.output_id

    def get_percent(self):
        return self.percent

    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_STATUS_OUTPUT_PERCENT.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            return [ModStatusOutput(addr, int(matcher.group('output_id')) - 1, float(matcher.group('percent')))]

        matcher = PckParser.PATTERN_STATUS_OUTPUT_NATIVE.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            return [ModStatusOutput(addr, int(matcher.group('output_id')), float(matcher.group('value')) / 2.)]

    def process(self, conn):
        super().process(conn)  # Will replace source segment 0 with the local segment id
        module_conn = conn.get_address_conn(self.logical_source_addr)
        # module_conn.request_status_outputs[self.output_id].cancel()
        module_conn.new_input(self)


class ModStatusRelays(ModInput):
    """Status of 8 relays received from an LCN module.
    """

    def __init__(self, physical_source_addr, states):
        super().__init__(physical_source_addr)
        self.states = states

    def get_state(self, relay_id):
        """
        Gets the state of a single relay.
        
        :param    int    relay_id:    Relay id (0..7)
        
        :return:                      The relay's state
        :rtype:   bool
        """
        return self.states[relay_id]

    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_STATUS_RELAYS.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            return [ModStatusRelays(addr, PckParser.get_boolean_value(int(matcher.group('byte_value'))))]

    def process(self, conn):
        super().process(conn)  # Will replace source segment 0 with the local segment id
        module_conn = conn.get_address_conn(self.logical_source_addr)
        # module_conn.request_status_relays.cancel()
        module_conn.new_input(self)


class ModStatusBinSensors(ModInput):
    """Status of 8 binary sensors received from an LCN module.
    """

    def __init__(self, physical_source_addr, states):
        super().__init__(physical_source_addr)
        self.states = states

    def get_state(self, bin_sensor_id):
        """
        Gets the state of a single binary-sensor.
        
        :param    int    bin_sensor_id:    Binary sensor id (0..7)
        
        :return:                           The binary-sensor's state
        :rtype:   bool
        """
        return not self.states[bin_sensor_id]

    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_STATUS_BINSENSORS.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            return [ModStatusBinSensors(addr, PckParser.get_boolean_value(int(matcher.group('byte_value'))))]

    def process(self, conn):
        super().process(conn)  # Will replace source segment 0 with the local segment id
        module_conn = conn.get_address_conn(self.logical_source_addr)
        # module_conn.request_status_relays.cancel()
        module_conn.new_input(self)


class ModStatusVar(ModInput):
    """
    Status of a variable received from an LCN module.
    """

    def __init__(self, physical_source_addr, orig_var, value):
        super().__init__(physical_source_addr)
        self.orig_var = orig_var
        self.value = value
        self.var = self.orig_var

    def get_var(self):
        """
        Gets the variable's real type.
        
        :return:        The real type
        :rtype:        :class:`~pypck.lcn_defs.Var`
        """
        return self.var

    def get_value(self):
        """
        Gets the variable's value.

        :return:    The value of the variable.
        :rtype:     int
        """
        return self.value

    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_STATUS_VAR.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            var = lcn_defs.Var.var_id_to_var(int(matcher.group('id')) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group('value')))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_STATUS_SETVAR.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            var = lcn_defs.Var.set_point_id_to_var(int(matcher.group('id')) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group('value')))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_STATUS_THRS.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            var = lcn_defs.Var.thrs_id_to_var(int(matcher.group('register_id')) - 1, int(matcher.group('thrs_id')) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group('value')))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_STATUS_S0INPUT.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            var = lcn_defs.Var.s0_id_to_var(int(matcher.group('id')) - 1)
            value = lcn_defs.VarValue.from_native(int(matcher.group('value')))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_VAR_GENERIC.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            var = lcn_defs.Var.UNKNOWN
            value = lcn_defs.VarValue.from_native(int(matcher.group('value')))
            return [ModStatusVar(addr, var, value)]

        matcher = PckParser.PATTERN_THRS5.match(input)
        if matcher:
            ret = []
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            for thrs_id in range(5):
                var = lcn_defs.Var.var_id_to_var(int(matcher.group('id')) - 1)
                value = lcn_defs.VarValue.from_native(int(matcher.group('value{:d}'.format(thrs_id + 1))))
                ret.append(ModStatusVar(addr, var, value))
            return ret

    def process(self, conn):
        super().process(conn)  # Will replace source segment 0 with the local segment id
        module_conn = conn.get_address_conn(self.logical_source_addr)
        if self.orig_var == lcn_defs.Var.UNKNOWN:
            self.var = module_conn.get_last_requested_var_without_type_in_response()
        else:
            self.var = self.orig_var

        if self.var != lcn_defs.Var.UNKNOWN:
            if module_conn.get_last_requested_var_without_type_in_response() == self.var:
                module_conn.set_last_requested_var_without_type_in_response(lcn_defs.Var.UNKNOWN)  # Reset
#             if self.var in module_conn.request_status_vars:
#                 module_conn.request_status_vars[self.var].cancel()
        module_conn.new_input(self)


class ModStatusLedsAndLogicOps(ModInput):
    """Status of LEDs and logic-operations received from an LCN module.

    :param    int      physicalSourceAddr:   The physical source address
    :param    states_led:                    The 12 LED states
    :type     states_led:                    list(:class:`~pypck.lcn_defs.LedStatus`)
    :param    states_logic_ops:              The 4 logic-operation states
    :type     states_logic_ops:              list(:class:`~pypck.lcn_defs.LogicOpStatus`)         
    """

    def __init__(self, physical_source_addr, states_led, states_logic_ops):
        """Constructor."""
        super().__init__(physical_source_addr)
        self.states_led = states_led  # 12x LED status.
        self.states_logic_ops = states_logic_ops  # 4x logic-operation status.

    def get_led_state(self, led_id):
        """Gets the status of a single LED.

        :param    int    led_id:   LED id (0..11)
        :return:                   The LED's status
        :rtype:   list(:class:`~pypck.lcn_defs.LedStatus`)
        """
        return self.states_led[led_id]

    def get_logic_op_state(self, logic_op_id):
        """Gets the status of a single logic operation.

        :param    int    logic_op_id:    Logic operation id (0..3)
        :return:    The logic-operation's status
        :rtype:     list(:class:`~pypck.lcn_defs.LogicOpStatus`)
        """
        return self.states_logic_ops[logic_op_id]

    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_STATUS_LEDSANDLOGICOPS.match(input)
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))

            led_states = matcher.group('led_states').upper()
            states_leds = [lcn_defs.LedStatus(led_state) for led_state in led_states]

            logic_op_states = matcher.group('logic_op_states').upper()
            states_logic_ops = [lcn_defs.LogicOpStatus(logic_op_state) for logic_op_state in logic_op_states]
            return [ModStatusLedsAndLogicOps(addr, states_leds, states_logic_ops)]

    def process(self, conn):
        super().process(conn)  # Will replace source segment 0 with the local segment id
        module_conn = conn.get_address_conn(self.logical_source_addr)
        # module_conn.request_status_leds_and_logic_ops.cancel()
        module_conn.new_input(self)


class ModStatusKeyLocks(ModInput):
    """
    Status of locked keys received from an LCN module.
    
    :param    int                physicalSourceAddr:    The source address
    :param    list(list(bool))   states:                The 4x8 key-lock states        
    """

    def __init__(self, physical_source_id, states):
        """Constructor.
        """
        super().__init__(physical_source_id)
        self.states = states

    def get_state(self, table_id, key_id):
        """Gets the lock-state of a single key.

        :param    int    tableId:    Table id: (0..3  =>  A..D)
        :param    int    keyId:      Key id (0..7  =>  1..8)
        :return:  The key's lock-state
        :rtype:   bool
        """
        return self.states[table_id][key_id]

    @staticmethod
    def try_parse(input):
        matcher = PckParser.PATTERN_STATUS_KEYLOCKS.match(input)
        states = []
        if matcher:
            addr = LcnAddr(int(matcher.group('seg_id')),
                           int(matcher.group('mod_id')))
            for i in range(4):
                s = matcher.group('table{:d}'.format(i))
                if s is not None:
                    states.append(PckParser.get_boolean_value(int(s)))
#                else:
#                     states.append([])
            return [ModStatusKeyLocks(addr, states)]

    def process(self, conn):
        super().process(conn)  # Will replace source segment 0 with the local segment id
        module_conn = conn.get_address_conn(self.logical_source_addr)
        # module_conn.request_status_key_locks.cancel()
        module_conn.new_input(self)

# ## Other inputs


class Unknown(Input):

    def __init__(self, input):
        super().__init__()
        self._input = input

    @staticmethod
    def try_parse(input):
        return [Unknown(input)]

    @property
    def input(self):
        return self._input

    def process(self, conn):
        pass


class InputParser(object):
    parsers = [AuthUsername,
               AuthPassword,
               AuthOk,
               LcnConnState,
               ModAck,
               ModSk,
               ModSn,
               ModStatusOutput,
               ModStatusRelays,
               ModStatusBinSensors,
               ModStatusVar,
               ModStatusLedsAndLogicOps,
               ModStatusKeyLocks,
               Unknown]

    @staticmethod
    def parse(input):
        for parser in InputParser.parsers:
            ret = parser.try_parse(input)
            if ret is not None:
                return ret

