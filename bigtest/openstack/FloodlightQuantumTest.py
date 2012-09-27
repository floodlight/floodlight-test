#!/usr/bin/env python
# owner: alex
# This test does the following:
# - Restarts floodlight in the quantum config
# - Sets up 2 virtual networks and verifies ping/no-cross ping
# - Makes sure hosts can reach the default gateway

import time, re
import bigtest.controller
import mininet.topolib
from util import *

# Creates a virtual network for the floodlight quantum plugin
# The tenant is ignored for now but required
# Gateway is an IP in 1.2.3.4 notation
def createVirtualNetwork(controller, tenant, netName, guid, gateway = None):
    url = '/quantum/v1.0/tenants/%s/networks/%s' % (tenant, guid)
    if gateway is not None:
        data = '{"network":{"name":"%s","gateway":"%s","id":"%s"}}' % (netName, gateway, guid)
    else:
        data = '{"network":{"name":"%s"}}' % (netName)
    controller.urlPut(url, data)

# Adds a host to a virtual network for the floodlight quantum plugin
# The network must already exist
# The tenant is ignored for now but required
# MAC must be in the form of 01:02:03:04:05:06
def addHostToVirtualNetwork(controller, tenant, guid, port, attachId, mac):
    url = '/quantum/v1.0/tenants/%s/networks/%s/ports/%s/attachment' % (tenant, guid, port)
    data = '{"attachment":{"id":"%s","mac":"%s"}}' % (attachId, mac)
    controller.urlPut(url, data)

# Setup Env
env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controller = env.node1()
cli = controller.cli()
rest = controller.restGet
cli2 = env.node2().cli()

log("Restarting Floodlight with Quantum config")
floodlightLoadQuantumConfig(cli)

cli2.gotoBashMode()
cli2.gotoMininetMode("--controller=remote --ip=%s --mac --topo=linear,5" % controller.ipAddress())

hostmacs = ["00:00:00:00:00:%02x" % x  for x in xrange(6,11)]
switches = ["00:00:00:00:00:00:00:%02x" % x for x in xrange(1,6)]
controller.waitForSwitches(switches)
createVirtualNetwork(controller, "ten1", "net1", "guid1", "10.0.0.10")
addHostToVirtualNetwork(controller, "ten1", "guid1", "port1", "attach1", hostmacs[0])
addHostToVirtualNetwork(controller, "ten1", "guid1", "port2", "attach2", hostmacs[1])
createVirtualNetwork(controller, "ten2", "net2", "guid2", "10.0.0.10")
addHostToVirtualNetwork(controller, "ten2", "guid2", "port3", "attach3", hostmacs[2])
addHostToVirtualNetwork(controller, "ten2", "guid2", "port4", "attach4", hostmacs[3])
verifyPing(cli2, 'h6', 'h7')
verifyPing(cli2, 'h8', 'h9')
verifyNoPing(cli2, 'h6', 'h8')
verifyNoPing(cli2, 'h7', 'h9')
# verify default gateway works
verifyPing(cli2, 'h10', 'h8')
verifyPing(cli2, 'h6', 'h10')
verifyPing(cli2, 'h8', 'h10')

env.endTest()
