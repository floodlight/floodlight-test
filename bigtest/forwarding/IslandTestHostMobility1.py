#!/usr/bin/env python
## Creates a 3 switch linear topology, with the middle switch
## being connected to another controller.
## We make sure everything can ping then
## move the nodes around on the topology
## and make sure pings work again.
from time import sleep
import bigtest.controller
import re
import time
import bigtest

mininettopo = """#!/usr/bin/python 
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel

def addHost(net, N):
    name= 'h%d' % N
    ip = '10.0.0.%d' % N
    mac = '00:00:00:00:00:%02d' % N
    return net.addHost(name, ip=ip, mac=mac)

def MultiControllerNet(c1ip = 'CONTROLLER1_IP', c2ip = 'CONTROLLER2_IP'):
    \"Create a network with multiple controllers.\"
    # Important to set autoSetMacs to True otherwise after detach and attach the mac address
    # would change and it would simulate a new device add instead of device move.
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, autoSetMacs=True)
    print \"Creating controllers\"
    c1 = net.addController(name = 'RemoteFloodlight1', controller = RemoteController, defaultIP=c1ip)
    c2 = net.addController(name = 'RemoteFloodlight2', controller = RemoteController, defaultIP=c2ip)

    print \"*** Creating switches\"
    s1 = net.addSwitch( 's1' )
    s2 = net.addSwitch( 's2' )
    s3 = net.addSwitch( 's3' )

    print \"*** Creating hosts\"
    hosts1 = [ addHost( net, n ) for n in 3, 4 ] 
    hosts2 = [ addHost( net, n ) for n in 5, 6 ] 
    hosts3 = [ addHost( net, n ) for n in 7, 8 ] 

    print \"*** Creating links\"
    for h in hosts1:
        s1.linkTo( h ) 
    for h in hosts2:
        s2.linkTo( h ) 
    for h in hosts3:
        s3.linkTo( h ) 
    s1.linkTo( s2 )
    s2.linkTo( s3 )

    print \"*** Building network\"
    net.build()
                    
    # In theory this doesn't do anything
    c1.start()
    c2.start()

    print \"*** Starting Switches\"
    s1.start([c1])
    s2.start([c2])
    s3.start([c1])
    return net

net = MultiControllerNet()
CLI(net)
"""

def putTopoOnNode(cNode, mininettopo):
    cli = cNode.cli()
    cli.gotoBashMode()
    console = cli.console()

    console.sendline('cat > topo.py << EOF')
    for l in mininettopo.split("\n"):
        console.sendline(l)
    console.sendline("EOF")
    cli.expectPrompt()
    cli.runCmd("chmod 755 topo.py")

env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controller1 = env.node1()
cli1 = controller1.cli()
controller2 = env.node2()
cli2 = controller2.cli()

mininettopo = mininettopo.replace("CONTROLLER1_IP", controller1.ipAddress())
mininettopo = mininettopo.replace("CONTROLLER2_IP", controller2.ipAddress())

putTopoOnNode(controller1, mininettopo)
cli1.gotoBashMode()
cli1.runCmd("sudo python topo.py")

log("Sleeping to allow the network to converge")
sleep(20)
o = cli1.runCmd("pingall")
bigtest.Assert(re.search(" 0% dropped", o, re.MULTILINE))

# ping to the h3 which is being moved to have a flowmod to h3
cli1.runCmd("h7 ping -c 1 h3")
log("Detaching h3 from s1")
cli1.runCmd("detach h3 s1")

#Add this sleep as the transition from s1 to s2 could be
#a move from non-broadcast domain to bradcast domain
sleep(5)

log("Attaching h3 to s2 (controller 2)")
cli1.runCmd("attach h3 s2")

n = cli1.runCmd("net")
# ping from h3 to island/cluster of h5 so that it is not a silent move
# Attachment point of h3 in cluster of h7 is unchanged 
cli1.runCmd("h3 ping -c 1 h5") # s2 island
# ping to h3 again, the flow mod from h7 to h3 should have been 
# reprogrammed
o = cli1.runCmd("h7 ping -c 1 h3")
bigtest.Assert(re.search(" 0% packet loss", o, re.MULTILINE))
# make sure the h7 to h3 flowmod established before the move hasn't
# expired
# ping from h3 to other islands so that it is not silent move for those
# islands as well
cli1.runCmd("h3 ping -c 1 h4") # s1 island
cli1.runCmd("h3 ping -c 1 h7") # s3 island
o = cli1.runCmd("pingall")
bigtest.Assert(re.search(" 0% dropped", o, re.MULTILINE))

# Start the next round of move
log("Detaching h3 from s2")
cli1.runCmd("detach h3 s2")

log("Attaching h3 to s3 (controller 1)")
cli1.runCmd("attach h3 s3")

# ping from h3 to each island/cluster
cli1.runCmd("h3 ping -c 1 h4") # s1 island
cli1.runCmd("h3 ping -c 1 h5") # s2 island
cli1.runCmd("h3 ping -c 1 h7") # s3 island
o = cli1.runCmd("pingall")
bigtest.Assert(re.search(" 0% dropped", o, re.MULTILINE))

env.endTest()
