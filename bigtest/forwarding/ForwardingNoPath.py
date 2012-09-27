#!/usr/bin/env python

import bigtest.controller
import bigtest

env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controllerNode = env.node1()
mininetNodeCli = env.node2().cli()

mininetNodeCli.gotoBashMode()
mininetNodeCli.runCmd("rm -f islands.py")
with open("bigtest/islands.py", "r") as topofile:
    for line in topofile:
        mininetNodeCli.runCmd("echo \'%s\' >> islands.py" % (line[:-1], ))

mininetNodeCli.gotoMininetMode("--controller=remote --ip=%s --custom islands.py --topo=islands,2,2,1" % controllerNode.ipAddress())
x = mininetNodeCli.runCmd("pingall")
x = mininetNodeCli.runCmd("pingall")
bigtest.Assert("Results: 66%" in x)

env.endTest()
