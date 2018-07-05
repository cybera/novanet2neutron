set -e

source base.sh

# Run puppet
dsh -Mg nova -F 5 "rm /etc/nova/nova.conf; puppet agent -t" || true
dsh -Mg nova -F 5 "puppet agent -t" || true

dsh -Mg cnodes -F 5 "iptables -F" || true
dsh -Mg cnodes -F 5 "echo 'role=compute_neutron' > /etc/facter/facts.d/role.txt"
dsh -Mg cnodes -F 5 "rm /etc/nova/nova.conf; rm /etc/nova/nova-compute.conf; puppet agent -t" || true
dsh -Mg cnodes -F 5 "puppet agent -t" || true
dsh -Mg cnodes -F 5 "puppet agent -t" || true
