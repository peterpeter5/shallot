def pytest_configure(config):
    import sys

    sys._pytest_shallot_ = True


def pytest_unconfigure(config):
    import sys

    del sys._pytest_shallot_


pytest_plugins = 'pytester'