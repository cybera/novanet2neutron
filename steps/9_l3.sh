set -e

source base.sh

echo "Re-associating floating IPs"
new_fips=$(ssh ${MYSQL_HOST} "mysql -NBe \"select uuid, tenant_id, floating_ip from network_migration_info where floating_ip != 'None'\" nova")
echo "$new_fips" | while read -r uuid tenant_id fip; do
  x=$(ssh -n ${MYSQL_HOST} "mysql -NBe \"select floating_ip_address from floatingips where floating_ip_address = '$fip'\" neutron")
  if [[ -n $x ]]; then
    continue
  fi

  echo "Associating $fip to $uuid"
  source /root/openrc && neutron floatingip-create --tenant-id $tenant_id --floating-ip-address $fip public
  source /root/openrc && nova floating-ip-associate $uuid $fip
done
