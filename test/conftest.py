def pytest_configure(config):
    import sys

    sys._pytest_ = True


def pytest_unconfigure(config):
    import sys

    del sys._pytest_


pytest_plugins = 'pytester'