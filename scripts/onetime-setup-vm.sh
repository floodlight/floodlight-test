#!/bin/bash

set -x

console_ip="192.168.1.111"
tester1_ip="192.168.1.110"
tester2_ip="192.168.1.116"

# configure console VM with needed dependencies
ssh floodlight@$console_ip "sudo apt-get update"
ssh floodlight@$console_ip "sudo apt-get install python-pip"
ssh floodlight@$console_ip "sudo pip install virtualenv"
ssh floodlight@$console_ip "sudo apt-get install git" 
ssh floodlight@$console_ip "sudo apt-get install emacs"

# checkout floodlight-test suite from github 
ssh floodlight@$console_ip "git clone git://github.com/floodlight/floodlight-test.git"

#still debugging
VBoxManage controlvm fl-tester1-vm pause
VBoxManage snapshot fl-tester1-vm take init
VBoxManage controlvm fl-tester1-vm resume

VBoxManage controlvm fl-tester2-vm pause
VBoxManage snapshot fl-tester2-vm take init
VBoxManage controlvm fl-tester2-vm resume

set +x


