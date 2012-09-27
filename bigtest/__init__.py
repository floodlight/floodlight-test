#!/usr/bin/python

import errno, logging, os, re, signal, subprocess, sys, time
import pexpect
import traceback
import os
import sys
from subprocess import call

log = None

#
# assert
#
# This is a custom assert method.
#
# Optionally, failures can be ignored or paused for resumption
#
# For IGNORE: env BIGTEST_FAILURE_IGNORE or file /tmp/BIGTEST_FAILURE_IGNORE
# For PAUSE:  env BIGTEST_FAILURE_PAUSE or  file /tmp/BIGTEST_FAILURE_PAUSE
#
# With file option, one can tune the behavior even after the tests have begun
#
def Assert (expression, msg = None):
    ignore_assert_failure = os.environ.has_key("BIGTEST_FAILURE_IGNORE") or \
                            os.path.isfile("/tmp/BIGTEST_FAILURE_IGNORE")
    pause_assert_failure  = os.environ.has_key("BIGTEST_FAILURE_PAUSE") or \
                            os.path.isfile("/tmp/BIGTEST_FAILURE_PAUSE")

    try:
        assert expression, msg

    except AssertionError, e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stack = traceback.format_list(traceback.extract_stack())

        #
        # Print the usual traceback header.
        #
        sys.stderr.write("Traceback (most recent call last):\n")

        #
        # Print all the frames except the last one which this bigtest.Assert() from
        # bigtest module.
        #
        for frame in range(0, len(stack) - 1):
            sys.stderr.write(stack[frame])
        traceback.print_exception(exc_type, exc_value, None)

        if pause_assert_failure:
            sys.stderr.write("To get to mininet session from mininet node's shell: ")
            sys.stderr.write("    screen -S bigtestMininet -x\n")

            sys.stderr.write("Failed test paused!, and python shell invoked: ")
            sys.stderr.write("Exit from python shell to resume test\n")
            subprocess.call("python")
            
        elif ignore_assert_failure:

            #
            # Ignore this failure
            #
            sys.stderr.write("Failed assertion ignored !\n")

        else:

            #
            # Force a failure with non zero exit status as the assert has indeed
            # failed and we do _not_ want to ignore it. (default behavior)
            #
            exit(1)

def setLog(name, level=None):
    global log
    if level is None:
        level = os.environ.get("BIGTEST_LOGLEVEL", "info")
    if isinstance(level, str):
        level = int(level) if level.isdigit() else getattr(logging, level.upper())
    ch = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(name)s: %(processName)s: %(message)s")
    ch.setFormatter(formatter)
    log = logging.getLogger(name)
    log.addHandler(ch)
    log.setLevel(level)
setLog("bigtest")


CalledProcessError = subprocess.CalledProcessError

def run(args, captureStdout=False, trace=True, asRoot=False):
    if type(args) is str:
        if trace:
            sys.stderr.write("+ %s\n" % args)
        c = ["sh", "-c", args]
    else:
        c = ["sh"] + (["-x"] if trace else []) + ["-c", '$0 "$@"'] + list(args)
    if asRoot:
        c = ["sudo"] + c
    p = subprocess.Popen(c, stdout=(subprocess.PIPE if captureStdout else None))
    out = p.communicate()[0]
    if captureStdout and out:
        out = out.rstrip("\n")
    if trace and out:
        for l in out.split("\n"):
            sys.stderr.write("> %s\n" % l)
    if p.returncode != 0:
        #### HACK -- try again if this failed
        # TODO come up with a better system
        # working theory is that there is a race to reclaim mem
        # and if we wait a bit and try again, the mem reclaim may have worked
        sys.stderr.write("+ WARNING failed to run %s (%s)\n" %(str(c), str(p.returncode)))
        sys.stderr.write("+ WARNING sleeping and try again\n")
        time.sleep(1)
        p = subprocess.Popen(c, stdout=(subprocess.PIPE if captureStdout else None))
        if p.returncode != 0:
            sys.stderr.write("+ WARNING really failed... giving up")
            raise CalledProcessError(p.returncode, args)
        else:
            sys.stderr.write("+ WARNING recovered... weird please FIXME")
    return out

def sudo(args, captureStdout=False, trace=True):
    return run(args, captureStdout, trace, asRoot=True)


