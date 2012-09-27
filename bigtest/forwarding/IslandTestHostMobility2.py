#!/usr/bin/env python
## Creates 3 islands: Island1: s1, s2; Island2: s3; Island3: s4
## s1-s4 are connected to controller 1 (node1) and s100 is connected to controller 2 (node 2)
## Test algo rithm is as follows:
## 1. Have two groups of hosts: static_hosts and dynamic_hosts. Ststic hosts don't move. 
## dynamic hosts can move from one switch/island to another. Each switch, and hence each
## island has one static host ialways attached.
## 2. After host x is moved to a different port and/or switch, ping from the moved host to\
## all the static hosts so that each island learns aboout the moved host's new location
## Then ping between all pairs of hosts in the dynamic_hosts set. If any ping fails at
## this statge then we wait for 7s, to let the existing flows expire, and the do ping tests
## between all pairs of dynamic hosts.

from time import sleep
import bigtest.controller
import re
import os
import sys

print "************ CWD= %s" % os.getcwd()
local_path  = "bigtest/forwarding"
topo_file   = "IslandTestHostMobility2Topo.py"
output_file = "IslandTestHostMobility2output.txt"

def CopyTopoToNode(cNode, topo):
    cli = cNode.cli()
    cli.gotoBashMode()
    console = cli.console()
    console.sendline('cat > %s << EOF' % topo_file)
    for line in topo.split("\n"):
        console.sendline(line)
    console.sendline("EOF")
    cli.expectPrompt()
    cli.runCmd("chmod 755 %s" % topo_file)

if (not os.path.isfile(os.path.join(local_path, topo_file))):
    print "Error: File %s is not found" % (os.path.join(local_path, topo_file))
    print "Please run from workspace directory"
    sys.exit(1)

env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controller1 = env.node1()
cli1 = controller1.cli()
controller2 = env.node2()
cli2 = controller2.cli()

topo = file(os.path.join(local_path, topo_file)).read()
topo = topo.replace("CONTROLLER1_IP", controller1.ipAddress())
topo = topo.replace("CONTROLLER2_IP", controller2.ipAddress())

CopyTopoToNode(controller1, topo)
cli1.gotoBashMode()
cli1.runCmd("script %s" % output_file)
cli1.runCmd("python")
print "\n*** The following command may take up to a few minutes\n"
cli1.runCmd("execfile('%s')" % topo_file)
cli1.runCmd("quit()")
# exit the script session
cli1.runCmd("exit")
print "*** Show outputs from Controller 1 -----------------"
cli1.runCmd("show host all attachment-point")
cli1.runCmd("show switch")
cli1.runCmd("show host")
cli1.runCmd("show link")
print "*** End of IslandTestHostMobility2"
env.endTest()
