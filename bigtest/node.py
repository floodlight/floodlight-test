#!/usr/bin/python

import bigtest
import json, logging, os, pwd, StringIO, tempfile, time, re
import pexpect
import os

defaultTimeout = 180

def getNode(name):
    f = os.path.join(bigtest.confdir(), "node-%s" % name, "class")
    c = None
    if os.path.exists(f):
        c = open(f).read().strip()
    if not c:
        return
    if "." in c:
        k = c[:c.index(".")]
        m = __import__(c[:c.rindex(".")])
        e = {k : m,}
    else:
        c = {}
    cls = eval(c, e)
    return cls(name)


def getAllNodes():
    nodes = []
    for name in sorted([n[5:] for n in os.listdir(bigtest.confdir())
                        if n.startswith("node-")]):
        nodes.append(getNode(name))
    return nodes

class Node(object):
    def __init__(self, name):
        # name is a generic name that indicates its role, but not its type (local kvm or others)
        # or location (domain name or IP address)
        self.name_ = name
        self.statedir_ = os.path.join(bigtest.confdir(), "node-%s" % name)

    def name(self):
        return self.name_

    def start(self):
        bigtest.run(["rm", "-rf", self.statedir_])
        bigtest.run(["mkdir", "-p", self.statedir_])
        self._writeKeyValueToStateDir("class",
            "%s.%s\n" % (self.__class__.__module__, self.__class__.__name__))

    def stop(self):
        bigtest.run(["rm", "-rf", self.statedir_])

    def serialConsole(self, logLevel):
        bigtest.Assert(False, "not implemented")

    #
    # get_shell_term
    #
    # Get term type to use for consoles. By default, use 'dumb'. If screen
    # sessions are to be used (for pesistent sessions), use 'screen'.
    #
    def get_shell_term (self):
        term = "dumb"
        use_screen = os.environ.has_key("BIGTEST_TERM_SCREEN") or \
                     os.path.isfile("/tmp/BIGTEST_TERM_SCREEN")
        if use_screen:
            term = "screen"
        return term

    def sshConsole(self, logLevel=logging.INFO, args=[], interval=10, timeout=300):
        env = os.environ.copy()
        env["TERM"] = self.get_shell_term()
        timeout_ = time.time() + timeout
        while time.time() < timeout_:
            try:
                pex = pexpect.spawn("ssh",
                                    ["-o", "UserKnownHostsFile /dev/null",
                                     "-o", "StrictHostKeyChecking no",
                                     "-A", "-X",
                                     "%s@%s" % (self.username(), self.ipAddress())] + args,
                                    env=env, maxread=20000, timeout=defaultTimeout)
                console = bigtest.Console(self.name_, pex, logLevel)
                if self.password() != '':
                    pex.expect("[Pp]assword: ")
                    pex.sendline(self.password())
                return console
            except Exception, e:
                print e
            time.sleep(interval)
        bigtest.Assert(False)

    def scpTo(self, fromPath, toPath):
        # This is not used anywhere for now
        # Suggestion: Add more error checkings before using it
        env = os.environ.copy()
        env["TERM"] = "dumb"
        print "+ scp %s %s@%s:%s" \
            % (fromPath, self.username(), self.ipAddress(), toPath)
        pex = pexpect.spawn("scp", [
            "-o", "UserKnownHostsFile /dev/null",
            "-o", "StrictHostKeyChecking no",
            fromPath,
            "%s@%s:%s" % (self.username(), self.ipAddress(), toPath)],
            env=env, maxread=20000, timeout=defaultTimeout)
        if self.password() != '':
            pex.expect("[Pp]assword: ")
            pex.sendline(self.password())
        a = pex.expect("100%")
        pex.close()

    def console(self, logLevel=logging.INFO):
        return self.sshConsole(logLevel)

    def saveSnapshot(self, name, logLevel):
        bigtest.Assert(False, "not implemented")

    def revertToSnapshot(self, name, logLevel):
        bigtest.Assert(False, "not implemented")

    def _writeKeyValueToStateDir(self, key, value):
        bigtest.Assert(value is not None)
        f = open(os.path.join(self.statedir_, key), "w")
        f.write("%s\n" % str(value).strip())

    def _readKeyValueFromStateDir(self, key):
        f = os.path.join(self.statedir_, key)
        if os.path.exists(f):
            return open(f).read().strip()
        return None

    def setMacAddress(self, macAddress):
        self._writeKeyValueToStateDir("macaddr", macAddress)

    def macAddress(self):
        return self._readKeyValueFromStateDir("macaddr")

    def setIpAddress(self, ipAddress):
        self._writeKeyValueToStateDir("ipaddr", ipAddress)

    def ipAddress(self):
        return self._readKeyValueFromStateDir("ipaddr")

    def setNetmask(self, netmask):
        self._writeKeyValueToStateDir("netmask", netmask)

    def netmask(self):
        return self._readKeyValueFromStateDir("netmask")

    def setGateway(self, gateway):
        self._writeKeyValueToStateDir("gateway", gateway)

    def gateway(self):
        return self._readKeyValueFromStateDir("gateway")

    def setDns(self, dns):
        self._writeKeyValueToStateDir("dns", dns)

    def dns(self):
        return self._readKeyValueFromStateDir("dns")

    def setDomain(self, domain):
        self._writeKeyValueToStateDir("domain", domain)

    def domain(self):
        return self._readKeyValueFromStateDir("domain")

    def setUsername(self, username):
        self._writeKeyValueToStateDir("username", username)

    def username(self):
        return self._readKeyValueFromStateDir("username")

    def setPassword(self, password):
        self._writeKeyValueToStateDir("password", password)

    def password(self):
        return self._readKeyValueFromStateDir("password")

    def setNtp(self, ntp):
        self._writeKeyValueToStateDir("ntp", ntp)

    def ntp(self):
        return self._readKeyValueFromStateDir("ntp")

    def setImageType(self, image_type):
        self._writeKeyValueToStateDir("imagetype", image_type)

    def imageType(self):
        return self._readKeyValueFromStateDir("imagetype")

    def dump(self):
        bridges, intfBridges = bigtest.bridgeInfo()
        s = StringIO.StringIO()
        bridge = intfBridges.get(self.name_)
        if bridge:
            s.write("bridge: %s\n" % bridge)
        s.write("ipaddr: %s\n" % self.ipAddress())
        s.write("image type: %s\n" % self.imageType())
        return s

    def listStates(self):
        return os.listdir(self.statedir_)

    def getAllStates(self):
        return dict([(s, self._readKeyValueFromStateDir(s)) for s in self.listStates()])

    def setStates(self, stateMap):
        for s, v in stateMap.iteritems():
            self._writeKeyValueToStateDir(s, v)


