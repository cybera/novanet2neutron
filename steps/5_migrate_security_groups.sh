set -e

source base.sh

# Migrate the security groups
source /root/openrc && /root/novanet2neutron/migrate-secgroups.py -c /root/novanet2neutron/novanet2neutron.conf
