import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def name():
    return "conftest"


@pytest.fixture
def role():
    return "guest"
