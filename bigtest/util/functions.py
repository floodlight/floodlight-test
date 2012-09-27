#!/usr/bin/env python
"""
This file contains utility methods used in BigTest.
Feel free to add to this file, but make so to comment it!
In the comment please include:
    - What the function does
    - What the input should be
    - What the output is
"""

import bigtest.controller
import time
import re
import json
import urllib2
import datetime
import pprint
from subprocess import Popen, PIPE
import bigtest

log = bigtest.log

# Expects bash mode. Runs a tcpdump and writes a traces to /var/log/tcpdump.pcap
# Will quote the filter
def startTcpdump(cli, filterStr="", interface="eth0"):
    cli.runCmd("sudo tcpdump -i %s -s 0 -w /log/bigswitch/tcpdump.pcap %s &" % (interface, filterStr))

# Kill all tcpdumps
def stopTcpdump(cli):
    cli.runCmd("sudo killall tcpdump");

# Cleanup any residual processes from mininet
def cleanupMininet():
    cmd=["sudo ps aux | grep mnexec | grep -v grep | awk {' print $2'} | xargs sudo kill -9"]
    Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)

# Change log level to DEBUG and restart floodlight to make it take effect
def enableDebugLog(cli, restartFloodlight=True):
    if cli.image_type == "linux":
        logFilePath = '/opt/floodlight/floodlight/configuration/logback.xml'
    cli.runCmd("sudo sed -i 's/INFO/DEBUG/' " + logFilePath + " > /tmp/logback.xml")
    if restartFloodlight:
        cli.runCmd("sudo service floodlight stop")
        cli.runCmd("sudo service floodlight start")
        time.sleep(30)

# Has floodlight restart using the Quantum config file for OpenStack.
def floodlightLoadQuantumConfig(cli):
    cli.runCmd('cd /opt/floodlight/floodlight')
    cli.runCmd('touch feature/quantum')
    cli.runCmd('sudo service floodlight stop')
    # we sleep here because the jmx port does not use reuseaddr
    time.sleep(5)
    cli.runCmd('sudo service floodlight start')

# Extract host mac from mininet hosts
def getHostMac(myhosts):
    hosts = {}
    for host in myhosts :
        s = host.cmd("ifconfig")
        for line in iter(s.splitlines()):
            m = re.match(".*HWaddr\s([a-f0-9:]*).*", line)
            if m:
                hosts[m.group(1)] = host.name
                break
    return hosts

def mininetFlushArpCache(cli, host_list):
    """Flush the ARP cache for each mininet host in the list
    cli ... a bigtest cli in mininet mode
    host_list a list of host to query, e.g., [ 'h1', 'h4' ]
    """
    for h in host_list:
        cli.runCmd("%s ip neigh flush all" % h)

def mininetGetArpCache(cli, host_list):
    """Query the ARP cache for each mininet host in host_list  and
    return the parsed result. The result is a dict of dicts: 
        res[host][ip] = mac
    If there's no entry for an IP, i.e., the host queried the IP
    but didn't receive a reply there's no entry for this IP in 
    the dict

    cli ... a bigtest cli in mininet mode
    host_list a list of host to query, e.g., [ 'h1', 'h4' ]
    """
    res = dict()
    for h in host_list:
        arp_str = cli.runCmd("%s ip neigh show" % h)
        arp_str = arp_str.replace('\\r', '').replace('\\n', '\n')
        arp_arr = arp_str.split("\n")
        entries = dict()
        for entry in arp_arr[2:]:
            # first two lines are the command itself
            a = entry.split()
            ip = a[0]
            if (a[3] == "lladdr"):
                # TODO: inlcude STALE entries?
                # Should we actually check the status of the last column?
                mac = a[4]
                entries[ip] = mac
        res[h] = entries
    return res

#
# mininetGetSwitchPorts
#
# Get mapping of all hosts and switches to the "switch port" it is connected
# from the other end of the p2p link
#
# Returned 'switch port' is in the format that can be directly used for
# configuration from bigcli.
#
def mininetGetSwitchPorts(net_dump):
    net_dump = net_dump.replace('\\r', '').replace('\\n', '\n')
    net_dump = net_dump.split("\n")
    switch_ports = dict()

    for entry in net_dump[1:]:
        a = entry.split()
        m = re.search('(\d+)$', a[0])
        if m == None:
            break
        switch = "00:00:00:00:00:00:00:%02x" % (int(m.group(0)))
        for i in range(2, len(a)):
            switch_ports[a[i]] = "%s %s-eth%d" % (switch, a[0], i - 1)
    return switch_ports

