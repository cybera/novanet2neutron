set -e

source base.sh

#echo "Create the external network"
source /root/openrc && /root/novanet2neutron/steps/create-floatingip-network.sh

