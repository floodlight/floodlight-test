#!/usr/bin/env python

import bigtest.controller
import bigtest

env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controllerNode = env.node1()
controllerCli = controllerNode.cli()
mininetNode = env.node2()
mininetCli = mininetNode.cli()

controllerCli.gotoBashMode()
controllerCli.runCmd("uptime")


mininetCli.gotoMininetMode("--controller=remote --ip=%s --topo=tree,4" % controllerNode.ipAddress())
switches = ["00:00:00:00:00:00:00:1%c" % x for x in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']]
controllerNode.waitForSwitchCluster(switches)
x = mininetCli.runCmd("pingall")

#intentionally putting this after pingall as I don't want the pingall to
#start later.  If there's a timing issue, we need to catch it.
bigtest.Assert("Results: 0%" in x)

env.endTest()
