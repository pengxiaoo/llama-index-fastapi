import os


def pytest_configure():
    os.environ["IS_LOCAL_TEST"] = "True"
