#!/usr/bin/env python

import argparse
import ConfigParser
import MySQLdb
import sys
import time
from netaddr import *

from novanet2neutron import common

CONF = ConfigParser.ConfigParser()


def add_port(neutronc, instance, network_id, subnet_id,
             mac_address, ip_address, subnet_v6=None, ip_v6=None):
    if subnet_v6:
        body_value = {
            "port": {
                "tenant_id": instance.tenant_id,
                "mac_address": mac_address,
                "fixed_ips": [
                    {
                        "subnet_id": subnet_id,
                        "ip_address": ip_address,
                    },
                    {
                        "subnet_id": subnet_v6,
                    }],
                "network_id": network_id,
            }
        }
    else:
        body_value = {
            "port": {
                "tenant_id": instance.tenant_id,
                "mac_address": mac_address,
                "fixed_ips": [
                    {
                        "subnet_id": subnet_id,
                        "ip_address": ip_address,
                    }],
                "network_id": network_id,
            }
        }
    ports = neutronc.list_ports(mac_address=mac_address, network_id=network_id)
    if ports['ports']:
        port = ports['ports'][0]
        print "Not creating port for %s already exists" % mac_address
    else:
        try:
            print body_value
            port = neutronc.create_port(body=body_value)['port']
        except Exception, e:
            print e

    instance_ports = neutronc.list_ports(device_id=instance.id,
                                         network_id=network_id)
    if not instance_ports['ports']:
        try:
            print 'attach interface'
            instance.interface_attach(port['id'], "", "")
        except Exception, e:
            print e
    else:
        print "Not attaching, already attached %s" % instance.id


def add_ports(neutronc, cursor, mappings, instance, target_zone):
    #suspend = False
    #if instance.status == "SUSPENDED":
    #    instance.resume()
    #    time.sleep(2)
    #    suspend = True
    cursor.execute(
        "SELECT * from network_migration_info where uuid = '%s'" % instance.id)
    networks = cursor.fetchall()

    for network in networks:
        zone = network['availability_zone']
        if zone is None or zone == 'None':
            print "unknown zone for %s" % instance.id
            continue
        if zone != target_zone:
            continue

        network_name = network['network_name']
        ip_v4 = network['ip_v4']
        ip_v6 = network['ip_v6']
        mac_address = network['mac_address']
        #network_info = mappings['network_%s:%s' % (zone, network_name)]
        network_info = mappings[network_name]
        neutron_network = network_info['network_id']
        subnet_v4 = network_info['subnet_v4_id']

        #add_port(neutronc, instance, neutron_network,
        #         subnet_v4, mac_address, ip_v4)
        if 'subnet_v6_id' in network_info:
            subnet_v6 = network_info['subnet_v6_id']
            add_port(neutronc, instance, neutron_network,
                     subnet_v4, mac_address, ip_v4, subnet_v6, ip_v6)
        else:
            add_port(neutronc, instance, neutron_network,
                     subnet_v4, mac_address, ip_v4)

    #if suspend:
    #    instance.suspend()


