#!/usr/bin/python

import bigtest
import os, pwd, StringIO


def getTestCluster(name):
    f = os.path.join(bigtest.confdir(), "tc-%s" % name, "class")
    c = None
    if os.path.exists(f):
        c = file(f).read().strip()
    if not c:
        return
    if "." in c:
        __import__(c[:c.rindex(".")])
    cls = eval(c)
    return cls(name)


def getAllTestClusters():
    tcs = []
    for name in sorted([n[3:] for n in os.listdir(bigtest.confdir())
                        if n.startswith("tc-")]):
        tcs.append(TestCluster(name))
    return tcs


class TestCluster(object):
    def __init__(self, name):
        self.name_ = name
        self.statedir_ = os.path.join(bigtest.confdir(), "tc-%s" % name)
        self.configFile_ = os.path.join(os.path.dirname(__file__), "%s.conf" % name)

    def name(self):
        return self.name_

    def start(self, controlBridge):
        bigtest.run(["rm", "-rf", self.statedir_])
        bigtest.run(["mkdir", "-p", self.statedir_])
        file(os.path.join(self.statedir_, "class"), "w").write(
            "%s.%s\n" % (self.__class__.__module__, self.__class__.__name__))
        config = self.config()
        x = config.get("host")
        if ":" in x:
            host, port = x.split(":")
        else:
            host, port = x, "5094"
        user = pwd.getpwuid(os.getuid())[0]
        try:
            bigtest.sudo(["openvpn", "--daemon", "--user", user,
                         "--writepid", os.path.join(self.statedir_, "pid"),
                         "--log", os.path.join(self.statedir_, "log"),
                         "--dev", self.name_, "--dev-type", "tap",
                         "--auth", "none", "--cipher", "none",
                         "--ping", "10", "--ping-restart", "60",
                         "--nobind", "--remote", host, port])
            for fn in ["log", "pid"]:
                bigtest.sudo(["chown", user, os.path.join(self.statedir_, fn)])
            bigtest.sudo(["ifconfig", self.name_, "up"])
            controlVlan = str(config.get("control_vlan"))
            bigtest.sudo(["vconfig", "add", self.name_, controlVlan])
            bigtest.sudo(["ifconfig", "%s.%s" % (self.name_, controlVlan), "up"])
            bigtest.sudo(["brctl", "addif", controlBridge, "%s.%s" % (self.name_, controlVlan)])
            sw = 0
            for vlans in config.get("switch_intf_vlans"):
                intf = 0
                for v in vlans:
                    vlan = "%s" % v
                    bridge = "%s-s%d-p%dbr" % (self.name_, sw, intf)
                    bigtest.sudo(["vconfig", "add", self.name_, vlan])
                    bigtest.sudo(["ifconfig", "%s.%s" % (self.name_, vlan), "up"])
                    if os.path.exists("/sys/class/net/%s" % bridge):
                        bigtest.sudo(["ifconfig", bridge, "down"])
                        bigtest.sudo(["brctl", "delbr", bridge])
                    bigtest.sudo(["brctl", "addbr", bridge])
                    bigtest.sudo(["ifconfig", bridge, "up"])
                    bigtest.sudo(["brctl", "addif", bridge, "%s.%s" % (self.name_, vlan)])
                    intf += 1
                sw += 1
            for i in reversed(range(10)):
                try:
                    bigtest.run(["ping", "-c", "2", config.get("control_ipaddr")])
                    break
                except bigtest.CalledProcessError:
                    if i < 1:
                        raise Exception("Failed to communicate with %s control address" % self.name_)
        except:
            bigtest.sudo(["cat", os.path.join(self.statedir_, "log")])
            raise

    def stop(self):
        bigtest.tryToStopProcess(bigtest.readPidFile(os.path.join(self.statedir_, "pid")))
        bridges, intfBridges = bigtest.bridgeInfo()
        config = self.config()
        sw = 0
        for vlans in config.get("switch_intf_vlans"):
            intf = 0
            for v in vlans:
                bridge = intfBridges.get("%s.%s" % (self.name_, v))
                if os.path.exists("/sys/class/net/%s" % bridge):
                    bigtest.sudo(["ifconfig", bridge, "down"])
                    bigtest.sudo(["brctl", "delbr", bridge])
                intf += 1
            sw += 1
        bigtest.run(["rm", "-rf", self.statedir_])

    def pid(self):
        return bigtest.readPidFile(os.path.join(self.statedir_, "pid"))

    def config(self):
        # FIXME: read configuration from a central database rather than a file
        d = {}
        execfile(self.configFile_, globals(), d)
        return d

    def topology(self):
        return self.config().get("topology")

    def switchDpids(self):
        return self.config().get("switch_dpids")

    def switchIntfBridges(self):
        bridges, intfBridges = bigtest.bridgeInfo()
        config = self.config()
        return [[intfBridges.get("%s.%s" % (self.name_, v)) for v in vlans]
                for vlans in config.get("switch_intf_vlans")]

    def dump(self):
        bridges, intfBridges = bigtest.bridgeInfo()
        config = self.config()
        s = StringIO.StringIO()
        s.write("host: %s\n" % config.get("host"))
        s.write("topology: %s\n" % config.get("topology"))
        pid = self.pid()
        if not os.path.exists("/proc/%s/cmdline" % pid):
            pid = "(not running)"
        s.write("pid: %s\n" % pid)
        bridge = intfBridges.get("%s.%s" % (self.name_, config.get("control_vlan")))
        s.write("control:\n")
        s.write("  ipaddr: %s\n" % config.get("control_ipaddr"))
        s.write("  interface: %s.%s\n" % (self.name_, config.get("control_vlan")))
        s.write("  bridge: %s\n" % bridge)
        sw = 0
        for vlans in config.get("switch_intf_vlans"):
            s.write("switch s%d:\n" % sw)
            s.write("  dpid: %s\n" % config.get("switch_dpids")[sw])
            s.write("  ipaddr: %s\n" % config.get("switch_ipaddrs")[sw])
            intf = 0
            for v in vlans:
                bridge = intfBridges.get("%s.%s" % (self.name_, v))
                s.write("  port p%d:\n" % intf)
                s.write("    interface: %s.%s\n" % (self.name_, v))
                s.write("    bridge: %s\n" % bridge)
                intf += 1
            sw += 1
        return s
