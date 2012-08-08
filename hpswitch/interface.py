# -*- coding: utf-8 -*-

from pysnmp.proto import rfc1902

class Interface(object):
    """
    Represents a physical interface on a switch.
    """
    def __init__(self, switch, identifier):
        """
        Construct a new Interface with the given `identifier` located on the given `switch`.
        """
        self.switch = switch
        self.identifier = identifier

    ifindex = property(lambda self: self.switch._get_ifindex_for_interface_identifier(self.identifier))

    def _get_name(self):
        """
        Get the friendly name configured for this interface.
        """

    def _set_name(self, value):
        """
        Configure the name `value` as the friendly name for this interface.
        """
        # Make sure that the name is legal according to the allowed interface names detailed in section 2-23 of the HP
        # Management and Configuration Guide
        assert(all(map(lambda letter: letter in (string.ascii_letters + string.digits), value)))
        # Issue the commands on the switch to set the new name.
        pass

    def _del_name(self):
        """
        Deconfigure the friendly name on this interface.
        """
        pass

    name = property(_get_name, _set_name, _del_name)

    def _get_enabled(self):
        """
        Get the admin status of this interface.
        """
        ifAdminStatus = self.switch.snmp_get(("ifAdminStatus", self.ifindex))
        return int(ifAdminStatus) == 1

    def _set_enabled(self, value):
        """
        Set the admin status of this interface.
        """
        self.switch.snmp_set(("ifAdminStatus", self.ifindex), rfc1902.Integer(1 if value else 2))

    enabled = property(_get_enabled, _set_enabled)

    def _get_operational(self):
        """
        Get the operational status of this interface.
        """
        ifOperStatus = self.switch.snmp_get(("ifOperStatus", self.ifindex))
        return int(ifOperStatus) == 1

    operational = property(_get_operational)

    def _get_untagged_vlan(self):
        """
        Get the untagged VLAN configured on this interface.
        None is returned in case no VLAN is configured as untagged on this interface.
        """
        pass

    untagged_vlan = property(_get_untagged_vlan)

    def _get_tagged_vlans(self):
        """
        Get a list of the tagged VLANs configured on this interface.
        """
        pass

    tagged_vlans = property(_get_tagged_vlans)
