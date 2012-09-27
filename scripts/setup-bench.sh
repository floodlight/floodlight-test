#!/bin/bash

# TODO: Automate set/get eth0 IP addresses of VMs
# In case problem with DHCP, assign static addresses from host's IP subnet
#
# Before running this script, make sure you have:
# 1. run onetime-create-vm.sh
# 2. set up the network as instructed when onetime-create-vm completes.
# 3. run onetime-setup-vm.sh

# USER: full directory path to your floodlight project root directory
djar="/Users/kwang/work/repo/myfloodlight"

# When bridged network available
console_ip="192.168.1.75"
tester1_ip="192.168.1.76"
tester2_ip="192.168.1.77"

# When bridged network unavailable (e.g., host not connected to any network)
# use VirtualBox host only network (vboxnet0)
#console_ip="192.168.56.101"
#tester1_ip="192.168.56.102"
#tester2_ip="192.168.56.103"


# create jar file for floodlight
echo "Creating floodlight.jar from $djar"
cd $djar; ant

# restore tester VMs to initial snapshot - this step is critical between check-tests-floodlight 
# runs to avoid stale VM states causing test failures
VBoxManage controlvm fl-benchtester1-vm poweroff
VBoxManage controlvm fl-benchtester2-vm poweroff

# need sleep to allow time for poweroff before restore
sleep 5

VBoxManage snapshot fl-benchtester1-vm restore init
VBoxManage startvm fl-benchtester1-vm

VBoxManage snapshot fl-benchtester2-vm restore init
VBoxManage startvm fl-benchtester2-vm

# need sleep to allow time for start complete before copy      
sleep 10

# stop default floodlight on VM and copy your jar to tester1 and tester2
echo "Copying floodlight.jar to fl-benchtester1-vm and fl-benchtester2-vm"
ssh -f floodlight@$tester1_ip "sudo service floodlight stop"
ssh -f floodlight@$tester2_ip "sudo service floodlight stop"

scp -q $djar/target/floodlight.jar floodlight@$tester1_ip:/opt/floodlight/floodlight
scp -q $djar/target/floodlight.jar floodlight@$tester2_ip:/opt/floodlight/floodlight

# Re-launch floodlight as service (with config options at each VM's /etc/init)
ssh -f floodlight@$tester1_ip "sudo service floodlight start"
ssh -f floodlight@$tester2_ip "sudo service floodlight start"
echo "+++ bench setup complete. floodlight running on tester VMs"

# Re-launch floodlight at command line
#ssh -f floodlight@$tester1_ip "java -jar /opt/floodlight/floodlight/floodlight.jar > /dev/null &"
#ssh -f floodlight@$tester2_ip "java -jar /opt/floodlight/floodlight/floodlight.jar > /dev/null &" 


