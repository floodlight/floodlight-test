#!/bin/bash

# Before you start, make sure you have downloaded floodlight-vm.zip 
# from openflowhub.org, e.g., by doing:
# wget http://floodlight.openflowhub.org/files/floodlight-vm.zip      
#
# This script creates and registers three VMs based on the vmdk image from floodlight-vm.zip
#
# Start the script with floodlight-vm.zip in a directory you created for this testing purpose.
#
# Network setup: Below creates three VMs in VirtualBox's bridged networking mode.
# 1. If your host is on a local network with a DHCP server, the VMs will get addresses via DHCP.
# 2. Otherwise, you can assign VMs static addresses in the same subnet as your host.

# grab the current directory full path name.
d1=$(cd $(dirname $0); pwd)

# Keep this section - this grabs the unzipped floodlight-vm folder
# echo "Unzipping floodlight-vm.zip" 
# unzip -o floodlight-vm.zip > unzip.out
# d2=$(cat unzip.out | awk '/ inflating:/ {print $2}'| awk -F/ '{print $1}'|head -1)

# If you already have an unzipped vmdk, you can specify its directory name below
d2="floodlightcontroller-bench"

cd $d2

# USER: set the host interface you use to bridge your VM to your physical host: 
# e.g., on Mac OS X, en0 for Ethernet, en1 for Wi-Fi, on Linux eth0 for Ethernet, eth1 for Wi-Fi, etc.
activeif="en1"

# create and register first VM (for console) to VirtualBox

echo "Copying vmdk image for first VM: fl-benchconsole-vm.vmdk"
cp $d1/$d2/floodlightcontroller.vmdk $d1/$d2/fl-benchconsole-vm.vmdk

echo "Registering fl-benchconsole-vm"
echo "fl-benchconsole-vm: cleaning up old record"
VBoxManage unregistervm fl-benchconsole-vm --delete 2>/dev/null
rm -f $d1/$d2/fl-benchconsole-vm/fl-benchconsole-vm.vbox
echo "fl-benchconsole-vm: VM create"
VBoxManage createvm --name fl-benchconsole-vm --basefolder $d1/$d2 --register
echo "fl-benchconsole-vm: VM setup"
VBoxManage modifyvm fl-benchconsole-vm --ostype Ubuntu --rtcuseutc on --memory 2048 --vram 16 --hwvirtexexcl on --ioapic on --uart1 0x3f8 4 --uartmode1 disconnected --nic1 bridged --nictype1 virtio --bridgeadapter1 $activeif
#TODO:  add host only network adaptor
echo "fl-benchconsole-vm: VM storage"
VBoxManage storagectl fl-benchconsole-vm --name ide --add ide
ln -nf $d1/$d2/fl-benchconsole-vm.vmdk $d1/$d2/fl-benchconsole-vm/fl-benchconsole-vm.vmdk
VBoxManage storageattach fl-benchconsole-vm --storagectl ide --port 0 --device 0 --type hdd --medium $d1/$d2/fl-benchconsole-vm/fl-benchconsole-vm.vmdk 

# create and register second VM (for controller/mininet #1)

echo "Copying vmdk image for second VM: fl-benchtester1-vm.vmdk"
cp $d1/$d2/floodlightcontroller.vmdk $d1/$d2/fl-benchtester1-vm.vmdk
echo "Registering fl-benchtester1-vm" 
echo "fl-benchtester1-vm: cleaning up old record"
VBoxManage unregistervm fl-benchtester1-vm --delete 2>/dev/null
rm -f $d1/$d2/fl-benchtester1-vm/fl-benchtester1-vm.vbox
echo "fl-benchtester1-vm: VM create"
VBoxManage createvm --name fl-benchtester1-vm --basefolder $d1/$d2 --register
echo "fl-benchtester1-vm: VM setup"
VBoxManage modifyvm fl-benchtester1-vm --ostype Ubuntu --rtcuseutc on --memory 2048 --vram 16 --hwvirtexexcl on --ioapic on --uart1 0x3f8 4 --uartmode1 disconnected --nic1 bridged  --nictype1 virtio --bridgeadapter1 $activeif
echo "fl-benchtester1-vm: VM storage"
VBoxManage storagectl fl-benchtester1-vm --name ide --add ide
ln -nf $d1/$d2/fl-benchtester1-vm.vmdk $d1/$d2/fl-benchtester1-vm/fl-benchtester1-vm.vmdk
VBoxManage storageattach fl-benchtester1-vm --storagectl ide --port 0 --device 0 --type hdd --medium $d1/$d2/fl-benchtester1-vm/fl-benchtester1-vm.vmdk

# create and register third VM (for controller/mininet #2)
echo "Copying vmdk image for second VM: fl-benchtester2-vm.vmdk"
cp $d1/$d2/floodlightcontroller.vmdk $d1/$d2/fl-benchtester2-vm.vmdk

echo "Registering fl-benchtester2-vm" 
echo "fl-benchtester2-vm: cleaning up old record"
VBoxManage unregistervm fl-benchtester2-vm --delete 2>/dev/null
rm -f $d1/$d2/fl-benchtester2-vm/fl-benchtester2-vm.vbox
echo "fl-benchtester2-vm: VM create"
VBoxManage createvm --name fl-benchtester2-vm --basefolder $d1/$d2 --register
echo "fl-benchtester2-vm: VM setup"
VBoxManage modifyvm fl-benchtester2-vm --ostype Ubuntu --rtcuseutc on --memory 2048 --vram 16 --hwvirtexexcl on --ioapic on --uart1 0x3f8 4 --uartmode1 disconnected --nic1 bridged --nictype1 virtio --bridgeadapter1 $activeif
echo "fl-benchtester2-vm: VM storage"
VBoxManage storagectl fl-benchtester2-vm --name ide --add ide
ln -nf $d1/$d2/fl-benchtester2-vm.vmdk $d1/$d2/fl-benchtester2-vm/fl-benchtester2-vm.vmdk
VBoxManage storageattach fl-benchtester2-vm --storagectl ide --port 0 --device 0 --type hdd --medium $d1/$d2/fl-benchtester2-vm/fl-benchtester2-vm.vmdk

echo "Your VMs are now set up in VirtualBox and ready for use."
echo " "
echo "Now perform the following steps:"
echo "1. In VirtualBox UI, click open the \"Network\" section for each VM configuration"
echo "   (this allows VirtualBox to capture the network interface's correct state)" 
echo "2. In VirtualBox UI, manually power on and ssh into three VMs (username:floodlight/no password)"
echo "   do 'ifconfig' to make sure eth0 has a valid IP address, note it down."
echo "   do 'sudo ifconfig eth0 [IP_ADDRESS] if eth0 does not have an address."    
echo "3. Open ./onetime-setup-vm.sh and edit the IP addresses on top."
echo "   Run ./onetime-setup-vm.sh:"

