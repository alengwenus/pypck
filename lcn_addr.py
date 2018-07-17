

class LcnAddr(object):
    """
    Represents a LCN address (module or group)
    """
    def __init__(self, seg_id=-1):
        """
        seg_id: -1 is an invalid segment id (default)
        """
        self.seg_id = seg_id
    
    def get_seg_id(self):
        """
        Get the (logical) segment id
        @return the segment id
        """
        return self.seg_id
    
    def get_physical_seg_id(self, local_seg_id):
        """
        Gets the physical segment id ("local" segment replaced with 0).
        Can be used to send data into the LCN bus.

        @param localSegId the segment id of the local segment
        @return the physical segment id        
        """
        return 0 if (self.seg_id == local_seg_id) else self.seg_id
    
    def is_valid(self):
        """
        Queries the concrete address type.
        
        @return true if address is a group address (module address otherwise)
        """
        raise NotImplementedError
    
    def is_group(self):
        """
        Gets the address' module or group id (discarding the concrete type).
        
        @return the module or group id
        """
        raise NotImplementedError
    
    def get_id(self):
        raise NotImplementedError

    def __hash__(self):
        assert(self.is_valid())
        return self.is_group() << 9 + reverse_uint8(self.get_id()) << 8 + reverse_uint8(self.get_seg_id())
    
    def __eq__(self, obj):
        if not isinstance(obj, self.__class__):
            return False
        return (self.is_group() == obj.is_group()) & (self.get_seg_id() == obj.get_seg_id()) & (self.get_id() == obj.get_id())



class LcnAddrMod(LcnAddr):
    """
    Represents an LCN module address.
    Can be used as a key in maps.
    """
    def __init__(self, seg_id=-1, mod_id=-1):
        """
        Constructs a module address with (logical) segment id and module id.
        
        @param seg_id the segment id
        @param mod_id the module id
        """
        super().__init__(seg_id = seg_id)
        self.mod_id = mod_id
    
    def get_mod_id(self):
        """
        Gets the module id.

        @return the module id
        """
        return self.mod_id
    
    def is_valid(self):
        """
        seg_id:
        0 = Local, 1..2 = Not allowed (but "seen in the wild")
        3 = Broadcast, 4 = Status messages, 5..127, 128 = Segment-bus disabled (valid value)
        mod_id:
        1 = LCN-PRO, 2 = LCN-GVS/LCN-W, 4 = PCHK, 5..254, 255 = Unprog. (valid, but irrelevant here)
        """
        return (self.seg_id >= 0) & (self.seg_id <= 128) & (self.mod_id >= 1) & (self.mod_id < 254)
    
    def is_group(self):
        return False
    
    def get_id(self):
        return self.mod_id
    
    

class LcnAddrGrp(LcnAddr):
    """
    Represents an LCN group address.
    Can be used as a key in maps.
    """
    def __init__(self, seg_id=-1, grp_id=-1):
        """
        Constructs a group address with (logical) segment id and group id.
        
        @param seg_id the segment id
        @param grp_id the module id
        """
        super().__init__(seg_id = seg_id)
        self.grp_id = grp_id
    
    def get_grp_id(self):
        """
        Gets the group id.

        @return the group id
        """
        return self.grp_id
    
    def is_valid(self):
        """
        seg_id:
        0 = Local, 1..2 = Not allowed (but "seen in the wild")
        3 = Broadcast, 4 = Status messages, 5..127, 128 = Segment-bus disabled (valid value)
        grp_id:
        3 = Broadcast, 4 = Status messages, 5..254
        """
        return (self.seg_id >= 0) & (self.seg_id <= 128) & (self.grp_id >= 3) & (self.grp_id < 254)
    
    def is_group(self):
        return True
    
    def get_id(self):
        return self.grp_id
    



# only execute, if not defined before
if not 'reversed_uint8' in dir():
    reversed_uint8 = [0]*256
    for i in range(256):
        reversed = 0
        for j in range(8):
            if ((i & (1 << j)) != 0):
                reversed |= (0x80 >> j)
        reversed_uint8[i] = reversed


def reverse_uint8(value):
    if (value < 0 | value > 255):
        raise ValueError('Invalid value.')
    return reversed_uint8[value]

