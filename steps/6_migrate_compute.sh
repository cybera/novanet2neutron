set -e

if [[ -z $1 ]]; then
  echo "must specify compute node"
  exit 1
fi

source base.sh

scp -r ~/novanet2neutron $1:.

ssh $1 "apt-get install -y python-mysqldb"

# Run migrate-compute.py in noop
ssh $1 "/root/novanet2neutron/migrate-compute.py -c /root/novanet2neutron/compute.conf -d neutron"

echo ""
echo "Does the above look OK? If not ctrl-c now"
echo "Otherwise, press any key to continue"
read

# Run migrate-compute.py for realsies
ssh $1 "/root/novanet2neutron/migrate-compute.py -c /root/novanet2neutron/compute.conf -d neutron -f"

echo ""
echo "Did the above succeed?"
read

# Flush all iptables rules and kill dnsmasq
ssh $1 "/root/novanet2neutron/flush-iptables.sh"
ssh $1 "service neutron-linuxbridge-agent restart"
