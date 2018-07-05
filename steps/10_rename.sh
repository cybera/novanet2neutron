set -e

source base.sh

# Rename all of the nova_* networks to "private"
for i in $(neutron net-list | awk '/nova/ { print $2 }'); do
  neutron net-update ${i} --name private
done