class KvmNode(Node):
    def __init__(self, name):
        Node.__init__(self, name)
        self.serialConsole_ = None

    def vmArgs(self):
        ret = self._readKeyValueFromStateDir("vmargs")
        return json.loads(ret) if ret else None

    def setVmArgs(self, args):
        self._writeKeyValueToStateDir("vmargs", json.dumps(args))

    def image(self):
        return self._readKeyValueFromStateDir("image")

    def setImage(self, image):
        self._writeKeyValueToStateDir("image", image)

    def imageMode(self):
        return self._readKeyValueFromStateDir("imagemode")

    def setImageMode(self, mode):
        self._writeKeyValueToStateDir("imagemode", mode)

    def controlBridge(self):
        return self._readKeyValueFromStateDir("controlbr")

    def setControlBridge(self, controlbr):
        self._writeKeyValueToStateDir("controlbr", controlbr)

    def vncPort(self):
        ret = self._readKeyValueFromStateDir("vncport")
        return int(ret) if ret else None

    def setVncPort(self, vncport):
        self._writeKeyValueToStateDir("vncport", vncport)

    def register(self, ipAddress, username, password, image_type):
        Node.start(self)
        self.setIpAddress(ipAddress)
        self.setUsername(username)
        self.setPassword(password)
        self.setImageType(image_type)

    def start(self, args, ipAddress, username, password, controlBridge,
              image_type="linux"):
        Node.start(self)
        self.setIpAddress(ipAddress)
        self.setUsername(username)
        self.setPassword(password)
        self.setImageType(image_type)
        self.setVmArgs(args)
        bigtest.Assert("-drive" in args)
        for arg in args[args.index("-drive") + 1].split(","):
            if arg.startswith("file="):
                self.setImage(arg[5:])
                break
        if "-snapshot" in args:
            self.setImageMode("snapshot")
        else:
            self.setImageMode("persistent")
        self.setControlBridge(controlBridge)
        self.setVncPort(self.generateVncPort())
        self.powerOn()

    def stop(self):
        self.powerOff()
        Node.stop(self)

    def pid(self):
        return bigtest.readPidFile(os.path.join(self.statedir_, "pid"))

    def serialConsole(self, logLevel=logging.INFO):
        if not self.serialConsole_:
            pex = pexpect.spawn("socat", ["stdio,raw,echo=0",
                                          "unix-connect:" + os.path.join(self.statedir_, "console")],
                                maxread=20000, timeout=defaultTimeout)
            self.serialConsole_ = bigtest.Console(self.name_, pex, logLevel)
        return self.serialConsole_

    def monitorCmds(self, cmds, logLevel=logging.INFO):
        pex = pexpect.spawn("socat", ["stdio,raw,echo=0",
                                      "unix-connect:" + os.path.join(self.statedir_, "monitor")],
                            maxread=20000, timeout=defaultTimeout)
        c = bigtest.Console(self.name_, pex, logLevel)
        c.expectRe(r"\r\n")
        c.sendline(json.dumps({"execute": "qmp_capabilities"}))
        c.expectRe(r"\r\n")
        results = []
        for cmd in cmds:
            c.sendline(json.dumps({"execute": "human-monitor-command", "arguments":
                                       {"command-line": cmd}}))
            while True:
                x = json.loads(c.expectRe(r"\r\n")[0])
                if "return" in x:
                    results.append(x["return"])
                    break
        return results

    def saveSnapshot(self, name, logLevel=logging.INFO):
        self.monitorCmds(["savevm %s" % name], logLevel)

    def revertToSnapshot(self, name, logLevel=logging.INFO):
        self.monitorCmds(["stop", "system_reset", "loadvm %s" % name, "cont"], logLevel)

    def reset(self, logLevel=logging.INFO):
        self.monitorCmds(["system_reset"], logLevel)

    def powerOn(self):
        user = pwd.getpwuid(os.getuid())[0]
        tf, tfn = tempfile.mkstemp()
        os.fchmod(tf, 0755)
        os.write(tf, "#!/bin/sh\nifconfig $1 up\n")
        os.write(tf, "brctl addif %s $1\n" % self.controlBridge())
        os.close(tf)
        try:
            bigtest.sudo(
                ["kvm",
                 "-runas", user,
                 "-daemonize",
                 "-nographic",
                 "-pidfile", os.path.join(self.statedir_, "pid"),
                 "-vnc", ":%d" % (self.vncPort()-5900),
                 "-qmp", "unix:%s,server,nowait" % os.path.join(self.statedir_, "monitor"),
                 "-serial", "unix:%s,server,nowait" % os.path.join(self.statedir_, "console"),
                 "-net", "tap,ifname=%s,script=%s,downscript=no" % (self.name(), tfn)]
                + list(self.vmArgs()))
        finally:
            for fn in ["pid", "monitor", "console"]:
                p = os.path.join(self.statedir_, fn)
                if os.path.exists(p):
                    bigtest.sudo(["chown", user, p])
        os.unlink(tfn)

    def powerOff(self):
        bigtest.tryToStopProcess(self.pid())
        self.serialConsole_ = None

    def connectNic(self, nic="tap.0", logLevel=logging.INFO):
        self.monitorCmds(["set_link %s on" % nic], logLevel)

    def disconnectNic(self, nic="tap.0", logLevel=logging.INFO):
        self.monitorCmds(["set_link %s off" % nic], logLevel)

    def dump(self):
        s = Node.dump(self)
        pid = self.pid()
        if not os.path.exists("/proc/%s/cmdline" % pid):
            pid = "(not running)"
        s.write("pid: %s\n" % pid)
        return s

    def generateVncPort(self):
        m = re.search('^node(\d+)$', self.name())
        if m:
            return 32000 + int(m.group(1))
        else:
            return 33000 + (self.name().__hash__() % 1000)

