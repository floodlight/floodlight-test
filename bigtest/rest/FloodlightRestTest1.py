#!/usr/bin/env python
# owner: alex reimers
# This test exercises the Floodlight REST API directly.
# Note that all of these APIs might not be used in the BigSwithController

import bigtest.controller
import bigtest
import re
import mininet.topolib
from mininet.cli import CLI

env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controller1 = env.node1()
cli1 = controller1.cli()
net = controller1.mininet(mininet.topolib.TreeTopo(depth=2))
switch1 = "00:00:00:00:00:00:00:05"
switch2 = "00:00:00:00:00:00:00:06"
switch3 = "00:00:00:00:00:00:00:07"
switches = [switch1, switch2, switch3]
controller1.waitForSwitches(switches)
net.pingAll()
switchesConnected = controller1.restGet("core/controller/switches/json", "dpid")
log("Testing switches")
for switch in switches:
    bigtest.Assert(switch in switchesConnected)

controller1.waitForSwitchCluster(switches)
log("Testing links")
links = controller1.restGet("/topology/links/json")
bigtest.Assert({"src-switch": str(switch1), "dst-switch": str(switch2), "dst-port": 3, "src-port": 1,
        "type": "internal"}) in links
bigtest.Assert({"src-switch": str(switch2), "dst-switch": str(switch1), "dst-port": 1, "src-port": 3,
        "type": "internal"}) in links
bigtest.Assert({"src-switch": str(switch1), "dst-switch": str(switch3), "dst-port": 3, "src-port": 2,
        "type": "internal"}) in links
bigtest.Assert({"src-switch": str(switch3), "dst-switch": str(switch1), "dst-port": 2, "src-port": 3,
        "type": "internal"}) in links

log("Testing clusters")
switchClusters = controller1.restGet("/topology/switchclusters/json")
## Make sure that the cluster was computed properly, key is switch1 with switches 1-3 in the cluster
for switch in switches:
    bigtest.Assert(switch in switchClusters[switch1])

log("Testing memory usage")
memory = controller1.restGet("core/memory/json")
bigtest.Assert(memory['free'] > 0)
bigtest.Assert(memory['total'] > 0)

log("Testing device manager")
devices = controller1.restGet("device/")

for device in devices:
    # get each device
    bigtest.Assert(controller1.restGet("device/?mac=%s" % (device["mac"][0])) != None)

log("Checking non-existant device")
bigtest.Assert(controller1.restGet("device/?mac=00:00:00:00:00:00") == [])

net.stop()
env.endTest()
