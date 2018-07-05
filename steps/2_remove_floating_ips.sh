set -e

source base.sh

# Remove all floating IPs
echo "Removing floating IPs"
old_fips=$(source /root/openrc && nova floating-ip-bulk-list | awk -F\| '{print $3,$4}' | grep -v addr | grep [a-f])
echo "$old_fips" | while read -r ip uuid; do
  echo "disassociating $ip from $uuid"
  source /root/openrc && nova floating-ip-disassociate $uuid $ip
done
