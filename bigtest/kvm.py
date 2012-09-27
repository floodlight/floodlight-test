#!/usr/bin/python

import bigtest.node, bigtest.linux, bigtest.cli
import logging, pexpect, re, time, os, time
import bigtest

class Node(bigtest.linux.Node):
    def __init__(self):
        pass

    def registerVm(self, name):
        cli = self.cli()

    # FIXME: support only linux now
    def startVm(self, name, spec, datastore, wait_for_migration=False):
        cli = self.cli()
        
        # create vm folder
        vm_dir = os.path.join(datastore, name)
        cli.runCmd("sudo mkdir -p %s" % vm_dir)

        # copy vmdk file
        defaultMount = os.path.join("/mnt", spec.nfsHost,
                                    os.path.basename(spec.nfsShare))
        mount = self.mountNas(spec.nfsHost, spec.nfsShare, defaultMount)
        srcVmdk = os.path.join(mount, spec.vmdkPath)
        dstVmdk = os.path.join(vm_dir, os.path.basename(spec.vmdkPath))
        cli.runCmd("sudo cp %s %s" % (srcVmdk, dstVmdk))
        
        # serial
        serial = self.serialCounter()
        self.setSerialCounter(serial + 1)
        monitor = self.monitorCounter()
        self.setMonitorCounter(monitor + 1)

        # network
        mac = "52:54:00:%02x:%02x:%02x" % ((hash(name) >> 16) & 0xff,
                                           (hash(name) >> 8) & 0xff,
                                           hash(name) & 0xff)
        ifup = "/etc/ovs-ifup" # ovs-br0
        ifdown = "/etc/ovs-ifdown" # ovs-br0

        # start kvm
        cmdline = ("sudo kvm "
                         "-name %s "
                         "-daemonize "
                         "-nographic "
                         "-serial telnet::%d,server,nowait "
                         "-qmp telnet::%d,server,nowait "
                         "-m %s "
                         "-hda %s " 
                         "-net nic,macaddr=%s "
                         "-net tap,script=%s,downscript=%s "
                         % (name, serial, monitor, spec.memory, dstVmdk,
                            mac, ifup, ifdown))
        if wait_for_migration:
            cmdline += " -incoming tcp:0:%d " % (monitor+1000)
        self.setCmdline(cmdline)
        ret = cli.runCmd(cmdline)
        self.setCreatedVms((self.createdVms()) + [name])
        return (ret, serial)

    def runSerialCmd(self, cmd, interval=5, timeout=600):
        exception = Exception("Unknown exception in runSerialCmd()")
        timeout_ = time.time() + timeout
        while time.time() < timeout_:
            try:
                console = self.serialConsole()
                username = self.username()
                password = self.password()
                self.doSerialLogin(console, username, r"\r\n[-.\w]+ login: ",
                                       r"\nPassword: ")
                console.sendline(password)
                cli = bigtest.cli.Cli(console, "linux")
                return cli.runCmd(cmd)
            except Exception, e:
                exception = e
                self.serialConsole_ = None
                bigtest.log.error("runSerialCmd() failed...")
            time.sleep(interval)
        raise exception

