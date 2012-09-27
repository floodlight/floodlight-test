#!/usr/bin/python

import atexit
import httplib
import inspect
import json
import logging
import optparse
import os
import re
import sys
import time
import traceback
import types
import urllib

import bigtest
import bigtest.cli
import bigtest.kvm
import bigtest.linux
import bigtest.node
import bigtest.tc
import pexpect
import util.httpsession
from util import *

try:
    # Override mininet log functions before importing anything else in mininet!
    import mininet.log
    def mnlog(level):
        def dolog(msg, *args, **kargs):
            for l in msg.split("\n"):
                bigtest.log.log(level, "mininet: " + l, *args, **kargs)
        return dolog
    mininet.log.debug = mnlog(logging.INFO)
    mininet.log.info = mnlog(logging.INFO)
    mininet.log.output = mnlog(logging.INFO)
    mininet.log.warn = mnlog(logging.WARN)
    mininet.log.error = mnlog(logging.ERROR)
    import mininet.node, mininet.util
except ImportError:
    pass


log = bigtest.log
def setLog(name, level=None):
    global log
    bigtest.setLog(name, level)
    log = bigtest.log


getNode = bigtest.node.getNode


class Node(bigtest.linux.Node):
    def __init__(self):
        self.webconn_ = None
        self.websession_ = None
        self.logfiles = []

    def cli(self, logLevel=logging.INFO):
        return bigtest.cli.Cli(self.console(logLevel), self.imageType())

    def mininet(self, topo, start=True):
        def cleanup():
            # Clean up leftovers from previous tests
            bigtest.sudo("killall ofdatapath 2>/dev/null; killall ofprotocol"
                         " 2>/dev/null; true", trace=False)
        cleanup()
        atexit.register(cleanup)
        # Disable IPv6 to avoid discovery chatter and work around Java bug 7075227
        bigtest.sudo("sysctl -q -w net.ipv6.conf.all.disable_ipv6=1", trace=False)
        def remoteController(name):
            return mininet.node.RemoteController(name, defaultIP=self.ipAddress())
        net = mininet.net.Mininet(topo=topo,
                                  switch=mininet.node.UserSwitch,
                                  controller=remoteController)
        if start:
            net.start()
            self.waitForNet(net)
        return net

    def waitForSwitches(self, dpids):
        log.info("Waiting for switches to connect to controller")
        for i in range(100):
            if self.imageType() == "linux":
                switches = self.restGet("core/controller/switches/json", "dpid")
                x = [d for d in dpids if d not in switches or not switches[d]["dpid"]]
            if not x:
                log.info("switches connected to controller")
                return i 
            log.info("still waiting for switches: " + ", ".join(x))
            time.sleep(1)
        bigtest.Assert(False)

    def waitForSwitchCluster(self, dpids, clix=None):
        self.waitForSwitches(dpids)
        # Set the time long enough (100s) to catch multiple lldp intervals
        log.info("WaitFSC: DPIDs: %s " % (dpids))
        dpids = sorted(dpids)
        starttime = time.time()
        for i in range(300):
            if self.imageType() == "linux":
                clusters = self.restGet("topology/switchclusters/json")
            # Mininet sometimes generates spurious switchids
            # We need to check if there is a cluster that has all the given
            # dpids
            for cid in clusters:
                log.info("CL: %s dpid: %s" % (clusters[cid], dpids))
                c = clusters[cid]
                count = 0
                for s in dpids:
                   if s in c:
                      count = count + 1
                if (count == len(dpids)):
                    # Cluster with all the given dpids is formed
                    dt = time.time() - starttime
                    log.info("Switch cluster set up with switches %s. It took %.2f seconds" %
                        (clusters[cid], dt))
                    return
            log.info("Waiting for a cluster with all the given switches ...")
            time.sleep(1)
        bigtest.Assert(False)

    def waitForLinks(self, links, clix=None):
        for i in range(60):
            clinks = self.restGet("topology/links/json")

            count = 0
            for link in links:
                for clink in clinks:
                    match = True
                    for k,v in link.iteritems():
                        if (k not in clink or
                            clink[k] != v):
                            match = False
                            break
                    
                    if match:
                        count += 1
                        break
            
            if count >= len(links):
                return

            log.info("Waiting for links (%d/%d found)" % (count, len(links)))
            time.sleep(1)

        log.error("Links never appeared")
        bigtest.Assert(False)

    def waitForNet(self, net):
        dpids = [s.dpid for s in net.switches]
        self.waitForSwitches(dpids)

    def restGet(self, path, keyColumn=None, verbose=True):
        """Get a URL from the node's REST interface and return the
        parsed JSON result.  If keyColumn is set, convert the result from
        a list to a dict indexed by the keyColumn value."""
        if self.imageType() == "linux":
            url = "http://%s:8080/wm/%s" % (self.ipAddress(), path)
        log.info("rest get from %s url %s:", self.name(), url)
        x = json.loads(urllib.urlopen(url).read())
        p0 = path if len(path) < 20 else "..." + path[-20:]
        for line in json.dumps(x, sort_keys=True, indent=2).split("\n"):
            log.log(logging.INFO if verbose else logging.DEBUG,
                    "%s:%s: %s", self.name(), p0, line)
        if keyColumn is not None:
            x = dict([l[keyColumn], l] for l in x)
        return x

    def urlGet(self, path, follow_redirects=True):
        """Gets URL from node without creating a session,
        returns the tuple (status, headers, data)"""

        if not path: path = '/'
        if path[0] != '/': path = '/' + path
        if not self.webconn_:
            self.webconn_ = httplib.HTTPSConnection(self.ipAddress())

        first_request = True
        status, headers, data = 0, {}, ''
        while first_request or (follow_redirects and status in [301, 302,]):
            if status in [301, 302,]:
                path = '/'.join([''] + headers['location'].split('/')[3:])
                log.info('GET ui-url redirected ===>>>')

            log.info('GET url from https://%s%s' % (self.ipAddress(), path))
            first_request = False
            self.webconn_.request('GET', path)
            resp = self.webconn_.getresponse()
            status, headers, data = resp.status, dict(resp.getheaders()), resp.read()
            log.info('GET url response status: %d' % status)
        return status, headers, data

    def urlPut(self, path, data):
        if not path: path = '/'
        # if there is no first / add it
        if path[0] != '/': path = '/' + path    
        if self.imageType() == "linux":
            port = 8080
        if not self.webconn_:
            self.webconn_ = httplib.HTTPConnection(self.ipAddress(), port)
        log.info('PUT URL to http://%s:%s%s' % (self.ipAddress(), port, path))
        log.info('PUT DATA: %s' % str(data))
        self.webconn_.request('PUT', path, data)
        resp = self.webconn_.getresponse()
        status, headers, data = resp.status, dict(resp.getheaders()), resp.read()
        log.info('PUT URL response status: %d' % status)
        log.info('PUT URL reponse data: %s' % data)
        return status, headers, data

    def urlPost(self, path, data):
        """Posts data the node with the given path"""
        if not path: path = '/'
        if path[0] != '/': path = '/' + path
        #data = urllib.urlencode(data)
        if self.imageType() == "linux":
            port = 8080
        if not self.webconn_:
            self.webconn_ = httplib.HTTPConnection(self.ipAddress(), port)
        log.info('POST URL to http://%s:%s%s' % (self.ipAddress(), port, path))
        self.webconn_.request('POST', path, data)
        resp = self.webconn_.getresponse()
        status, headers, data = resp.status, dict(resp.getheaders()), resp.read()
        log.info('POST URL response status: %d' % status)
        log.info('POST URL reponse data: %s' % data)
        return status, headers, data

    def serialLogin(self, logLevel=logging.INFO):
        console = self.serialConsole(logLevel)
        log.info("=== Logging into node %s on serial console", self.name())
        username = self.username()
        password = self.password()
        image_type = self.imageType()

        if password != '':
            self.doSerialLogin(console, username, r"\r\n[-.\w]+ login: ", r"\nPassword: ")
            console.sendline(password)
        else:
            self.doSerialLogin(console, username, r"\r\n[-.\w]+ login: ")
        if image_type == "linux":
            console.expectRe(r"%s" % re.escape(self.username()))
        log.info("=== Finished logging into node %s on serial console", self.name())

    def serialSetupLinux(self, logLevel=logging.INFO):
        if self.image_type != "linux":
            return

        console = self.serialConsole(logLevel)
        log.info("=== Setting up node %s on serial console", self.name())
        ipAddress = self.ipAddress()
        username = self.username()
        password = self.password()
        if password != '':
            self.doSerialLogin(console, username, r"\r\n[-.\w]+ login: ", r"\nPassword: ")
            console.sendline(password)
        else:
            self.doSerialLogin(console, username, r"\r\n[-.\w]+ login: ")
        console.expectRe(r".*%s@.*\$" % re.escape(username))
        log.info("=== Configuring IP address on eth0")
        console.sendline("sudo ifconfig eth0 %s/8" % (self.ipAddress()))
        log.info("=== Finished setting up node %s on serial console", self.name())

    def setVmType(self, iType):
        self.image_type = iType

    def getVmType(self):
        return self.image_type

    def getIPFromSerial(self, logLevel=logging.DEBUG):
        self.serialLogin(logLevel)
        cli = bigtest.cli.Cli(self.serialConsole(logLevel))
        cli.gotoBashMode()
        output = cli.runCmd("ifconfig eth0")
        m = re.search(r"inet addr:([^\s]+)", output, re.M)
        bigtest.Assert(m and m.group(1) != "")
        return m.group(1)

