#!/usr/bin/env python

import os

from neutronclient.v2_0 import client as neutron_client
from novaclient import client as nova_client


def load_config(conf, filename):
    conf.read(filename)


def get_nova_client(url=None, username=None, password=None, tenant=None, region=None):
    url = os.environ.get('OS_AUTH_URL', url)
    username = os.environ.get('OS_USERNAME', username)
    password = os.environ.get('OS_PASSWORD', password)
    tenant = os.environ.get('OS_TENANT_NAME', tenant)
    region = os.environ.get('OS_REGION_NAME', region)
    assert url and username and password and tenant and region
    return nova_client.Client('2',
                              username=username, api_key=password,
                              project_id=tenant, auth_url=url,
                              region_name=region)

def get_neutron_client(url=None, username=None, password=None, tenant=None, region=None):
    url = os.environ.get('OS_AUTH_URL', url)
    username = os.environ.get('OS_USERNAME', username)
    password = os.environ.get('OS_PASSWORD', password)
    tenant = os.environ.get('OS_TENANT_NAME', tenant)
    region = os.environ.get('OS_REGION_NAME', region)
    assert url and username and password and tenant and region
    nc = neutron_client.Client(username=username, password=password,
                               tenant_name=tenant, auth_url=url,
                               region_name=region)
    nc.httpclient.authenticate_and_fetch_endpoint_url()
    return nc


def all_servers(client, host=None):
    servers = []
    marker = None

    while True:
        opts = {"all_tenants": True}
        if marker:
            opts["marker"] = marker
        if host:
            opts["host"] = host
        res = client.servers.list(search_opts=opts)
        if not res:
            break
        servers.extend(res)
        marker = servers[-1].id
    return servers

def all_networks(novac):
    networks = []
    marker = None

    networks = novac.networks.list()

    return networks

def create_network(neutronc, network_name, physname='public', net_type='flat', vlan_id='0', project=None):
    body_sample = {}
    if project == None:
        body_sample = {'network': {'name': network_name,
                               'admin_state_up': True,
                               'provider:network_type': net_type,
                               'provider:physical_network': physname,
                               'provider:segmentation_id': vlan_id,
                               'router:external': False,
                               'shared': False}}
    else:
        body_sample = {'network': {'name': network_name,
                               'admin_state_up': True,
                               'provider:network_type': net_type,
                               'provider:physical_network': physname,
                               'provider:segmentation_id': vlan_id,
                               'tenant_id': project,
                               'router:external': False,
                               'shared': False}}

    network = neutronc.create_network(body=body_sample)
    net_dict = network['network']
    network_id = net_dict['id']
    print('Network %s created' % network_id)
    return network_id


def create_subnet(neutronc, network_id, protocol, cidr, dns_servers=None,
                  gateway=None, dhcp_start=None, dhcp_end=None, project=None,
                  ipv6_address_mode=None, name=None):

    body_create_subnet = {'subnets': [{'cidr': cidr,
                                       'ip_version': protocol,
                                       'network_id': network_id }]}
    if dhcp_start and dhcp_end:
        body_create_subnet['subnets'][0]['allocation_pools'] = [
            {'start': dhcp_start, 'end': dhcp_end}]

    if dns_servers:
        body_create_subnet['subnets'][0]['dns_nameservers'] = dns_servers
    if gateway:
        body_create_subnet['subnets'][0]['gateway_ip'] = gateway
    if ipv6_address_mode:
        body_create_subnet['subnets'][0]['ipv6_address_mode'] = ipv6_address_mode
    if name:
        body_create_subnet['subnets'][0]['name'] = name
    if project:
        body_create_subnet['subnets'][0]['tenant_id'] = project
    subnet = neutronc.create_subnet(body=body_create_subnet)

    sn_dict = subnet['subnets'][0]
    print('Created subnet %s' % sn_dict['id'])
    return sn_dict['id']


def get_network(neutronc, name):
    networks = neutronc.list_networks(name=name)['networks']
    if len(networks) == 1:
        return networks[0]['id']
    return None


def get_subnet(neutronc, network_id, protocol):
    subnets = neutronc.list_subnets(network_id=network_id,
                                    ip_version=protocol)['subnets']
    if len(subnets) == 1:
        return subnets[0]['id']
    return None


def get_db_data(cursor, instance, network_name):
    sql = """SELECT * from network_migration_info where uuid = '%(uuid)s'
    AND network_name = '%(network_name)s'
    """
    cursor.execute(sql % {'uuid': instance.id,
                          'network_name': network_name})
    rows = cursor.fetchall()
    if len(rows) > 1:
        print "ERROR"
    if len(rows) == 0:
        return None
    return rows[0]


def get_mac_db(cursor, instance, network_name):
    return get_db_data(cursor, instance, network_name)['mac_address']
