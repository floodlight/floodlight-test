# This is topology file for IslandHostMobilityTest2.py bigtest. 
# contents of tis file is uploaded to node1 (controller1) and it is
# run there. Upto 100 mac moves are performed.

from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info, output, error
import random
import sys
from time import sleep


c1ip='CONTROLLER1_IP'
c2ip='CONTROLLER2_IP'

net = Mininet(autoSetMacs=True, controller=RemoteController, switch=OVSKernelSwitch)
print "*** Adding Controller nodes c1 and c2"
c1 = net.addController(name = 'RemoteBSC1', controller = RemoteController, defaultIP=c1ip)
c2 = net.addController(name = 'RemoteBSC2', controller = RemoteController, defaultIP=c2ip)

print "*** Adding switches s1 - s29"
s1 = net.addSwitch( 's1' ,  mac='55:55:55:AA:AA:01') 
s2 = net.addSwitch( 's2',   mac='55:55:55:AA:AA:02' ) 
s3 = net.addSwitch( 's3',   mac='55:55:55:AA:AA:03' ) 
s4 = net.addSwitch( 's4',   mac='55:55:55:AA:AA:04' ) 
print "*** Adding broadcast simulation switch switches s100"
s100 = net.addSwitch( 's100' , mac='BC:BC:BC:BC:01:00') # Broadcast Node
print "*** Adding hosts h1 - h10"
h1 = net.addHost('h1', ip='10.0.0.1', mac='AA:BB:CC:DD:EE:01') 
h2 = net.addHost('h2', ip='10.0.0.2', mac='AA:BB:CC:DD:EE:02') 
h3 = net.addHost('h3', ip='10.0.0.3', mac='AA:BB:CC:DD:EE:03') 
h4 = net.addHost('h4', ip='10.0.0.4', mac='AA:BB:CC:DD:EE:04') 
last_host_that_can_move = 4

# Adding hosts that don't move
print "*** Adding hosts that don't move"
h21 = net.addHost('h21', ip='10.0.0.21', mac='AA:BB:CC:DD:EE:21') 
h22 = net.addHost('h22', ip='10.0.0.22', mac='AA:BB:CC:DD:EE:22') 
h23 = net.addHost('h23', ip='10.0.0.23', mac='AA:BB:CC:DD:EE:23') 
h24 = net.addHost('h24', ip='10.0.0.24', mac='AA:BB:CC:DD:EE:24') 
print "*** Attaching the hosts that don't move such that every island has one of these hosts"
s1.linkTo(h1)
s1.linkTo( h21 ) 
s2.linkTo(h2)
s2.linkTo( h22 ) 
s3.linkTo(h3)
s3.linkTo( h23 ) 
s4.linkTo(h4)
s4.linkTo( h24 ) 

s1.linkTo( s2 )
s2.linkTo( s100 )
s3.linkTo( s100 )
s4.linkTo( s100 )

print "*** Building network"
net.build()
print "*** Starting s1 - s4 with c1"
s1.start([c1])
s2.start([c1])
s3.start([c1])
s4.start([c1])
print "*** Starting s100 with c2"
s100.start([c2])

my_switches = []
for x in range (1,5):
    my_switches.append('s'+str(x))

my_static_hosts = []
for x in range(21, 25):
    my_static_hosts.append(net.nameToNode['h'+str(x)])

my_hosts = []
for x in range (1, last_host_that_can_move+1):
    my_hosts.append(net.nameToNode['h'+str(x)])

my_moves=[]

print "***** Baseline: Pinging all pairs"
ping_output = net.pingAll()

def show_topology():
    output("------- Topology -------\n")
    for s in net.switches:
        output(s.name, '<->')
        for intf in s.intfs.values():
            name = s.connection.get(intf, (None, 'Unknown ') ) [ 1 ]
            output( ' %s' % name )
        output('\n')
    output('\n')

def sleep_with_dots(n):
    for n in range(1,n+1):
        sys.stdout.write("%d." % n)
        sys.stdout.flush()
        sleep(1)
    sys.stdout.write('\n')
    
def run_loop(count):
    print "*** Starting loop"
    idx = 0
    stop_tests = False
    while ((idx < count) and (not stop_tests)):
        # sleep for 7 seconds for olf flows to expire
        # sleep_with_dots(7)
        sys.stdout.write('\n')
        idx += 1
        random_host   = random.choice(my_hosts)
        random_switch = random.choice(my_switches)
        print "****** %2d: Moving host %s to switch %s" % (idx, random_host.name, random_switch)
        net.detachHost(random_host.name)
        net.attachHost(random_host.name, random_switch)
        show_topology()
        my_moves.append(["%s, %s" % (random_host.name, random_switch)])
        # sleep_with_dots(7)
        # Pinging all pairs
        print "***** Pinging from moved host %s to all other hosts" % random_host.name
        for tgt in my_static_hosts:
            print "******** Pinging from %s to %s" % (random_host.name, tgt)
            result = random_host.cmd( 'ping -c 1 -W 2 ' + tgt.IP() )
            #print result
        print "***** Pinging between all dynamic pairs"
        ping_output = net.ping(my_hosts)
        if (ping_output > 0):
            print 'ping output = %d' % ping_output
            # Sleep to clear the flows and then retry
            sleep_with_dots(7)
            my_moves.append("7s sleep")
            print "***** Pinging after sleep of 7s between all dynamic pairs"
            ping_output = net.ping(my_hosts)
            print 'ping output = %d' % ping_output
            if (ping_output > 0):
                # still drops found 
                stop_tests = True
                print "Test Failed due to drops"
                print "Drops found after sleep - stopping tests"
                print "Host Moves: %s" % my_moves

# run for up to 100 mac moves, unless there are failures earlier.
print "Starting test - 50 loops"
# If you increase the number of loops make sure that the console/cli timeout is 
# long enough otherwise the test would fail.
run_loop(10)