class GenericVmNode(Node):
    def __init__(self):
        Node.__init__(self)
        self.logfilePositions_ = {}
        if self.imageType() == "linux":
            self.logfiles.append("/opt/floodlight/floodlight/log/floodlight.log")
            self.logfiles.append("/var/log/syslog")

    def preTest(self):
        log.info("=== Setting up %s", self.name())
        cli = self.cli(logging.DEBUG)
        self.updateTime(cli)

    def updateTime (self, cli):
        if self.imageType() == "linux":
            return

    def postTest(self, success):
        return

    def reboot(self):
        cli = self.cli(logging.DEBUG)
        cli.gotoBashMode()
        cli.runCmd("sudo reboot")


class KvmNode(bigtest.node.KvmNode, GenericVmNode):
    def __init__(self, name):
        bigtest.node.KvmNode.__init__(self, name)
        GenericVmNode.__init__(self)

    def saveInitialSnapshot(self, logLevel=logging.INFO):
        log.info("=== Saving initial snapshot on node %s", self.name())
        if self.imageMode() == "snapshot":
            self.saveSnapshot("initial", logLevel)
        elif self.imageMode() == "persistent":
            self.shutdown(waitForState=True)
            bigtest.run("rm -f %s.initial" % self.image())
            bigtest.run("cp %s %s.initial" % (self.image(), self.image()))
            self.powerOn()
        log.info("=== Finished saving initial snapshot on node %s", self.name())

    def revertToInitialSnapshot(self, logLevel=logging.INFO):
        log.info("=== Reverting to initial snapshot on node %s", self.name())
        if self.imageMode() == "snapshot":
            self.revertToSnapshot("initial", logLevel)
            self.serialLogin(logLevel)
            cli = bigtest.cli.Cli(self.serialConsole(logLevel), self.imageType())
            cli.runCmd("sudo hwclock -s -u")
        elif self.imageMode() == "persistent":
            self.powerOff()
            bigtest.run("rm -f %s" % self.image())
            bigtest.run("cp %s.initial %s" % (self.image(), self.image()))
            self.powerOn()
        log.info("=== Finished reverting to initial snapshot on node %s", self.name())

    def shutdown(self, delay=0, waitForState=False):
        cli = self.cli(logging.DEBUG)
        cli.gotoBashMode()
        cli.runCmd("sudo shutdown -h %d" % delay)
        if waitForState:
            bigtest.waitForProcessToStop(self.pid())

