"""LoggingTest.py

Adapter classes to use logging with unittest.

Usage:

1. inherit your test case classes from TestCase here
2. invoke unittest.main with either the TestRunner class as an
   argument:

     unittest.main(testRunner=LoggingTest.TestRunner, ...)

   or create an instance of the TestRunner with a specific log:

     logger = bigtest.log.getChild("unittest")
     runner = LoggingTest.TestRunner(log=logger, verbosity=...)
     unittest.main(testRunner=runner, verbosity=...)

   (note that in the latter case 'verbosity' should be passed to both
   the unittest main and to the TestRunner constructor).

NOTES:

- stdout/stderr is captured within Python, but not for subprocesses.

"""

import sys, io
import time
import logging
import unittest.result
from unittest.signals import registerResult
from cStringIO import StringIO

class LogIO(io.IOBase):
    """File-like wrapper to serialize 'print' output to the log.

    Emits a line for each full line of text, also emits a partial line
    when 'flush' is called.
    """

    def __init__(self, log, prefix="", level=logging.INFO):
        self.log = log
        self.pfx = prefix
        self.lvl = level
        self.buf = ""

    def write(self, s):
        self.buf += s
        self._drain()

    def flush(self):
        self._drain(force=True)

    def _drain(self, force=False):

        while self.buf:
            idx = self.buf.find("\n")
            if idx < 0: break

            self.log.log(self.lvl, "%s%s", self.pfx, self.buf[:idx])
            self.buf = self.buf[idx+1:]

        if self.buf and force:
            self.log.log(self.lvl, "%s%s ...", self.pfx, self.buf[:idx])
            self.buf = ""

class TestResult(unittest.result.TestResult):
    """Result accumulator for unittest.

    Test events are logged to the per-result logger.
    stdout/stderr is wrapped in a file-like log serializer.
    Exceptions are serialized to the log as per 'logging.exception'.
    """
    
    def __init__(self, log, descriptions, verbosity):
        super(TestResult, self).__init__()

        self.log = log
        self.descriptions = descriptions

        if verbosity > 1:
            self.lvl = logging.INFO
        else:
            self.lvl = logging.DEBUG

        self._stdout = None
        self._stderr = None

    def getDescription(self, test):
        doc_first_line = test.shortDescription()
        if self.descriptions and doc_first_line:
            return test.shortDescription() or str(test)
        else:
            return str(test)
        
    def startTest(self, test):
        super(TestResult, self).startTest(test)
        self.log.log(self.lvl, "START %s", self.getDescription(test))

        self._stdout = sys.stdout
        sys.stdout = LogIO(self.log, prefix=">>> ", level=logging.INFO)
        self._stderr = sys.stderr
        sys.stderr = LogIO(self.log, prefix="*** ", level=logging.WARN)
        
    def stopTest(self, test):

        if self._stdout is not None:
            sys.stdout, self._stdout = self._stdout, None
        if self._stderr is not None:
            sys.stderr, self._stderr = self._stderr, None

    def addSuccess(self, test):
        super(TestResult, self).addSuccess(test)
        self.log.log(self.lvl, "PASS")

    def addError(self, test, err):
        super(TestResult, self).addError(test, err)
        self.log.log(logging.ERROR, "ERROR", exc_info=err)

    def addFailure(self, test, err):
        super(TestResult, self).addError(test, err)
        self.log.log(logging.ERROR, "FAIL", exc_info=err)

    def addSkip(self, test, reason):
        super(TestResult, self).addSkip(test, reason)
        self.log.warn("SKIP (%s)", reason)

    def addExpectedFailure(self, test, err):
        super(TestResult, self).addExpectedFailure(test, err)
        self.log.log(logging.ERROR, "XFAIL", exc_info=err)

    def addUnexpectedSuccess(self, test):
        super(TestResult, self).addUnexpectedSuccess(test)
        self.log.error("XPASS")

class TestRunner(object):
    """Logging-aware unittest.TestRunner class."""

    resultclass = TestResult

    def __init__(self, descriptions=True, verbosity=1,
                 failfast=False, buffer=False, resultclass=None,
                 log=None):
        self.descriptions = descriptions
        self.verbosity = verbosity
        self.failfast = failfast
        self.buffer = buffer
        if resultclass is not None:
            self.resultclass = resultclass

        if log is None:
            logging.basicConfig()
        self.log = log or logging.getLogger("unittest")

    def _makeResult(self):
        return self.resultclass(self.log, self.descriptions, self.verbosity)

    def run(self, test):
        "Run the given test case or test suite."
        result = self._makeResult()
        registerResult(result)
        result.failfast = self.failfast
        result.buffer = self.buffer
        startTime = time.time()
        startTestRun = getattr(result, 'startTestRun', None)
        if startTestRun is not None:
            startTestRun()
        try:
            test(result)
        finally:
            stopTestRun = getattr(result, 'stopTestRun', None)
            if stopTestRun is not None:
                stopTestRun()
        stopTime = time.time()
        timeTaken = stopTime - startTime
        run = result.testsRun
        self.log.info("Ran %d test%s in %.3fs",
                      run, run != 1 and "s" or "", timeTaken)

        expectedFails = unexpectedSuccesses = skipped = 0
        try:
            results = map(len, (result.expectedFailures,
                                result.unexpectedSuccesses,
                                result.skipped))
        except AttributeError:
            pass
        else:
            expectedFails, unexpectedSuccesses, skipped = results

        infos = []
        summary = StringIO()
        lvl = logging.INFO
        if not result.wasSuccessful():
            summary.write("FAILED")
            lvl = logging.ERROR
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                infos.append("failures=%d" % failed)
            if errored:
                infos.append("errors=%d" % errored)
        else:
            summary.write("OK")
        if skipped:
            infos.append("skipped=%d" % skipped)
        if expectedFails:
            infos.append("expected failures=%d" % expectedFails)
        if unexpectedSuccesses:
            infos.append("unexpected successes=%d" % unexpectedSuccesses)
        if infos:
            summary.write(" (%s)" % (", ".join(infos),))
        self.log.log(lvl, summary.getvalue())
        return result
    
class TestCase(unittest.TestCase):
    """Logging-aware unittest.TestCase base class.

    Each invocation (test method execution) starts with a local 'log'
    attribute that is prefixed with the test specifier (usually the
    test class plus the test method name).

    Make sure to inherit from this class if you want your tests to log
    correctly!
    """

    def run(self, result):
        if isinstance(result, TestResult):
            self.log = result.log.getChild(self.id())
        super(TestCase, self).run(result)
