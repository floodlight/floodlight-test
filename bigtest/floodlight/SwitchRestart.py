#!/usr/bin/env python

import bigtest.controller
import bigtest

env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controller1 = env.node1()
cli1 = controller1.cli()
controller2 = env.node2()
cli2 = controller2.cli()

# Restart mininet with the same mac to simulate a real
# switch disconnect/connect, verify pingall succeeds
cli1.runCmd("show version")
cli1.gotoBashMode()
cli1.runCmd("uptime")

dpids = ["00:00:00:00:00:00:00:%02x" % x for x in [9, 10, 11, 12, 13, 14, 15]]
cli2.gotoMininetMode("--controller=remote --ip=%s --mac --topo=tree,3" % controller1.ipAddress())
controller1.waitForSwitchCluster(dpids)

x = cli2.runCmd("pingall")
bigtest.Assert("Results: 0%" in x)
cli2.runCmd("exit")

log("restart mininet and verify pingall")
cli2.gotoMininetMode("--controller=remote --ip=%s --mac --topo=tree,3" % controller1.ipAddress())
controller1.waitForSwitchCluster(dpids)

x = cli2.runCmd("pingall")
bigtest.Assert("Results: 0%" in x)
cli2.runCmd("exit")

env.endTest()
