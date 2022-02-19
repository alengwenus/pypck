"""Classes to store module and group addresses."""

from dataclasses import dataclass


@dataclass(frozen=True)
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

    seg_id: int
    addr_id: int
    is_group: bool = False

    def get_physical_seg_id(self, local_seg_id: int) -> int:
        """Get the physical segment id ("local" segment replaced with 0).

        Can be used to send data into the LCN bus.

        :param    int    local_seg_id:    The segment id of the local segment

        :return:    The physical segment id
        :rtype:     int
        """
        return 0 if (self.seg_id == local_seg_id) else self.seg_id