def verifyArpCache(expected, actual, ignore=None, msg=None):
    expected = expected.copy()
    actual = actual.copy()
    if ignore is not None:
        for ip in ignore:
            if ip in expected:
                del expected[ip]
            if ip in actual:
                del actual[ip]
    if actual != expected:
        if msg is not None:
            print msg
        print "Expected:"
        pprint.pprint(expected)
        print "Actual:"
        pprint.pprint(actual)
        bigtest.Assert(False)
# Change the MAC and/or IP address of a mininet host
# IP is really IP/mask 
def mininetChangeHostAddress(cli, host_num, vlan=None, mac=None, ip=None):
    if vlan is not None:
        intf = "h%d-eth0.%d" % (host_num, vlan) 
    else:
        intf = "h%d-eth0" % host_num
    if mac is not None:
        log.info("MININET_CMD: h%d ifconfig %s down" % (host_num, intf))
        log.info("MININET_CMD: h%d ifconfig %s hw ether %s" % (host_num, intf, mac))
        log.info("MININET_CMD: h%d ifconfig %s up" % (host_num, intf))
        cli.runCmd("py h%d.setMAC('%s', '%s')" % (host_num, intf, mac))
    if ip is not None:
        log.info("MININET_CMD: h%d ifconfig %s %s/8" % (host_num, intf, ip))
        cli.runCmd("py h%d.setIP('%s', '%s')" % (host_num, intf, ip))

# Config mininet host name as aliases in the controller
def configHostAlias(cli, hosts):
    cli.gotoConfigMode()
    for mac, name in hosts.items():
        cli.runCmd("host %s"%mac)
        cli.runCmd("alias %s"%name)
        cli.runCmd("exit")

def enableMininetHostICMPBroadcast(cli, host):
    cli.runCmd("%s echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts" % host)

def getMininetIfStats(cli, host):
    rxPackets = 0
    rxBytes = 0
    txPackets = 0
    txBytes = 0
    x = cli.runCmd("%s ifconfig" % host)
    pattern = re.compile(r".*RX\s*packets:(\d*).*TX\s*packets:(\d*).*RX\s*bytes:(\d*).*TX\s*bytes:(\d*).*", re.DOTALL)
    m = re.match(pattern, x)
    if m:
        rxPackets, txPackets, rxBytes, txBytes = m.groups("")
        try : 
            txPackets = int(txPackets)
        except ValueError:
            txPackets = 0
        try : 
            rxPackets = int(rxPackets)
        except ValueError:
            rxPackets = 0
        try : 
            txBytes = int(txBytes)
        except ValueError:
            txBytes = 0
        try : 
            rxBytes = int(rxBytes)
        except ValueError:
            rxBytes = 0

    return rxPackets, txPackets, rxBytes, txBytes

# Verify hosta can ping hostb
def verifyPing(cli, hosta, hostb, controller_ipAddr=None,
        ignoreFirstPing=False, count = 1, timeout = 3, threshold=0):

    if ignoreFirstPing:
        cli.runCmd("%s ping -c%d -W%d %s" % (hosta, 1, 3, hostb))
    x = cli.runCmd("%s ping -c%d -W%d %s" % (hosta, count, timeout, hostb))
    m = re.search(r'(\d*)% packet loss', x)
    loss = int(m.group(1))

    result = True
    if (loss > threshold):
        result = False
    bigtest.Assert(result)

# Verify hosta cannot ping hostb
def verifyNoPing(cli, hosta, hostb):
    x = cli.runCmd("%s ping -c1 -w1 %s" % (hosta, hostb))
    bigtest.Assert("100% packet loss" in x)

# Verify hosta can talk to hostb via tcp port
def verifyTcpPort(cli, hosta, hostb, port):
    cli.runCmd("%s nc -l %s &" % (hosta, port))
    x = cli.runCmd("%s nc -w3 -z %s %s; echo $?" % (hostb, hosta, port))
    cli.runCmd("%s pkill nc" % hosta)
    bigtest.Assert('0' in x)

