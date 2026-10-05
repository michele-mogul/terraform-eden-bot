import eden.core.ui


def pytest_configure(config):
    eden.core.ui.SUSPENSE_SECONDS = 0   # no "typing…" pauses in tests
