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

# REMOVE - setup private git credential
scp ~/.ssh/id_rsa floodlight@$console_ip:.ssh/
ssh floodlight@$console_ip "git config --global git.user kwanggithub"

# checkout floodlighttest suite from github 
# TODO: setup GIT_SSH to pass "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
#       before this will work
ssh floodlight@$console_ip "git clone git@github.com:kwanggithub/floodlighttest.git"

#still debugging
VBoxManage controlvm fl-tester1-vm pause
VBoxManage snapshot fl-tester1-vm take init
VBoxManage controlvm fl-tester1-vm resume

VBoxManage controlvm fl-tester2-vm pause
VBoxManage snapshot fl-tester2-vm take init
VBoxManage controlvm fl-tester2-vm resume

set +x


