#!/usr/bin/python

import re
import pexpect
import os

class CommandFailed(Exception):
    pass

class Cli(object):
    def __init__(self, console, image_type = "linux"):
        self.image_type = image_type
        self.console_ = console
        self.mode_ = None
        self.count_ = 0
        self.modes = self.setupModes()
        self.console_.sendline("") # try to backspace over any old chars
                                     # left on the tty from a prev test
        self.console_.sendline("")
        self.expectPrompt()
        # might need to check image type here
        self.gotoBashMode()

    def console(self):
        return self.console_

    cliErrorRes = [re.compile(r"\r\nError running command '.*'\.\r"),
                   re.compile(r"\r\nREST API .* unexpected error -.*\r\n\{.*"),
                   re.compile(r"\r\nError: .*"),
                   re.compile(r"\r\nSyntax: .*"),
                   re.compile(r"\r\nSyntax error: .*")
                   ]

    #
    # get_mininet_cmd
    #
    # Get the command string to use to start mininet session. If a screen
    # session is desired, command string is modified so that mn is launched
    # through persistent screen session.
    #
    # 'screen' based mn can be enabled either setting env BIGTEST_TERM_SCREEN 
    # or 'touch /tmp/BIGTEST_TERM_SCREEN'
    #
    def get_mininet_cmd (self):
        cmd = "sudo mn"
        use_screen = os.environ.has_key("BIGTEST_TERM_SCREEN") or \
                     os.path.isfile("/tmp/BIGTEST_TERM_SCREEN")
        if use_screen:
            cmd = "screen -S bigtestMininet %s" % cmd
        return cmd

    #
    # Close any outstanding screen based mininet session by sending 'quit'
    # command to screen.
    #
    def close_mininet (self):
        self.gotoBashMode()
        self.runCmd("screen -S bigtestMininet -X quit")

    def setupModes(self):
        if self.image_type == "linux":
            modes = {
                "bash":
                    (None, None, r"\r\n[\S@]+:[\S ]+\$ ", "echo %s", None),
                "root":
                    ("bash", "sudo bash", r"\r\n[\S@]+:[\S ]+[#] ", "echo %s", None),
                "mininet":
                    ("bash", self.get_mininet_cmd(), r"\r\n+mininet> ", "sh echo %s", None),
                "python":
                    ("bash", "python", r"\r\n>>> ", "print '%s'.replace('   ', ' ')", None),
            }
        else:
            modes = None

        return modes

    def runCmd(self, cmd, check=True):

        # Note: the output of cmd must end with a newline separating it from
        # the next prompt
        self.console_.sendline(self.modes[self.mode_][3] %
                               ("__   %d   __" % self.count_))
        # send extra new line if in scapy mode
        if self.mode_ == 'scapy' :
            self.console_.sendline("\r\n")

        self.console_.expect("\r\n__ %d __" % self.count_)
        self.count_ += 1

        # if in scapy mode, expect 2 extra >>> before scapy prompt
        if self.mode_ == 'scapy' :
            self.console_.expect(">>>")
            self.console_.expect(">>>")

        self.expectPrompt()
        self.console_.sendline(cmd)
        # send extra new line if in scapy mode
        if self.mode_ == 'scapy' :
            self.console_.sendline("\r\n")

        # special handling for exit(). If exit is called, expect till mininet mode is reached
        previousMode = self.mode_
        if self.mode_ == 'scapy' and cmd == 'exit()':
            while (self.mode_ == 'scapy'):
                self.expectPrompt()
            self.console_.sendline("\r\n")
        x = self.expectPrompt()
        # if still in scapy mode, expect two extra >>>
        if previousMode == 'scapy' and self.mode_ == 'scapy':
            self.console_.expect(">>>")
            self.console_.expect(">>>")
        if check:
            for errorRe in self.modes[self.mode_][4] or []:
                m = errorRe.search(x)
                if m:
                    raise CommandFailed("Command '%s' failed in mode '%s': %s" % (
                            cmd, self.mode_, m.group(0)))
        return x

    def expectPrompt(self):
        modes = self.modes.items()
        i, before, after = self.console_.expectReAlt([p[2] for m, p in modes])
        self.mode_ = modes[i][0]
        return before

    def sleep(self, seconds):
        self.console_.expectRe(pexpect.TIMEOUT, timeout=seconds)

    def mode(self):
        return self.mode_

    def gotoMode(self, mode, append=None):
        # first get to the top level mode
        top_level = 'login'
        if self.image_type == 'linux':
            top_level = 'bash'

        if mode == top_level:
            while self.mode_ != top_level:
                self.runCmd("exit")
            return
        self.gotoMode(self.modes[mode][0])
        cmd = self.modes[mode][1]
        if append is not None:
            cmd += " " + append
        self.runCmd(cmd)

    def gotoLoginMode(self):
        self.gotoMode("login")

    def gotoEnableMode(self):
        self.gotoMode("enable")

    def gotoConfigMode(self):
        self.gotoMode("config")

    def gotoBashMode(self):
        self.gotoMode("bash")

    def gotoRootMode(self):
        self.gotoMode("root")

    # call after going to mininet mode, so dont go there
    def gotoScapyMode(self, args):
       cmd = self.modes["scapy"][1]
       cmd = args + " " + cmd
       self.runCmd(cmd)

    def gotoMininetMode(self, args):
        self.close_mininet()
        self.gotoMode("mininet", args)

    def gotoDjangoShellMode(self):
        self.gotoMode("djangoshell")
