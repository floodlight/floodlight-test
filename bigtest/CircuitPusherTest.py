#!/usr/bin/env python
## Creates a tree,4 topology to test circuitpusher functionality
## Prerequisite: Copy circuitpusher.py to /opt/floodlight/floodlight on test VM (controller node)
## @author KC Wang

import bigtest.controller
import bigtest
import json
import urllib
import time
from util import *
import httplib
import re

env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controllerNode = env.node1()
controllerCli = controllerNode.cli()
controllerIp = controllerNode.ipAddress()

mininetNode = env.node2()
mininetCli = mininetNode.cli()

controllerCli.gotoBashMode()
controllerCli.runCmd("uptime")

# wait for mininet settles and all switches connected to controller
mininetCli.gotoMininetMode("--controller=remote --ip=%s --mac --topo=tree,4" % controllerIp)
switches = ["00:00:00:00:00:00:00:1%c" % x for x in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']]
controllerNode.waitForSwitchCluster(switches)

# mininet pingall to make all devices known to floodlight
mininetCli.runCmd("pingall")

# enter working directory of circuitpusher
command="cd /opt/floodlight/floodlight"
controllerCli.runCmd(command)

# push a circuit from h1 to h16
command="./circuitpusher.py --controller=%s:8080 --type ip --src %s --dst %s --add --name test-circuit-1" % (controllerIp, "10.0.0.1","10.0.0.16") 
x = controllerCli.runCmd(command)

# verify using staticflowentrypusher each switch has correct flowentry
command="http://%s:8080/wm/staticflowentrypusher/list/all/json" % controllerIp
y = urllib.urlopen(command).read()
parsedResult = json.loads(y)

expectedSwitches = ["00:00:00:00:00:00:00:1%c" % x for x in ['1', '2', '3', '4', '9', 'd', 'f']]
foundSwitches = dict(parsedResult)

for key in expectedSwitches:
    if foundSwitches.has_key(key):
        flowEntries = dict(parsedResult.get(key))
        print "found switch %s with %s flows" % (key, len(flowEntries))
        bigtest.Assert(len(flowEntries)==4)
    else:
        print "missing switch %s" % key
        bigtest.Assert(False)

# do iperf test to confirm things working (this is meaningful only if forwarding module is unloaded)

mininetCli.runCmd("h16 iperf -s &")
x = mininetCli.runCmd("h1 iperf -c h16 -t 2")
bigtest.Assert(not "connect failed" in x)

mininetCli.runCmd("h16 pkill iperf")

# push another circuit from h1 to h9
command="./circuitpusher.py --controller=%s:8080 --type ip --src %s --dst %s --add --name test-circuit-2" % (controllerIp, "10.0.0.1","10.0.0.9")
x = controllerCli.runCmd(command)

# verify using staticflowentrypusher each switch has correct flowentry                                                    
command="http://%s:8080/wm/staticflowentrypusher/list/all/json" % controllerIp
y = urllib.urlopen(command).read()
parsedResult = json.loads(y)

expectedSwitches = ["00:00:00:00:00:00:00:1%c" % x for x in ['1', '2', '3', '4', '9', 'a', 'b', 'd', 'f']]
expectedSwitchesWithEightFlows = ["00:00:00:00:00:00:00:1%c" % x for x in ['1', '2', '3', '4', '9']]
expectedSwitchesWithFourFlows = ["00:00:00:00:00:00:00:1%c" % x for x in ['a', 'b', 'd', 'f']]
foundSwitches = dict(parsedResult)

# verify new entries are in place and old entries were not affected
for key in expectedSwitches:
    if foundSwitches.has_key(key):
        flowEntries = dict(parsedResult.get(key))
        print "found switch %s with %s flows" % (key, len(flowEntries))
        if key in expectedSwitchesWithEightFlows:
            bigtest.Assert(len(flowEntries)==8)
        if key in expectedSwitchesWithFourFlows:
            bigtest.Assert(len(flowEntries)==4)
    else:
        print "missing switch %s" % key
        bigtest.Assert(False)

# delete second flow
command="./circuitpusher.py --controller=%s:8080 --delete --name test-circuit-2" % (controllerIp)
x = controllerCli.runCmd(command)

# verify using staticflowentrypusher each switch has correct flowentry
command="http://%s:8080/wm/staticflowentrypusher/list/all/json" % controllerIp
y = urllib.urlopen(command).read()
parsedResult = json.loads(y)

expectedSwitches = ["00:00:00:00:00:00:00:1%c" % x for x in ['1', '2', '3', '4', '9', 'd', 'f']]
foundSwitches = dict(parsedResult)

# verify entries removed and first circuit still intact
for key in expectedSwitches:
    if foundSwitches.has_key(key):
        flowEntries = dict(parsedResult.get(key))
        print "found switch %s with %s flows" % (key, len(flowEntries))
        bigtest.Assert(len(flowEntries)==4)
    else:
        print "missing switch %s" % key
        bigtest.Assert(False)

# do an iperf test (this is meaningful only if forwarding module is unloaded)
mininetCli.runCmd("h16 iperf -s &")
x = mininetCli.runCmd("h1 iperf -c h16 -t 2")
bigtest.Assert(not "connect failed" in x)

mininetCli.runCmd("h16 pkill iperf")

# remove flow 1
command="./circuitpusher.py --controller=%s:8080 --delete --name test-circuit-1" % (controllerIp)
x = controllerCli.runCmd(command)

# verify using staticflowentrypusher each switch has correct flowentry                                                    
command="http://%s:8080/wm/staticflowentrypusher/list/all/json" % controllerIp
y = urllib.urlopen(command).read()
parsedResult = json.loads(y)

foundSwitches = dict(parsedResult)

# confirm all switches clean
for key in foundSwitches:
    flowEntries = dict(parsedResult.get(key))
    bigtest.Assert(len(flowEntries)==0)

# end test
env.endTest()
