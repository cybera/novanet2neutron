set -e

source base.sh

# Generate network migration table
source /root/openrc && /root/novanet2neutron/generate-network-data.py -c /root/novanet2neutron/novanet2neutron.conf