class RemoteKvmNode(Node):
    def __init__(self, name):
        Node.__init__(self, name)
        self.serialConsole_ = None

    def setKvmNode(self, kvmNode):
        self._writeKeyValueToStateDir("kvmnode", kvmNode)

    def kvmNode(self):
        return self._readKeyValueFromStateDir("kvmnode")

    def setVmname(self, vmname):
        self._writeKeyValueToStateDir("vmname", vmname)

    def vmname(self):
        return self._readKeyValueFromStateDir("vmname")

    def setSerialPort(self, serialPort):
        self._writeKeyValueToStateDir("serialport", serialPort)

    def serialPort(self):
        return self._readKeyValueFromStateDir("serialport")

    def setMonitorPort(self, monitorPort):
        self._writeKeyValueToStateDir("monitorport", monitorPort)

    def monitorPort(self):
        return self._readKeyValueFromStateDir("monitorport")

    def serialConsole(self, logLevel=logging.INFO):
        if not self.serialConsole_:
            pex = pexpect.spawn("telnet", self.serialPort().split(":"),
                                maxread=20000, timeout=defaultTimeout)
            self.serialConsole_ = bigtest.Console(self.name_, pex, logLevel)
        return self.serialConsole_

    def start(self, kvmNode, vmname, vmSpec, datastore, wait_for_migration=False):
        Node.start(self)
        self.setKvmNode(kvmNode)
        self.setVmname(vmname)
        kvm = getNode(kvmNode)
        vm, serial = kvm.startVm(
                vmname, vmSpec, datastore,
                wait_for_migration=wait_for_migration)
        self.setSerialPort("%s:%s" % (kvm.ipAddress(), serial))
        self.setMonitorPort("%s:%s" % (kvm.ipAddress(), serial + 1000)) #FIXME: need to return monitor port from kvm.startVm
        return vm, serial


