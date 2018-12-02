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


class LcnAddr():
    """Represents a LCN address (module or group)
    If the segment id is 0, the address object points to modules/groups which
    are in the segment where the bus coupler is connected to. This is also the
    case if no segment coupler is present at all.

    :param    int    seg_id:    Segment id
                                (0 = Local,
                                1..2 = Not allowed (but "seen in the wild")
                                3 = Broadcast,
                                4 = Status messages,
                                5..127,
                                128 = Segment-bus disabled (valid value))
    :param    bool   is_group:  Indicates whether address point to a module
                                (False) or a group (True)


    If address represents a **module**:

    :param    int    addr_id:   Module id
                                (1 = LCN-PRO,
                                2 = LCN-GVS/LCN-W,
                                4 = PCHK,
                                5..254,
                                255 = Unprog. (valid, but irrelevant here))


    If address represents a **group**:

    :param    int    addr_id:   Group id
                                (3 = Broadcast,
                                4 = Status messages,
                                5..254)
    """

    def __init__(self, seg_id=-1, addr_id=-1, is_group=False):
        """Constructor
        """
        self.seg_id = seg_id
        self.addr_id = addr_id
        self._is_group = is_group

    def is_group(self):
        """Gets the address' module or group id (discarding the concrete
        type).

        :return:    Returns whether address points to a module(False) or
                    group(True)
        :rtype:     bool
        """
        return self._is_group

    def get_seg_id(self):
        """Gets the logical segment id.

        :return:    The (logical) segment id
        :rtype:     int
        """
        return self.seg_id

    def get_physical_seg_id(self, local_seg_id):
        """Gets the physical segment id ("local" segment replaced with 0).
        Can be used to send data into the LCN bus.

        :param    int    local_seg_id:    The segment id of the local segment

        :return:    The physical segment id
        :rtype:     int
        """
        return 0 if (self.seg_id == local_seg_id) else self.seg_id

    def get_id(self):
        """
        Gets the module id.

        :return:    The module id
        :rtype:     int
        """
        return self.addr_id

    def is_valid(self):
        """
        Returns if the current address is valid.

        :return:    True, if address is a valid group/module address,
                    otherwise False
        :rtype:     bool
        """
        if self.is_group():
            # seg_id:
            # 0 = Local, 1..2 = Not allowed (but "seen in the wild")
            # 3 = Broadcast, 4 = Status messages, 5..127, 128 = Segment-bus
            #     disabled (valid value)
            # addr_id:
            # 3 = Broadcast, 4 = Status messages, 5..254
            is_valid = (self.seg_id >= 0) & (self.seg_id <= 128) & \
                        (self.addr_id >= 3) & (self.addr_id < 254)
        else:
            # seg_id:
            # 0 = Local, 1..2 = Not allowed (but "seen in the wild")
            # 3 = Broadcast, 4 = Status messages, 5..127, 128 = Segment-bus
            #     disabled (valid value)
            # addr_id:
            # 1 = LCN-PRO, 2 = LCN-GVS/LCN-W, 4 = PCHK, 5..254, 255 = Unprog.
            #     (valid, but irrelevant here)
            is_valid = (self.seg_id >= 0) & (self.seg_id <= 128) & \
                       (self.addr_id >= 1) & (self.addr_id < 254)
        return is_valid

    def __hash__(self):
        if self.is_valid():
            hash_value = (self.is_group() << 9) + \
                         (reverse_uint8(self.get_id()) << 8) + \
                         (reverse_uint8(self.get_seg_id()))
        else:
            hash_value = -1
        return hash_value

    def __eq__(self, obj):
        return (self.is_group() == obj.is_group()) & \
               (self.get_seg_id() == obj.get_seg_id()) & \
               (self.get_id() == obj.get_id())


# only execute, if not defined before
if 'REV_UINT8' not in dir():
    REV_UINT8 = [0] * 256
    for i in range(256):
        rev = 0
        for j in range(8):
            if i & (1 << j) != 0:
                rev |= (0x80 >> j)
        REV_UINT8[i] = rev


def reverse_uint8(value):
    """Reverse the bit order of the given value.
    """
    if value < 0 | value > 255:
        raise ValueError('Invalid value.')
    return REV_UINT8[value]
