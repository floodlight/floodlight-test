#!/usr/bin/env python
# This test checks if the controller can correctly handle multiple switches
# connecting with the same DPID. The expected behavior is that the latest
# switch would be retained and the older switch would be discarded. The test
# creates a topology on cli1 first and verifies its ping.  Then, we create
# the sam topology on cli2 and connect it to the same controller on cli1.
# We verify that the ping works on cli2 and not on cli1.
#
# However, we cannot test what we actually want to see, namely that the
# controller closes the TCP connection to the switches on cli1. In order
# to do that we need a custom OF speaker and not mininet.....
import bigtest.controller
import time
from util import *

env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controller1 = env.node1()
cli1 = controller1.cli()
controller2 = env.node2()
cli2 = controller2.cli()

################
# Start mininet with tree,2,4 from cli1
cli1.gotoBashMode()
enableDebugLog(cli1)

cli2.gotoBashMode()

cli1.runCmd("sudo mn --mac --topo=tree,2,4")
# Wait for all switches to connect
switches = ["00:00:00:00:00:00:00:%02x" % x for x in [17, 18, 19, 20, 21]]
controller1.waitForSwitchCluster(switches)

# Verify pings
cli1.runCmd("h1 ping -c1 -w1 10.0.0.100")
verifyPing(cli1, "h1", "h3")


################
# Start mininet with tree,2,4 from cli2
# Exit from cli1
cli2.gotoMininetMode("--controller=remote --mac --ip=%s --topo=tree,2,4" % controller1.ipAddress())
# The exit is written specifically after the second switch connects
cli1.runCmd("exit")
cli1.runCmd("sudo mn -c")
# After cli2 connects, cli1 gets disconnected, however, it will try to
# reconnect (which will disconnect cli2). After we exit cli1, cli2 will
# eventually succeed in reconnecting. Since OVS's default max backoff is
# 8sec, this is guaranteed to happen after 8sec. So we wait for 10sec.
time.sleep(10)
controller1.waitForSwitchCluster(switches)

# Verify ping from cli2 works and cli1 doesn't.
cli2.runCmd("h1 ping -c1 -w1 10.0.0.150")
verifyPing(cli2, "h1", "h3")


################
# Start mininet from cli1
# Exit from cli2
cli1.runCmd("sudo mn --mac --topo=tree,2,4")
cli2.runCmd("exit")
cli2.runCmd("sudo mn -c")
time.sleep(10)
# Wait for all switches to connect
controller1.waitForSwitchCluster(switches)

# Verify ping from cli1 works and cli2 doesn't.
cli1.runCmd("h1 ping -c1 -w1 10.0.0.200")
verifyPing(cli1, "h1", "h3")

env.endTest()


