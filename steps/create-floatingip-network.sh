neutron net-create public --router:external True --provider:physical_network public --provider:network_type flat
#HNL
neutron subnet-create --name public_subnet --allocation-pool start=192.168.250.105,end=192.168.250.130 --disable-dhcp --gateway 192.168.250.9 public 192.168.250.0/24

neutron router-create shared_router
neutron router-gateway-set shared_router public

# Attach all the private_v4 networks to the shared router
for i in $(neutron subnet-list | awk '/private_v4/ { print $2 }'); do
  echo "Attaching subnet $i to router";
  neutron router-interface-add dair_router ${i}
done
