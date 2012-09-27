from contextlib import contextmanager

@contextmanager
def NetContext (net):
  try:
    yield net
  finally:
    net.stop()

@contextmanager
def EnvContext (env):
  try:
    yield env
  finally:
    env.endTest()
