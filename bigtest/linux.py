#!/usr/bin/python

import bigtest.node, bigtest.cli 
import logging, pexpect, re, time, os, time, signal
import bigtest

"""
A base Node class that represents any Linux based VM
running in a BigTest environment.
"""
class Node(object):
    def __init__(self):
        pass

    def cli(self, logLevel=logging.INFO):
        return bigtest.cli.Cli(self.console(logLevel), "linux")

    def doSerialLogin(self, console, username, usernamePrompt, passwordPrompt = None):
        p = console.pexpect()
        enteredUsername = False
        for i in xrange(300):
            n, b, a = console.expectReAlt([pexpect.TIMEOUT, usernamePrompt] + ([passwordPrompt] if passwordPrompt else []), timeout=2)
            if n == 0: # timeout
                if not b: # no output received
                    # Send Control-D and Control-M in an attempt to exit from a shell or
                    # other interactive process; don't send Control-C as that tends to
                    # interrupt cleanup routines, leaving stale processes behind
                    console.sendcontrol("d")
                    console.sendcontrol("m")
                elif enteredUsername and passwordPrompt is None:
                    console.sendline('\r\n')
                    break
            elif n == 1: # username prompt
                # Send the username
                console.sendline(username)
                enteredUsername = True
            elif n == 2: # password prompt
                # We're done
                break
            else:
                bigtest.Assert(False)
        else:
            # Cause pexpect to raise a timeout exception if the password prompt is
            # still not seen
            if passwordPrompt != None:
               console.expectRe(passwordPrompt, timeout=0)

    def runSerialCmd(self, cmd, interval=5, timeout=600):
        exception = Exception("Unknown exception in runSerialCmd()")
        timeout_ = time.time() + timeout
        while time.time() < timeout_:
            try:
                console = self.serialConsole()
                username = self.username()
                self.doSerialLogin(console, username, r"\r\n[-.\w]+ login: ")
                cli = bigtest.cli.Cli(console, "linux")
                return cli.runCmd(cmd)
            except Exception, e:
                exception = e
                self.serialConsole_ = None
                bigtest.log.error("runSerialCmd() failed...")
            time.sleep(interval)
        raise exception

    """
    Restarts the linux networking stack
    """
    def restartNetworking(self):
        self.runSerialCmd("sudo /etc/init.d/networking restart")

    def shutdown(self, delay=0):
        cli = self.cli(logging.DEBUG)
        cli.gotoBashMode()
        cli.runCmd("sudo shutdown -h %d" % delay)

    def reboot(self):
        cli = self.cli(logging.DEBUG)
        cli.gotoBashMode()
        cli.runCmd("sudo reboot")

    def getMacAddrFromSerial(self, interface="eth0"):
        output = self.runSerialCmd("ifconfig %s" % interface)
        m = re.search(r"HWaddr ([^\s\n]+)", output, re.M)
        if m:
            return m.group(1).lower()
        else:
            print "Could not find MAC for interface %s"%interface
            bigtest.Assert(0)

    def getIPFromSerial(self, interface="eth0", interval=1, timeout=300):
        timeout_ = time.time() + timeout
        class ForceSerialTimeoutException(Exception):
            pass
        def forceSerialTimeoutHandler(signum, frame):
            raise ForceSerialTimeoutException("ForceSerialTimeoutHandler")
        oldHandler = signal.signal(signal.SIGALRM, forceSerialTimeoutHandler)
        try:
            while time.time() < timeout_:
                signal.alarm(60)
                try:
                    output = self.runSerialCmd("ifconfig %s" % interface)
                    signal.alarm(0)
                    m = re.search(r"inet addr:([^\s]+)", output, re.M)
                    if m:
                        bigtest.log.info("getIPFromSerial() took %.2f seconds"
                            % (time.time() - (timeout_ - timeout)))
                        return m.group(1) 
                    else:
                        print "Waiting for an IP ...", time.time(), timeout_
                        self.serialConsole_ = None
                        time.sleep(interval)
                except ForceSerialTimeoutException:
                    pass
        finally:
            signal.signal(signal.SIGALRM, oldHandler)
        print "Did not get an IP"
        return None

    def dhcpIPReleaseRenew(self, interface="eth0"):
        self.runSerialCmd("sudo dhclient -r %s; sudo dhclient -4 %s" % (interface, interface))

    def getIfConfigStrFromSerial(self):
        return self.runSerialCmd("ifconfig")

    def getIpForMac(self, mac):
        nextIp = False
        getIp = False
        ifConfigStr = self.ifConfigStr()
        if ifConfigStr is None:
            return None
        for item in ifConfigStr.split():
            if getIp:
                if item[:5] == "addr:":
                    return item[5:]
                else:
                    return None
            if nextIp:
                if item.lower() == "inet":
                    getIp = True
                else:
                    return None
            if item.lower() == mac:
                nextIp = True
        return None

    def getIfConfigStrFromSerial(self):
        return self.runSerialCmd("ifconfig")
   
    def getIpForMac(self, mac):
        nextIp = False
        getIp = False
        ifConfigStr = self.ifConfigStr()
        if ifConfigStr is None:
            return None
        for item in ifConfigStr.split():
            if getIp:
                if item[:5] == "addr:":
                    return item[5:]
                else:
                    return None
            if nextIp:
                if item.lower() == "inet":
                    getIp = True
                else:
                    return None
            if item.lower() == mac:
                nextIp = True
        return None

    def waitForIpAddress(self, interface="eth0"):
        self.setIpAddress(self.getIPFromSerial(interface))
        self.setIfConfigStr(self.getIfConfigStrFromSerial())

    def mountNas(self, server, share, mount):
        cli = self.cli()
        # check if already mounted
        pat = re.compile(r"%s:%s on ([^\s]+)" % (re.escape(server),
                                                 re.escape(share)))
        for line in cli.runCmd("mount").split("\n"):
            m = pat.search(line)
            if m:
                return m.group(1)
        cli.runCmd("sudo mkdir -p %s" % mount)
        cli.runCmd("sudo sh -c 'echo \"%s:%s %s nfs rw 0 0\" >> /etc/fstab'" \
                    % (server, share, mount))
        cli.runCmd("sudo mount -a")
        return mount

    def unmountNas(self, mount):
        self.cli().runCmd("sudo unmount %s" % mount)

    # OVS related commands
    def waitForTunnelIpAddress(self, interface="ovs-br0"):
        self.runSerialCmd("sudo dhclient ovs-br0")
        self.setTunnelIpAddress(self.getIPFromSerial(interface))

    def runOVSCmd(self, cmd):
        cli = self.cli()
        return cli.runCmd("sudo ovs-vsctl %s" % cmd)

    def showOVS(self):
        return self.runOVSCmd("show")

    def setupOVS(self, dpid, controller, tunnelIp):
        bridge = "ovs-br0" # assume ovs-br0 already exists
        self.runOVSCmd("--no-wait set-fail-mode %s secure" % bridge)
        self.runOVSCmd("set bridge %s other-config:tunnel-ip=%s" % \
                       (bridge, tunnelIp))
        self.runOVSCmd("set bridge %s other-config:datapath-id=%s" % \
                       (bridge, dpid))
        self.runOVSCmd("set-controller %s tcp:%s:6633" % (bridge, controller))
 
    # bridge related commands
    # Using a stock OVS as bridge 
    def runBridgeCmd(self, cmd):
        cli = self.cli()
        return cli.runCmd("sudo ovs-vsctl --no-wait %s" % cmd)

    def showBridge(self):
        return self.runBridgeCmd("show")

    def setupBridge(self, interfaces=[], stp=True):
        bridge = "br0"
        self.runBridgeCmd("add-br %s" % bridge)
        if stp:
            self.runBridgeCmd("set bridge  %s stp=true" % bridge)
        for eth in interfaces:
            self.runBridgeCmd("add-port %s %s" % (bridge, eth))

        cli = self.cli()
        cli.runCmd("sudo ifconfig %s up" % bridge)
        for eth in interfaces:
            cli.runCmd("sudo ifconfig %s up" % eth)

    def enableOFonBridge(self, controller, dpid=None):
        bridge = "br0"
        if dpid is not None:
            dpid = dpid.replace(":", "")
            dpid = dpid.rjust(16, "0")
            self.runBridgeCmd("set bridge %s other-config:datapath-id=%s" % (bridge, dpid))
        self.runBridgeCmd("set bridge  %s stp=false" % bridge)
        self.runBridgeCmd("set-controller %s tcp:%s" % (bridge,controller))
        self.runBridgeCmd("set-fail-mode %s secure" % bridge)

    def disableOFonBridge(self, stp=True):
        bridge = "br0"
        self.runBridgeCmd("del-controller %s" % bridge)
        self.runBridgeCmd("del-fail-mode %s" % bridge)
        if stp:
            self.runBridgeCmd("set bridge  %s stp=true" % bridge)



    # functions that write BigTest metadata about the node
    def setIfConfigStr(self, ifConfigStr):
        self._writeKeyValueToStateDir("ifconfig", ifConfigStr)

    def ifConfigStr(self):
        return self._readKeyValueFromStateDir("ifconfig")

    def setSerialCounter(self, serialCounter):
        self._writeKeyValueToStateDir("serialCounter", serialCounter)

    def serialCounter(self):
        ret = self._readKeyValueFromStateDir("serialCounter")
        return int(ret) if ret else None

    def setMonitorCounter(self, monitorCounter):
        self._writeKeyValueToStateDir("monitorCounter", monitorCounter)

    def monitorCounter(self):
        ret = self._readKeyValueFromStateDir("monitorCounter")
        return int(ret) if ret else None

    def setCmdline(self, cmdline):
        self._writeKeyValueToStateDir("cmdline", cmdline)

    def cmdline(self):
        return self._readKeyValueFromStateDir("cmdline")

    def setTunnelIpAddress(self, ipAddress):
        self._writeKeyValueToStateDir("tunnelipaddr", ipAddress)

    def tunnelIpAddress(self):
        return self._readKeyValueFromStateDir("tunnelipaddr")
   
    def setCreatedVms(self, vms):
        self._writeKeyValueToStateDir("vms", ",".join(vms))

    def createdVms(self):
        ret = self._readKeyValueFromStateDir("vms")
        return ret.split(",") if ret else []

    def setDefaultDatastore(self, datastore):
        self._writeKeyValueToStateDir("datastore", datastore)

    def defaultDatastore(self):
        return self._readKeyValueFromStateDir("datastore")

