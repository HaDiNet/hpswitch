# -*- coding: utf-8 -*-
import struct

from pysnmp.proto import rfc1902

import ipaddress

from port import Port

class VLAN(object):
    """
    Represents a 802.1Q VLAN.
    """
    def __init__(self, switch, vid):
        """
        Constructs a new VLAN with the given VLAN ID `vid` on the given `switch`.
        """
        self.vid = vid
        self.switch = switch

        # Make sure that the VLAN is known on the switch
        if not bool(self.switch.snmp_get(("dot1qVlanStaticRowStatus", self.vid))):
            # create the VLAN on the switch: createAndGo == 4
            self.switch.snmp_set((("dot1qVlanStaticRowStatus", self.vid), rfc1902.Integer(4)))

    def _get_ifindex(self):
        # TODO: is this correct?
        return self.vid + 577

    ifindex = property(_get_ifindex)

    def __eq__(self, other):
        return self.vid == other.vid and self.switch == other.switch

    def __ne__(self, other):
        return not self.__eq__(other)

    def _get_name(self):
        """
        The name configured for the VLAN.
        """
        return unicode(self.switch.snmp_get(("dot1qVlanStaticName", self.vid)))

    def _set_name(self, value):
        # Make sure that the name is legal according to the allowed VLAN names detailed in section 1-40 of the HP
        # Advanced Traffic Management Guide
        assert(all(map(lambda illegal_char: illegal_char not in value, "\"\'@#$^&*")))
        self.switch.snmp_set((("dot1qVlanStaticName", self.vid), rfc1902.OctetString(value)))

    name = property(_get_name, _set_name)

    def _get_ipv4_addresses(self):
        """
        Get the IPv4 addresses configured configured for this VLAN.
        """
        # Get all address Entries in hpicfIpAddressTable
        vlan_ipv4_address_prefix_length_entries = self.switch.snmp_get_subtree(("hpicfIpAddressPrefixLength", self.ifindex, 1))

        ipv4_addresses = []
        for result in vlan_ipv4_address_prefix_length_entries:
            # Build an IPv4 address from the last 4 components of the oid
            ipv4_address_string = reduce(lambda a, b: a + "." + b, map(unicode, tuple(result[0][-4:])))
            ipv4_prefix_length_string = unicode(result[1])
            ipv4_addresses.append(ipaddress.IPv4Interface(ipv4_address_string + "/" + ipv4_prefix_length_string))
        return ipv4_addresses

    ipv4_addresses = property(_get_ipv4_addresses)

    def add_ipv4_address(self, address):
        """
        Add the given IPv4 address to the VLAN.

        `address` should be of type ipaddress.IPv4Interface.
        """
        ipv4_address_tuple = struct.unpack("4B", address.ip.packed)
        self.switch.snmp_set(
                (("ipv4InterfaceEnableStatus", self.ifindex), rfc1902.Integer(1)),
                # hpicfIpv4InterfaceDhcpEnable off
                (("hpicfIpv4InterfaceDhcpEnable", self.ifindex), rfc1902.Integer(2)),
                (("hpicfIpAddressPrefixLength", self.ifindex, 1, 4) + ipv4_address_tuple,
                    rfc1902.Gauge32(address.prefixlen)),
                # hpicfIpAddressType unicast
                (("hpicfIpAddressType", self.ifindex, 1, 4) + ipv4_address_tuple, rfc1902.Integer(1)),
                # hpicfIpAddressRowStatus createAndGo 4
                (("hpicfIpAddressRowStatus", self.ifindex, 1, 4) + ipv4_address_tuple, rfc1902.Integer(4))
                )

    def remove_ipv4_address(self, address):
        """
        Remove the given IPv4 address from the VLAN.

        `address` should be of type ipaddress.IPv4Interface.
        """
        ipv4_address_tuple = struct.unpack("4B", address.ip.packed)
        self.switch.snmp_set(
                # hpicfIpAddressRowStatus destroy 6
                (("hpicfIpAddressRowStatus", self.ifindex, 1, 4) + ipv4_address_tuple, rfc1902.Integer(6))
                )

    def _get_ipv6_addresses(self):
        """
        Get the IPv6 addresses configured for this VLAN.
        """
        # Get all address Entries in hpicfIpAddressTable
        vlan_ipv6_address_prefix_length_entries = self.switch.snmp_get_subtree(("hpicfIpAddressPrefixLength", self.ifindex, 2))

        ipv6_addresses = []
        for result in vlan_ipv6_address_prefix_length_entries:
            # Build an IPv6 address from the last 16 components of the oid
            ipv6_address_string_without_colons = reduce(
                    lambda a, b: a + b, 
                    map(lambda x: unicode("%02x" % x), tuple(result[0][-16:]))
                    )
            ipv6_address_string = ""
            while True:
                ipv6_address_string += ipv6_address_string_without_colons[:4]
                ipv6_address_string_without_colons = ipv6_address_string_without_colons[4:]
                if len(ipv6_address_string_without_colons) != 0:
                    ipv6_address_string += ":"
                else:
                    break

            ipv6_prefix_length_string = unicode(result[1])
            ipv6_addresses.append(ipaddress.IPv6Interface(ipv6_address_string + "/" + ipv6_prefix_length_string))
        return ipv6_addresses

    ipv6_addresses = property(_get_ipv6_addresses)

    def add_ipv6_address(self, address):
        """
        Add the given IPv6 address to the VLAN.

        `address` should be of type ipaddress.IPv6Interface.
        """
        # TODO: Convert a HP-ICF-IPCONFIG with this OID to pysnmp format
        hpicfIpv6InterfaceCfgEnableStatus = (1, 3, 6, 1, 4, 1, 11, 2, 14, 11, 1, 10, 3, 2, 1, 1, 6)
        hpicfIpv6InterfaceManual = (1, 3, 6, 1, 4, 1, 11, 2, 14, 11, 1, 10, 3, 2, 1, 1, 2)

        ipv6_address_tuple = struct.unpack("16B", address.ip.packed)
        self.switch.snmp_set(
                # Set enabled and configure a link-local address
                (hpicfIpv6InterfaceCfgEnableStatus + (self.ifindex, ), rfc1902.Integer(1)),
                # Enable manual address configuration
                (hpicfIpv6InterfaceManual + (self.ifindex, ), rfc1902.Integer(1)),
                (("ipv6InterfaceEnableStatus", self.ifindex), rfc1902.Integer(1)),
                (("hpicfIpAddressPrefixLength", self.ifindex, 2, 16) + ipv6_address_tuple,
                    rfc1902.Gauge32(address.prefixlen)),
                # hpicfIpAddressType unicast
                (("hpicfIpAddressType", self.ifindex, 2, 16) + ipv6_address_tuple, rfc1902.Integer(1)),
                # hpicfIpAddressRowStatus createAndGo 4
                (("hpicfIpAddressRowStatus", self.ifindex, 2, 16) + ipv6_address_tuple, rfc1902.Integer(4))
                )

    def remove_ipv6_address(self, address):
        """
        Remove the given IPv6 address from the VLAN.

        `address` should be of type ipaddress.IPv6Interface.
        """
        ipv6_address_tuple = struct.unpack("16B", address.ip.packed)
        self.switch.snmp_set(
                # hpicfIpAddressRowStatus destroy 6
                (("hpicfIpAddressRowStatus", self.ifindex, 2, 16) + ipv6_address_tuple, rfc1902.Integer(6))
                )

    @staticmethod
    def _set_port_list_port_status(port_list, port, status):
        """
        Return a new port list that is identical to the given `port_list` except that the bit corresponding to `port` is
        set to the binary value of `status`.
        """
        # Calculate the byte in `port_list` that needs to be modified as well as the bit within that byte.
        byte_position = (port.base_port - 1) / 8
        bit_position = 7 - ((port.base_port - 1) % 8)

        if status:
            newbyte = chr(ord(port_list[byte_position]) | (1 << bit_position))
        else:
            newbyte = chr(ord(port_list[byte_position]) & (~(1 << bit_position)))

        new_port_list = port_list[:byte_position] + newbyte + port_list[(byte_position + 1):]
        return new_port_list

    def _get_port_list_enabled_ports(self, port_list):
        """
        Return a list of Ports corresponding to the ports marked as enabled in the given `port_list`.
        """
        from port import get_port_list_enabled_ports
        return get_port_list_enabled_ports(self.switch, port_list)

    def _get_tagged_ports(self):
        """
        Get a list of ports that have this VLAN configured as tagged.
        """
        dot1qVlanStaticEgressPorts = self.switch.snmp_get(("dot1qVlanStaticEgressPorts", self.vid))
        egress_ports = self._get_port_list_enabled_ports(dot1qVlanStaticEgressPorts)
        # Filter out all untagged ports
        untagged_ports = self.untagged_ports
        tagged_ports = filter(lambda port: port not in untagged_ports, egress_ports)
        return tagged_ports

    tagged_ports = property(_get_tagged_ports)

    def _set_port_tagged_status(self, port, status):
        dot1qVlanStaticEgressPorts = self.switch.snmp_get(("dot1qVlanStaticEgressPorts", self.vid))
        new_port_list = VLAN._set_port_list_port_status(dot1qVlanStaticEgressPorts, port, status)
        if dot1qVlanStaticEgressPorts != new_port_list:
            self.switch.snmp_set((("dot1qVlanStaticEgressPorts", self.vid), rfc1902.OctetString(new_port_list)))

    def add_tagged_port(self, port):
        """
        Configure this VLAN as tagged on the Port `port`.
        """
        self._set_port_tagged_status(port, True)

    def remove_tagged_port(self, port):
        """
        Remove this VLAN as tagged from the Port `port`.
        """
        self._set_port_tagged_status(port, False)

    def _get_untagged_ports(self):
        """
        Get a list of ports that have this VLAN configured as untagged.
        """
        dot1qVlanStaticUntaggedPorts = self.switch.snmp_get(("dot1qVlanStaticUntaggedPorts", self.vid))
        return self._get_port_list_enabled_ports(dot1qVlanStaticUntaggedPorts)

    untagged_ports = property(_get_untagged_ports)

    def _set_port_untagged_status(self, port, status):
        previous_untagged_vlan = port.untagged_vlan
        if status == True:
            # To add a port to a VLAN untagged, it first needs to be added as tagged
            self.add_tagged_port(port)
        # Add the port to the list of untagged ports for this VLAN
        dot1qVlanStaticUntaggedPorts = self.switch.snmp_get(("dot1qVlanStaticUntaggedPorts", self.vid))
        new_untagged_port_list = VLAN._set_port_list_port_status(dot1qVlanStaticUntaggedPorts, port, status)
        if dot1qVlanStaticUntaggedPorts != new_untagged_port_list:
            self.switch.snmp_set((("dot1qVlanStaticUntaggedPorts", self.vid), rfc1902.OctetString(new_untagged_port_list)))
        # Only set the pvid if the port is being added to the VLAN
        if status == True:
            dot1qPvid = self.switch.snmp_get(("dot1qPvid", port.base_port))
            if dot1qPvid != self.vid:
                self.switch.snmp_set((("dot1qPvid", port.base_port), rfc1902.Gauge32(self.vid)))
            # Remove the port from the VLAN that it belonged to before
            if previous_untagged_vlan is not None and self != previous_untagged_vlan:
                previous_untagged_vlan.remove_untagged_port(port)
        # If the port was just removed from dot1qVlanStaticUntaggedPorts, it is still in dot1qVlanStaticEgressPorts and
        # therefore still egresses this VLAN tagged
        if status == False:
            self.remove_tagged_port(port)


    def add_untagged_port(self, port):
        """
        Configure this VLAN as untagged on the Port `port`.
        """
        self._set_port_untagged_status(port, True)

    def remove_untagged_port(self, port):
        """
        Remove this VLAN as untagged from the Port `port`.
        """
        self._set_port_untagged_status(port, False)

    def enable_igmp(self):
        """
        Enable IGMP
        """
        #.1.3.6.1.4.1.11.2.14.11.5.1.7.1.15.1.1.2.401 = INTEGER: enable(1)
        #.1.3.6.1.4.1.11.2.14.11.5.1.7.1.15.1.1.2.402 = INTEGER: disable(2)

        # TODO: Convert hpSwitchConfig.mib to pysnmp format
        hpSwitchIgmpState = (1, 3, 6, 1, 4, 1, 11, 2, 14, 11, 5, 1, 7, 1, 15, 1, 1, 2)

        self.switch.snmp_set((hpSwitchIgmpState + (self.vid, ), rfc1902.Integer(1)))

    def disable_igmp(self):
        """
        Disable IGMP
        """

        # TODO: Convert hpSwitchConfig.mib to pysnmp format
        hpSwitchIgmpState = (1, 3, 6, 1, 4, 1, 11, 2, 14, 11, 5, 1, 7, 1, 15, 1, 1, 2)

        self.switch.snmp_set((hpSwitchIgmpState + (self.vid, ), rfc1902.Integer(2)))

    def get_igmp_status(self):
        """
        Get status of igmp for this vlan.
        """

        # TODO: Convert hpSwitchConfig.mib to pysnmp format
        hpSwitchIgmpState = (1, 3, 6, 1, 4, 1, 11, 2, 14, 11, 5, 1, 7, 1, 15, 1, 1, 2)

        igmp_status = self.switch.snmp_get(hpSwitchIgmpState + (self.vid, ))
        # 1 enabled, 2 disabled
        return int(igmp_status) == 1

    def enable_pim_sparse_mode(self):
        """
        Enable PIM sparse-mode
        """

        #TODO: rfc2934.mib should contain the needed oids, convert it to pysnmp format

        #SNMPv2-SMI::experimental.61.1.1.2.1.7.978 = INTEGER: 4
        #.1.3.6.1.3.61.1.1.2.1.7.978 = INTEGER: 4
        #Syntax  INTEGER {active(1),notInService(2),notReady(3),createAndGo(4),createAndWait(5),destroy(6)}
        pimInterfaceStatus = (1, 3, 6, 1, 3, 61, 1, 1, 2, 1, 7)

        #SNMPv2-SMI::experimental.61.1.1.2.1.4.978 = INTEGER: 2
        #.1.3.6.1.3.61.1.1.2.1.4.978 = INTEGER: 2
        #Syntax  INTEGER {dense(1), sparse(2), sparseDense(3) }
        pimInterfaceMode = (1, 3, 6, 1, 3, 61, 1, 1, 2, 1, 4)

        pim_sparse_mode_enabled = self.get_pim_sparse_mode_status()

        if not pim_sparse_mode_enabled:
            self.switch.snmp_set(
                (pimInterfaceStatus + (self.ifindex, ), rfc1902.Integer(4)),
                (pimInterfaceMode + (self.ifindex, ), rfc1902.Integer(2))
                )

    def disable_pim_sparse_mode(self):
        """
        Disable PIM sparse-mode
        """

        #TODO: rfc2934.mib should contain the needed oids, convert it to pysnmp format

        #SNMPv2-SMI::experimental.61.1.1.2.1.7.978 = INTEGER: 6
        #.1.3.6.1.3.61.1.1.2.1.7.978 = INTEGER: 6
        #Syntax  INTEGER {active(1),notInService(2),notReady(3),createAndGo(4),createAndWait(5),destroy(6)}
        pimInterfaceStatus = (1, 3, 6, 1, 3, 61, 1, 1, 2, 1, 7)

        pim_sparse_mode_enabled = self.get_pim_sparse_mode_status()

        if pim_sparse_mode_enabled:
          self.switch.snmp_set(
                (pimInterfaceStatus + (self.ifindex, ), rfc1902.Integer(6)),
                )

    def get_pim_sparse_mode_status(self):
        """
        Get status of pim sparse mode for this vlan.
        """

        #SNMPv2-SMI::experimental.61.1.1.2.1.7.978 = INTEGER: 6
        #.1.3.6.1.3.61.1.1.2.1.7.978 = INTEGER: 6
        #Syntax  INTEGER {active(1),notInService(2),notReady(3),createAndGo(4),createAndWait(5),destroy(6)}
        pimInterfaceStatus = (1, 3, 6, 1, 3, 61, 1, 1, 2, 1, 7)

        pim_sparse_mode_status = self.switch.snmp_get(pimInterfaceStatus + (self.ifindex, ))
        #status is 1 if enabled, noSuchInstance if disabled

        from pysnmp.smi.exval import noSuchInstance
        if pim_sparse_mode_status is noSuchInstance:
            return False
        else:
            return True
