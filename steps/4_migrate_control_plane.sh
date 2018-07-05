set -e

source base.sh

# Migrate the control plane
# Create subnetpool first
source /root/openrc && neutron subnetpool-create --pool-prefix 10.0.0.0/16 --default-prefixlen 24 --shared --is-default True subnetpool
source /root/openrc && /root/novanet2neutron/migrate-control.py -z nova -c /root/novanet2neutron/novanet2neutron.conf

ssh ${MYSQL_HOST} "mysql -e \"select * from ml2_port_bindings where host not like '%neutron%'\" neutron"
echo "Does the above look correct? If not, ctrl-c now, delete all ports, fix the problem, and retry"
read