class LocalNode(Node):
    def start(self, consoleCommand, ipAddress):
        Node.start(self)
        self.setConsoleCommand(consoleCommand)
        if ipAddress:
            self.setIpAddress(ipAddress)
            bigtest.sudo("ip link del %s 2>/dev/null || :" % self.name_)
            bigtest.sudo(["ip", "link", "add", "name", "%s" % self.name_,
                         "type", "veth", "peer", "name", "%s-s" % self.name_])
            bigtest.sudo(["ifconfig", "%s" % self.name_, "up"])
            bigtest.sudo(["ifconfig", "%s-s" % self.name_, ipAddress,
                         "netmask", "255.255.255.0", "up"])
        else:
            self.setIpAddress("127.0.0.1")

    def stop(self):
        if self.ipAddress() != "127.0.0.1":
            bigtest.sudo("ip link del %s 2>/dev/null || :" % self.name_)
        Node.stop(self)

    def console(self, logLevel=logging.INFO, args=[]):
        pex = pexpect.spawn("bash", ["-c", self.consoleCommand()],
                            maxread=20000, timeout=defaultTimeout)
        return bigtest.Console(self.name_, pex, logLevel)

    def sshConsole(self, logLevel=logging.INFO):
        bigtest.Assert(False, "not implemented")

    def setConsoleCommand(self, command):
        c = bigtest.run(["which", command], captureStdout=True)
        self._writeKeyValueToStateDir("command", c)

    def consoleCommand(self):
        return self._readKeyValueFromStateDir("command")

    def dump(self):
        s = Node.dump(self)
        s.write("console command: %s\n" % self.consoleCommand())
        return s
