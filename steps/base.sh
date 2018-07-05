set -e

REGION="abc123"
MYSQL_HOST="MYSQL_HOST_${REGION}"
NOVA_HOST="NOVA_HOST_${REGION}"
ALL_NOVA_HOSTS=$(ssh ${NOVA_HOST} "source openrc && nova service-list" | grep nova-conductor | awk '{print $6}' | grep ${REGION} | sort | uniq)
ALL_COMPUTE_NODES=$(ssh ${NOVA_HOST} "source /root/openrc && nova hypervisor-list" | awk '{print $4}' | grep -v Hy | grep -v ^\$)