class Test(object):
    def __init__(self, name=None, nodeNames=["node1"], fetchLogs=True, extraLogs=[]):
        op = optparse.OptionParser()
        # just get options from original command line
        op.add_option("--nodes", help="Override default (%s)" % nodeNames)
        opts, args = op.parse_args()
        if opts.nodes:
            nodeNames = opts.nodes.split(",")

        self.name_ = name
        self.reportStatus_ = True
        for x in [f[1] for f in inspect.stack()]:
            if not x.endswith("/bigtest/controller.py"):
                if self.name_ is None:
                    self.name_ = os.path.basename(x)[:-3]
            if x.endswith("/unittest/suite.py"):
                self.reportStatus_ = False
        self.startTime_ = time.time()
        setLog(self.name_)
        self.nodes_ = []
        for nodeName in nodeNames:
            node = bigtest.node.getNode(nodeName)
            if not node:
                raise Exception("Node %s not found" % nodeName)
            for f in extraLogs:
                node.logfiles.append(f)
            if not fetchLogs:
                node.logfiles = []
            self.nodes_.append(node)
            # Add a method called nodeName that returns the node object
            setattr(self, nodeName, types.MethodType(lambda s, n=node: n, self, self.__class__))
        for node in self.nodes_:
            node.preTest()
        log.info("=== Running test %s", self.name_)
        sys.excepthook = self.excepthook
        self.failed = False

    def endTest(self):
        if self.failed:
            return
        duration = time.time() - self.startTime_
        self.cleanup(True)
        if self.reportStatus_:
            log.info("=== Test %s completed normally (%d sec)", self.name_, duration)

    def excepthook(self, x, y, z):
        duration = time.time() - self.startTime_
        sys.__excepthook__(x, y, z)
        self.cleanup(False)
        if self.reportStatus_:
            log.info("=== Test %s failed (%d sec)", self.name_, duration)
        self.failed = True

    def cleanup(self, success):
        sys.excepthook = sys.__excepthook__
        for node in self.nodes_:
            try:
                node.postTest(success)
            except Exception, e:
                log.error("Exception hit during cleanup, bypassing:\n%s\n\n" %
                    traceback.format_exc())
                pass

    # map self.node1()... self.nodeN() to nodes provided
    def mapNodes(self):
        for i, node in enumerate(self.nodes_):
            f = types.MethodType(lambda s, n=node: n, self, self.__class__)
            setattr(self, "node%d" % (i + 1), f)
            log.info("=== node%d() mapped to %s" % (i + 1, node.name()))


class TwoNodeTest(Test):
    def __init__(self, name=None, nodeNames=["node1", "node2"], fetchLogs=True, extraLogs=[]):
        Test.__init__(self, name, nodeNames, fetchLogs, extraLogs)
        bigtest.Assert(len(self.nodes_) == 2)
        self.mapNodes()


class ThreeNodeTest(Test):
    def __init__(self, name=None, nodeNames=["node1", "node2", "node3"], fetchLogs=True, extraLogs=[]):
        Test.__init__(self, name, nodeNames, fetchLogs, extraLogs)
        bigtest.Assert(len(self.nodes_) == 3)
        self.mapNodes()