# Verify hosta cannot talk to hostb via tcp port
def verifyNoTcpPort(cli, hosta, hostb, port):
    cli.runCmd("%s nc -l %s &" % (hosta, port))
    x = cli.runCmd("%s nc -w3 -z %s %s; echo $?" % (hostb, hosta, port))
    cli.runCmd("%s pkill nc" % hosta)
    bigtest.Assert('1' in x)

def verifyUdpPort(cli, hosta, hostb, port):
    cli.runCmd("%s rm /tmp/nc-u.out; nc -l -u %s > /tmp/nc-u.out&" % (hosta, port))
    cli.runCmd("%s echo 'connected' | nc -w3 -u %s %s" % (hostb, hosta, port))
    cli.runCmd("%s pkill nc" % hosta)
    x = cli.runCmd("%s cat /tmp/nc-u.out" % hosta)
    bigtest.Assert('connected' in x)

def verifyNoUdpPort(cli, hosta, hostb, port):
    cli.runCmd("%s rm /tmp/nc-u1.out; nc -l -u %s > /tmp/nc-u1.out&" % (hosta, port))
    cli.runCmd("%s echo 'connected' | nc -w3 -u %s %s" % (hostb, hosta, port))
    cli.runCmd("%s pkill nc" % hosta)
    x = cli.runCmd("%s cat /tmp/nc-u1.out" % hosta)
    bigtest.Assert('connected' not in x)

def decodeWildcard(wildcard):
    wildcard_dict = {}
    bit_field_map = { 
        0 : 'inputPort',
        1 : 'dataLayerVirtualLan',
        2 : 'dataLayerSource',
        3 : 'dataLayerDestination',
        4 : 'dataLayerType',
        5 : 'networkProtocol',
        6 : 'transportSource',
        7 : 'transportDestination',
        13 : 'networkSource',
        19 : 'networkDestination',
        20 : 'dataLayerVirtualLanPriorityCodePoint',
        21 : 'networkTypeOfService',
    }        
    for (k,v) in bit_field_map.items():
        if wildcard & (1 << k): 
            wildcard_dict[v] = "*" 
    return wildcard_dict

def restGet(host, path, port=80, obj=False):
    url = "http://%s:%d/rest/v1/%s" % (host, port, path)
    log.info("[rest-get] %s", url)
    x = json.loads(urllib2.urlopen(url).read())
    if obj: return x
    return json.dumps(x, sort_keys=True, indent=2)

def calculateControllerTimeDifference(controller1, controller2, absolute=True):
    """
    Calculate UTC time difference in seconds between 2 controllers

    - Unreliable if response time is slow.
    - This is meant to be a sanity check for NTP. Or to be used when NTP
      is not used.
    """
    ju1 = controller1.restGet("system/clock/utc")
    ju2 = controller2.restGet("system/clock/utc")
    def convertUnicodeKeyToString(ju):
        js = {}
        for i in ju:
            if str(i) in ["tz", "tzinfo", "microsecond"]: continue
            js[str(i)] = ju[i]
        # Make sure all of (year, month, day, hour, minute, second) are there
        # len() is ok because datetime.datetime() fails with unknown kwargs
        bigtest.Assert(len(js) == 6)
        return js
    js1 = convertUnicodeKeyToString(ju1)
    js2 = convertUnicodeKeyToString(ju2)
    t1 = datetime.datetime(**js1)
    t2 = datetime.datetime(**js2)
    difference = (t2 - t1).total_seconds()
    return abs(difference) if absolute else difference

## Cats a file onto a node. The permissions
## are then set to 755.
def putStringAsFileOnNode(cNode, filename, string):
    cli = cNode.cli()
    cli.gotoBashMode()
    console = cli.console()
    console.sendline('cat > ' + str(filename) + '<< EOF')
    for l in string.split("\n"):
        console.sendline(l)
    console.sendline("EOF")
    cli.expectPrompt()
    cli.runCmd("chmod 755 " + str(filename))

## Cats a file onto a node. The permissions
## are then set to 755.
def putStringAsFileOnNode(cNode, filename, string):
    cli = cNode.cli()
    cli.gotoBashMode()
    console = cli.console()
    console.sendline('cat > ' + str(filename) + '<< EOF')
    for l in string.split("\n"):
        console.sendline(l)
    console.sendline("EOF")
    cli.expectPrompt()
    cli.runCmd("chmod 755 " + str(filename))

