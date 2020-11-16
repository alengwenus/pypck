"""Copyright (c) 2006-2018 by the respective copyright holders.

All rights reserved. This program and the accompanying materials
are made available under the terms of the Eclipse Public License v1.0
which accompanies this distribution, and is available at
http://www.eclipse.org/legal/epl-v10.html

Contributors:
  Andre Lengwenus - port to Python and further improvements
  Tobias Juettner - initial LCN binding for openHAB (Java)
"""

from dataclasses import dataclass


@dataclass(unsafe_hash=True)
class LcnAddr:
    """Represents a LCN address (module or group).

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

    seg_id: int = -1
    addr_id: int = -1
    is_group: bool = False

    def get_seg_id(self) -> int:
        """Get the logical segment id.

        :return:    The (logical) segment id
        :rtype:     int
        """
        return self.seg_id

    def get_physical_seg_id(self, local_seg_id: int) -> int:
        """Get the physical segment id ("local" segment replaced with 0).

        Can be used to send data into the LCN bus.

        :param    int    local_seg_id:    The segment id of the local segment

        :return:    The physical segment id
        :rtype:     int
        """
        return 0 if (self.seg_id == local_seg_id) else self.seg_id

    def get_id(self) -> int:
        """Get the module id.

        :return:    The module id
        :rtype:     int
        """
        return self.addr_id

    def is_valid(self) -> bool:
        """Return if the current address is valid.

        :return:    True, if address is a valid group/module address,
                    otherwise False
        :rtype:     bool
        """
        if self.is_group:
            # seg_id:
            # 0 = Local, 1..2 = Not allowed (but "seen in the wild")
            # 3 = Broadcast, 4 = Status messages, 5..127, 128 = Segment-bus
            #     disabled (valid value)
            # addr_id:
            # 3 = Broadcast, 4 = Status messages, 5..254
            is_valid = (
                (self.seg_id >= 0)
                & (self.seg_id <= 128)
                & (self.addr_id >= 3)
                & (self.addr_id <= 254)
            )
        else:
            # seg_id:
            # 0 = Local, 1..2 = Not allowed (but "seen in the wild")
            # 3 = Broadcast, 4 = Status messages, 5..127, 128 = Segment-bus
            #     disabled (valid value)
            # addr_id:
            # 1 = LCN-PRO, 2 = LCN-GVS/LCN-W, 4 = PCHK, 5..254, 255 = Unprog.
            #     (valid, but irrelevant here)
            is_valid = (
                (self.seg_id >= 0)
                & (self.seg_id <= 128)
                & (self.addr_id >= 1)
                & (self.addr_id <= 254)
            )
        return is_valid
