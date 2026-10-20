pytest-autofixture
======
Simplify pytest fixtures by making them automagically available.  Tests can reference fixtures without needing to reference them as function parameters.


### Install
```pip install pytest-autofixture```


### Usage
```python
# conftest.py
import pytest

@pytest.fixture
def one():
    return 1


# test_one.py
def test_one():
    assert one == 1
```

Any name in a test or fixture that would otherwise raise `NameError` is looked up as a fixture. Lookup is lazy, so a fixture is only set up if it's actually reached. Scope, overrides and teardown work exactly as they do for declared fixtures.

Because fixtures resolve their dependencies from where the test is, an inner class can override one value and outer fixtures pick it up, like a nested `let` in RSpec:
```python
@pytest.fixture
def role():
    return "member"

@pytest.fixture
def user():
    return User(role=role)

def test_member():
    assert not user.can_delete()

class TestAdmin:
    @pytest.fixture
    def role(self):
        return "admin"

    def test_admin(self):
        assert user.can_delete()
```


### Limitations
Declare the fixture as a parameter instead when:
- the test is wrapped by a decorator such as `@mock.patch` or hypothesis's `@given`
- the fixture is parametrized
- an async test uses an async fixture

Linters will flag bare fixture names as undefined (ruff `F821`, pyright). Silence that for test files, e.g. in `pyproject.toml`:
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["F821"]
```

----
[![installs](https://img.shields.io/pypi/dm/pytest-autofixture?label=installs)](https://pypi.org/project/pytest-autofixture)
