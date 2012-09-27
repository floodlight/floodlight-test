#!/usr/bin/env python

import re
from time import sleep

import bigtest
from mininet.net import Mininet
from mininet.node import UserSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
import bigtest.controller
from bigtest.util.context import NetContext, EnvContext

def addHost(net, N):
    name= 'h%d' % N
    ip = '10.0.0.%d' % N
    return net.addHost(name, ip=ip)

def MultiControllerNet(c1ip, c2ip):
    "Create a network with multiple controllers."

    net = Mininet(controller=RemoteController, switch=UserSwitch)

    print "Creating controllers"
    c1 = net.addController(name = 'RemoteFloodlight1', controller = RemoteController, defaultIP=c1ip)
    c2 = net.addController(name = 'RemoteFloodlight2', controller = RemoteController, defaultIP=c2ip)

    print "*** Creating switches"
    s1 = net.addSwitch( 's1' )
    s2 = net.addSwitch( 's2' )
    s3 = net.addSwitch( 's3' )
    s4 = net.addSwitch( 's4' )

    print "*** Creating hosts"
    hosts1 = [ addHost( net, n ) for n in 3, 4 ] 
    hosts2 = [ addHost( net, n ) for n in 5, 6 ] 
    hosts3 = [ addHost( net, n ) for n in 7, 8 ] 
    hosts4 = [ addHost( net, n ) for n in 9, 10 ]

    print "*** Creating links"
    for h in hosts1:
        s1.linkTo( h ) 
    for h in hosts2:
        s2.linkTo( h ) 
    for h in hosts3:
        s3.linkTo( h ) 
    for h in hosts4:
        s4.linkTo( h )

    s1.linkTo( s2 )
    s2.linkTo( s3 )
    s4.linkTo( s2 )

    print "*** Building network"
    net.build()
    
    # In theory this doesn't do anything
    c1.start()
    c2.start()

    #print "*** Starting Switches"
    s1.start( [c1] )
    s2.start( [c2] )
    s3.start( [c1] )
    s4.start( [c1] )

    return net


with EnvContext(bigtest.controller.TwoNodeTest()) as env:
  log = bigtest.log.info

  controller1 = env.node1()
  cli1 = controller1.cli()

  controller2 = env.node2()
  cli2 = controller2.cli()

  print "ip1:%s ip2:%s" % (controller1.ipAddress(), controller2.ipAddress())

  with NetContext(MultiControllerNet(controller1.ipAddress(), controller2.ipAddress())) as net:
    sleep(20)
    ## net.pingAll() returns percentage drop so the bigtest.Assert(is to make sure 0% dropped)
    o = net.pingAll()
    bigtest.Assert(o == 0)
