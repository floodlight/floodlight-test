#!/usr/bin/env python

import bigtest.controller
import bigtest
import json
import urllib
import time
from util import *
import httplib

env = bigtest.controller.TwoNodeTest()
log = bigtest.log.info

controllerNode = env.node1()
controllerCli = controllerNode.cli()
controllerIp = controllerNode.ipAddress()

mininetNode = env.node2()
mininetCli = mininetNode.cli()

controllerCli.gotoBashMode()
controllerCli.runCmd("uptime")

# wait for mininet settles and all switches connected to controller
mininetCli.gotoMininetMode("--controller=remote --ip=%s --topo=tree,4" % controllerIp)
switches = ["00:00:00:00:00:00:00:1%c" % x for x in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']]
controllerNode.waitForSwitchCluster(switches)

# allow mininet hosts to accept broadcast ping
for i in range(1,17):
    hosti = "h%s" % i
    enableMininetHostICMPBroadcast(mininetCli, hosti)

# cleanup all rules
command = "http://%s:8080/wm/firewall/rules/json" % controllerIp
x = urllib.urlopen(command).read()
parsedResult = json.loads(x)

for i in range(len(parsedResult)):
    params = "{\"ruleid\":\"%s\"}" % parsedResult[i]['ruleid']
    command = "/wm/firewall/rules/json"
    url = "%s:8080" % controllerIp
    connection =  httplib.HTTPConnection(url)
    connection.request("DELETE", command, params)
    x = connection.getresponse().read()
    bigtest.Assert("Rule deleted" in x)
# sleep to time out previous flows in switches 
time.sleep(10)

# Test REST rules, empty  
command = "http://%s:8080/wm/firewall/rules/json" % controllerIp
x = urllib.urlopen(command).read()
bigtest.Assert("[]" in x)

# Test REST disable
command = "http://%s:8080/wm/firewall/module/disable/json" % controllerIp
x = urllib.urlopen(command).read()
bigtest.Assert("stopped" in x)

# pingall should succeed since firewall disabled
x = mininetCli.runCmd("pingall")
bigtest.Assert("Results: 0%" in x)

# Test REST storage rules, empty
command = "http://%s:8080/wm/firewall/module/storageRules/json" % controllerIp
x = urllib.urlopen(command).read()
bigtest.Assert("[]" in x)

# Test enable
command = "http://%s:8080/wm/firewall/module/enable/json" % controllerIp
x = urllib.urlopen(command).read()
bigtest.Assert("running" in x)

# sleep to time out previous flows in switches
time.sleep(10)

# With firewall enabled and no rules, all traffic stopped
# arbitrary ping (instead of pingall which takes too long to fail), should fail (ICMP)
x = mininetCli.runCmd("h3 ping -c3 h7")
bigtest.Assert("100% packet loss" in x)

# TCP, UDP should fail - iperf takes too long to fail, nc doesn't have good output for test

# Add rules to enable a set of switches across three switches
# interesting punch-out test
# can do the same with specific switch-ports, but only practical for custom topology or with circuit pusher

# (h1, h2)--s20---s19---s21--(h3, h4) 
params = "{\"switchid\":\"20\"}"
command = "http://%s:8080/wm/firewall/rules/json" % controllerIp
urllib.urlopen(command, params).read()
params = "{\"switchid\":\"19\"}"
command = "http://%s:8080/wm/firewall/rules/json" % controllerIp
urllib.urlopen(command, params).read()
params = "{\"switchid\":\"21\"}"
command = "http://%s:8080/wm/firewall/rules/json" % controllerIp
urllib.urlopen(command, params).read()

# Two end points can ping and iperf  
x = mininetCli.runCmd("h1 ping -c3 h4")
bigtest.Assert(" 0% packet loss" in x)

mininetCli.runCmd("h3 iperf -s &")
x = mininetCli.runCmd("h2 iperf -c h3 -t 2")
bigtest.Assert(not "connect failed" in x)

mininetCli.runCmd("h3 pkill iperf")
# sleep to time out previous flows in switches 
time.sleep(10)

# Another two end points cannot ping and iperf
x = mininetCli.runCmd("h7 ping -c3 h4")
bigtest.Assert("100% packet loss" in x)

# iperf test omitted, takes too long to fail

# clean up all three rules - testing delete rule
# for now, retrieve all rule ids from GET rules
command = "http://%s:8080/wm/firewall/rules/json" % controllerIp
x = urllib.urlopen(command).read()
parsedResult = json.loads(x)

for i in range(len(parsedResult)):
    params = "{\"ruleid\":\"%s\"}" % parsedResult[i]['ruleid']
    command = "/wm/firewall/rules/json"
    url = "%s:8080" % controllerIp
    connection =  httplib.HTTPConnection(url)
    connection.request("DELETE", command, params)
    x = connection.getresponse().read()
    bigtest.Assert("Rule deleted" in x)
# sleep to time out previous flows in switches
time.sleep(10)

# Add rules to allow traffic between two nodes based on IP
command = "/wm/firewall/rules/json"
url = "%s:8080" % controllerIp
connection =  httplib.HTTPConnection(url)

params = "{\"src-ip\":\"10.0.0.3/32\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.3/32\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"src-ip\":\"10.0.0.7/32\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.7/32\"}"
connection.request("POST", command, params)
connection.getresponse().read()

x = mininetCli.runCmd("h3 ping -c3 h7")
bigtest.Assert(" 0% packet loss" in x)

# cleanup all rules
command = "http://%s:8080/wm/firewall/rules/json" % controllerIp
x = urllib.urlopen(command).read()
parsedResult = json.loads(x)

for i in range(len(parsedResult)):
    params = "{\"ruleid\":\"%s\"}" % parsedResult[i]['ruleid']
    command = "/wm/firewall/rules/json"
    url = "%s:8080" % controllerIp
    connection =  httplib.HTTPConnection(url)
    connection.request("DELETE", command, params)
    x = connection.getresponse().read()
    bigtest.Assert("Rule deleted" in x)
# sleep to time out previous flows in switches
time.sleep(10)

# Add rules to enable ICMP only for two other nodes
# must allow both ARP reply and ICMP

command = "/wm/firewall/rules/json"
url = "%s:8080" % controllerIp
connection =  httplib.HTTPConnection(url)

params = "{\"src-ip\":\"10.0.0.3/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.3/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"src-ip\":\"10.0.0.7/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.7/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"src-ip\":\"10.0.0.3/32\",\"proto-type\":\"ICMP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.3/32\",\"proto-type\":\"ICMP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"src-ip\":\"10.0.0.7/32\",\"proto-type\":\"ICMP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.7/32\",\"proto-type\":\"ICMP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

# ping works
x = mininetCli.runCmd("h3 ping -c3 h7")

bigtest.Assert(" 0% packet loss" in x)

# iperf doesn't - takes too long

# cleanup all rules
command = "http://%s:8080/wm/firewall/rules/json" % controllerIp
x = urllib.urlopen(command).read()
parsedResult = json.loads(x)

for i in range(len(parsedResult)):
    params = "{\"ruleid\":\"%s\"}" % parsedResult[i]['ruleid']
    command = "/wm/firewall/rules/json"
    url = "%s:8080" % controllerIp
    connection =  httplib.HTTPConnection(url)
    connection.request("DELETE", command, params)
    x = connection.getresponse().read()
    bigtest.Assert("Rule deleted" in x)
# sleep to time out previous flows in switches
time.sleep(10)

# Add rules to enable TCP for two nodes
command = "/wm/firewall/rules/json"
url = "%s:8080" % controllerIp
connection =  httplib.HTTPConnection(url)

params = "{\"src-ip\":\"10.0.0.3/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.3/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"src-ip\":\"10.0.0.7/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.7/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"src-ip\":\"10.0.0.3/32\",\"proto-type\":\"TCP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.3/32\",\"proto-type\":\"TCP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"src-ip\":\"10.0.0.7/32\",\"proto-type\":\"TCP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.7/32\",\"proto-type\":\"TCP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

# iperf TCP works, UDP doesn't
mininetCli.runCmd("h3 iperf -s &")

x = mininetCli.runCmd("h7 iperf -c h3 -t 2")

bigtest.Assert(not "connect failed" in x)

command = "http://%s:8080/wm/core/switch/all/flow/json" % controllerIp
x = urllib.urlopen(command).read()
print json.loads(x)

mininetCli.runCmd("h3 pkill iperf")

# timeout to remove previous flow entries
time.sleep(10)

mininetCli.runCmd("h3 iperf -s -u &")

x = mininetCli.runCmd("h7 iperf -c h3 -u -t 2")

bigtest.Assert(not "Server Report" in x)

# cleanup all rules                                                                                                              
command = "http://%s:8080/wm/firewall/rules/json" % controllerIp
x = urllib.urlopen(command).read()
parsedResult = json.loads(x)

for i in range(len(parsedResult)):
    params = "{\"ruleid\":\"%s\"}" % parsedResult[i]['ruleid']
    command = "/wm/firewall/rules/json"
    url = "%s:8080" % controllerIp
    connection =  httplib.HTTPConnection(url)
    connection.request("DELETE", command, params)
    x = connection.getresponse().read()
    bigtest.Assert("Rule deleted" in x)
# sleep to time out previous flows in switches
time.sleep(10)

# Add rules to enable UDP for two nodes
command = "/wm/firewall/rules/json"
url = "%s:8080" % controllerIp
connection =  httplib.HTTPConnection(url)

params = "{\"src-ip\":\"10.0.0.3/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.3/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"src-ip\":\"10.0.0.7/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.7/32\",\"proto-type\":\"ARP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"src-ip\":\"10.0.0.3/32\",\"proto-type\":\"UDP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.3/32\",\"proto-type\":\"UDP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"src-ip\":\"10.0.0.7/32\",\"proto-type\":\"UDP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

params = "{\"dst-ip\":\"10.0.0.7/32\",\"proto-type\":\"UDP\"}"
connection.request("POST", command, params)
connection.getresponse().read()

# UDP now works

x = mininetCli.runCmd("h7 iperf -c h3 -u -t 2")

bigtest.Assert("Server Report" in x)

# Boundary test 1: L3 broadcast ...

env.endTest()