def create_networks(neutronc, cursor):
    mappings = {}

    #Get Network list - have to use MySQL and not the Nova API
    #as nova needs to be switched to neutron for the add_ports
    #section to work. We also don't want to migrate non assigned
    #networks
    cursor.execute("SELECT * from networks WHERE project_id is not null order by id")
    networks = cursor.fetchall()

    # Set some defaults for things that are not defined in nova-network
    # This assumes all networks to migrate have the same zone, and ipv6_address_mode
    zone = 'default'
    ipv6_address_mode = 'slaac'
    for section in CONF.sections():
        # Recommended name for section: network_defaults
        if not section.startswith('network_'):
            continue
        mappings[section] = {}
        for option in CONF.options(section):
            mappings[section][option] = CONF.get(section, option)
        zone = CONF.get(section, 'zone')
        if 'cidr_v6' in CONF.options(section):
            ipv6_address_mode = CONF.get(section, 'ipv6_address_mode')

    # Iterate through networks and create if not already created
    for network_to_migrate in networks:
        name = network_to_migrate['label']
        vlan_id = network_to_migrate['vlan']
        project_id = network_to_migrate['project_id']

        # If project is unassigned - who do we assign it to?
        #if project_id == None:

        #physnet = network_to_migrate.bridge_interface
        #Always eth2 which is mapped to the name physnet
        physnet = 'physnet'

        mappings[name] = {}

        print name

        network = common.get_network(neutronc, name)
        if not network:
            network = common.create_network(neutronc, name, physnet, 'vlan', vlan_id, project_id)
        mappings[name]['network_id'] = network

        print network_to_migrate['cidr']

        gateway_v4 = network_to_migrate['gateway']
        dns_servers = []
        # If the DNS server is set to null - use Cloudflare
        if not network_to_migrate['dns1']:
            network_to_migrate['dns1'] = '1.1.1.1'
        dns_servers.append(network_to_migrate['dns1'])
        dhcp_start = network_to_migrate['dhcp_start']

        # nova-network doesn't have a dhcp_end by default instead it uses the cidr
        # Calculate last ip using the cidr
        ip = IPNetwork(network_to_migrate['cidr'])
        dhcp_end = ip[-2]

        subnet_v4 = common.get_subnet(neutronc, network, 4)
        if not subnet_v4:
            # Add subnetpool here as well
            subnet_v4 = common.create_subnet(
                neutronc, network, 4,
                cidr=network_to_migrate['cidr'],
                dns_servers=dns_servers,
                gateway=gateway_v4,
                dhcp_start=dhcp_start,
                dhcp_end=dhcp_end,
                project=project_id,
                name="private_v4")

        mappings[name]['subnet_v4_id'] = subnet_v4

        if network_to_migrate['cidr_v6'] != None:
            subnet_v6 = common.get_subnet(neutronc, network, 6)
            if not subnet_v6:
                gateway_v6 = network_to_migrate['gateway_v6']
                subnet_v6 = common.create_subnet(
                    neutronc, network, 6,
                    network_to_migrate['cidr_v6'],
                    dns_servers=None,
                    gateway=gateway_v6,
                    ipv6_address_mode=ipv6_address_mode,
                    project=project_id,
                    name="private_v6")
            mappings[name]['subnet_v6_id'] = subnet_v6

    return mappings


def check_hypervisors(novac):
    print "Checking all hypervisors are running fake driver"
    for h in novac.hypervisors.list():
        if h.hypervisor_type != 'fake':
            print 'Hypervisor %s is not fake' % h.hypervisor_hostname
            print 'Hypervisor %s is %s' % (h.hypervisor_hostname, h.hypervisor_type)
            sys.exit(1)


def collect_args():
    parser = argparse.ArgumentParser(description='novanet2neutron.')

    parser.add_argument('-c', '--config', action='store',
                        default='novanet2neutron.conf', help="Config file")
    parser.add_argument('-z', '--zone', action='store',
                        help="AZ to migrate")
    return parser.parse_args()


def main():
    args = collect_args()
    common.load_config(CONF, args.config)
    target_zone = args.zone
    conn = MySQLdb.connect(
        host=CONF.get('db', 'host'),
        user=CONF.get('db', 'user'),
        passwd=CONF.get('db', 'password'),
        db=CONF.get('db', 'name'))

    cursor = MySQLdb.cursors.DictCursor(conn)
    novac = common.get_nova_client()
    check_hypervisors(novac)
    neutronc = common.get_neutron_client()
    print "creating networks"
    mappings = create_networks(neutronc, cursor)
    print "getting instances"
    instances = common.all_servers(novac)
    print "adding ports"

    for i in instances:
        add_ports(neutronc, cursor, mappings, i, target_zone)
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