def readPidFile(pidFile):
    try:
        return int(file(pidFile).read().strip())
    except ValueError, e:
        return None
    except IOError, e:
        if e.errno != errno.ENOENT:
            raise
        return None


def tryToStopProcess(pid):
    while pid is not None:
        try:
            os.kill(pid, signal.SIGKILL) # returns ESRCH if already dead
            os.waitpid(pid, 0) # returns ECHILD if already dead or not a child
        except OSError, e:
            if e.errno == errno.ECHILD:
                if os.path.exists("/proc/%d/status" % pid):
                    for line in file("/proc/%d/status" % pid).readlines():
                        # process is in zombie state
                        if line.startswith("State:") and "Z (zombie)" in line:
                            pid = None
                            break
                # process does not exist or is not a child
                time.sleep(1)
                continue
            if e.errno != errno.ESRCH:
                raise
            # process is dead
            pid = None


def waitForProcessToStop(pid):
    while pid is not None:
        try:
            os.kill(pid, signal.SIGCONT)
        except OSError, e:
            if e.errno != errno.ESRCH:
                raise
            pid = None


_bridgeInfo = None
def bridgeInfo(useCached=True):
    """Scrape bridge info from brctl show.  Return a dict indexed by
    bridge name with info about each bridge (bridge id, stp enabled,
    slave interfaces, IP address), and a dict mapping a slave
    interface to the bridge name."""
    global _bridgeInfo
    if not _bridgeInfo or not useCached:
        bridges = {}
        intfBridges = {}
        if os.path.exists("/sys/class/net"):
            x = sudo(["brctl", "show"], captureStdout=True, trace=False)
            lastName = None
            for l in x.split("\n"):
                m = re.match(r"([\S]*)\t\t(\t|[\S]*)\t(\t|[\S]*)\t\t([\S]*)$", l)
                if not m:
                    continue
                name, bid, stp, intf = m.groups()
                if name:
                    ipaddr = None
                    y = sudo(["ifconfig", name], captureStdout=True, trace=False)
                    n = re.search("inet addr:([0-9.]*)", y)
                    if n:
                        ipaddr = n.group(1)
                    bridges[name] = [bid, stp, [intf] if intf else [], ipaddr]
                    if intf:
                        intfBridges[intf] = name
                    lastName = name
                else:
                    bridges[lastName][2].append(intf)
                    intfBridges[intf] = lastName
        _bridgeInfo = (bridges, intfBridges)
    return _bridgeInfo


_confdir = None
def confdir():
    global _confdir
    if not _confdir:
        _confdir = "/var/run/bigtest"
        sudo(["mkdir", "-p", _confdir], trace=False)
        sudo(["chmod", "0777", _confdir], trace=False)
    return _confdir


class Console(object):
    def __init__(self, name, pex, logLevel):
        self.name_ = name
        self.pexpect_ = pex
        self.logLevel_ = logLevel

    def pexpect(self):
        return self.pexpect_

    def logFrom(self, s):
        for line in s.split("\n"):
            log.log(self.logLevel_, "from %s: %r", self.name_, line)

    def logTo(self, s):
        log.log(self.logLevel_, "to %s: %r", self.name_, s)

    def expectRe(self, pattern, **kargs):
        try:
            self.pexpect_.expect(pattern, **kargs)
        except pexpect.TIMEOUT:
            raise

        self.logFrom(str(self.pexpect_.before) + str(self.pexpect_.after))
        return [self.pexpect_.before, self.pexpect_.after]

    def expectReAlt(self, patternList, **kargs):
        i = self.pexpect_.expect(patternList, **kargs)
        self.logFrom(str(self.pexpect_.before) + str(self.pexpect_.after))
        if patternList[i] == pexpect.TIMEOUT:
            self.pexpect_.buffer = ""
        return [i, self.pexpect_.before, self.pexpect_.after]

    def expect(self, pattern, **kargs):
        return self.expectRe(re.escape(pattern), **kargs)

    def send(self, s):
        self.logTo(s)
        self.pexpect_.send(s)

    def sendline(self, s):
        self.logTo(s)
        self.pexpect_.sendline(s)

    def sendcontrol(self, char):
        self.logTo("[control-%s]" % char)
        self.pexpect_.sendcontrol(char)
