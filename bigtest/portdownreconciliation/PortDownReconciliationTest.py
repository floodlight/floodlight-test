#!/usr/bin/env python
#Author: Jason Parraga, Marist College (Jason.Parraga1@marist.edu)
'''' Warning: This test can be unreliable sometimes. Sometimes the test 
#suite will lag, causing flow expiration times to reach ~ 12 seconds.
#When properly functioining the flows will be deleted in ~ 2 seconds. Then the
following ping shows that the down link is avoided.  '''
import bigtest.controller
import bigtest
import json
import urllib
import time

env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controllerNode = env.node1()
mininetNodeCli = env.node2().cli()

# Startup the controller with the custom square topology
mininetNodeCli.gotoMininetMode("--controller=remote --ip=%s --custom square.py --topo=square" % controllerNode.ipAddress())

# Wait for network to converge (An attempt to mitigate unreliable results, see above)                                                                                                                                                                                             
time.sleep(5)

# Ping between the hosts to establish some temporary flows
x = mininetNodeCli.runCmd("h5 ping -c1 h6")
bigtest.Assert(" 0% packet loss" in x)

# Verify that the traffic is using a direct route between switches 1,3
command = "http://%s:8080/wm/core/switch/all/flow/json" % controllerNode.ipAddress()
x = urllib.urlopen(command).read()
# Only switches 1,3 should contain flows
bigtest.Assert(not "\"00:00:00:00:00:00:00:01\":[]" in x
               and not "\"00:00:00:00:00:00:00:03\":[]" in x 
               and "\"00:00:00:00:00:00:00:02\":[]" in x
               and "\"00:00:00:00:00:00:00:04\":[]" in x)

# Bring down the link between s1 and s3, triggering port down reconciliation
x = mininetNodeCli.runCmd("link s1 s3 down")

#Wait until any invalid flows are removed (Output Port 2 involves inter switch links, which should be deleted)
timeToDeleteFlows = time.time()
while("[{\"port\":2,\"maxLength\":-1,\"length\":8,\"type\":\"OUTPUT\",\"lengthU\":8}]" in urllib.urlopen(command).read()):
    pass

# Calculate the time it has taken for the invalid flows to be removed
timeToDeleteFlows = time.time()-timeToDeleteFlows

# Verify that the hosts can successfully ping now that the invalid flows are deleted
x = mininetNodeCli.runCmd("h5 ping -c1 h6")
bigtest.Assert(" 0% packet loss" in x)

# Verify that the traffic is using an alternative route to route traffic around the link down
command = "http://%s:8080/wm/core/switch/all/flow/json" % controllerNode.ipAddress()
x = urllib.urlopen(command).read()
# All switches should now contain flows, not just switches 1,3
bigtest.Assert(not "\"00:00:00:00:00:00:00:01\":[]" in x
                and not "\"00:00:00:00:00:00:00:03\":[]" in x 
                and not "\"00:00:00:00:00:00:00:02\":[]" in x
                and not "\"00:00:00:00:00:00:00:04\":[]" in x)

# Print the time it took to delete the invalid flows
print "It took " + str(timeToDeleteFlows) + " seconds to delete the invalid flows";

env.endTest()