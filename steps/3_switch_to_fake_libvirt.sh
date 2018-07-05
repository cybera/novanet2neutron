set -e

source base.sh

echo ""
echo "This will change the role of the compute nodes to compute_fake"
echo ""
echo "Press any key to continue"
read

# Running puppet on all nova containers and compute nodes
dsh -Mg nova -F 5 "rm /etc/nova/nova.conf; puppet agent --enable; puppet agent -t" || true
dsh -Mg nova -F 5 "puppet agent -t" || true

dsh -Mg cnodes -F 5 "echo 'role=compute_fake' > /etc/facter/facts.d/role.txt"
dsh -Mg cnodes -F 5 "rm /etc/nova/nova.conf; rm /etc/nova/nova-compute.conf; puppet agent --enable; puppet agent -t" || true
dsh -Mg cnodes -F 5 "puppet agent -t" || true
dsh -Mg cnodes -F 5 "puppet agent -t" || true
dsh -Mg cnodes -F 5 "service puppet stop"
