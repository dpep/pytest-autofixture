pytest-autofixture
======
Simplify pytest fixtures by making them automagically available.  Tests can reference fixtures without needing to reference them as function parameters.


### Install
```pip install pytest-autofixture```

Requires Python 3.11+ and pytest 8.4+. The plugin is active as soon as it's installed; turn it off for a run with `-p no:autofixture`.


### Usage
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

Declared parameters keep working, and mix freely with bare names.

`parametrize` works the same way, without declaring the name:
```python
@pytest.mark.parametrize("role", ["admin", "owner"])
def test_can_delete():
    assert user.can_delete()
```


### `let`
For one-liners, `let` defines a fixture right where it's written, at module level or in a test class, like RSpec's `let(:role) { "member" }`:
```python
from pytest_autofixture import let

let.role = "member"
let.user = lambda: User(role=role)


class TestAdmin:
    let.role = "admin"

    def test_admin(self):
        assert user.can_delete()
```

A `lambda` is called on first use, at most once per test, so it can use other fixtures by bare name. A list, dict or set is deep-copied for each test, so `let.items = []` starts empty every time; use a lambda if its contents must stay the same objects. Any other value is shared by every test: fine for strings, numbers and classes (`let.model = User` is the class, not an instance). Use a regular fixture when you need a scope, params, or teardown. There's no special `subject`: `let.subject = lambda: Order(items=items)` is just a fixture named `subject`.


### Coming from RSpec
| RSpec | pytest-autofixture |
|---|---|
| `let(:user) { User.new(role:) }` | `let.user = lambda: User(role=role)` |
| `let!` / `before` | `@pytest.fixture(autouse=True)` |
| `after` | a `yield` fixture |
| `subject` | `let.subject = lambda: ...` |
| `describe` / `context` | a nested `class TestX` |
| `shared_examples` | a base test class |
| same examples with a different `let` | `@pytest.mark.parametrize("role", [...])` |


### Limitations
Declare the fixture as a parameter instead when:
- the test is wrapped by a decorator such as `@mock.patch` or hypothesis's `@given` (the test fails with an error saying so)
- the fixture is parametrized
- an async test uses an async fixture
- a yield fixture first uses the name after its `yield` (pytest 9.1+ refuses fixture lookups during teardown)

Only test and fixture bodies resolve bare names. A module-level helper raises `NameError` for them; pass the value in instead.

Linters will flag bare fixture names as undefined (ruff `F821`, pyright). Silence that for test files, e.g. in `pyproject.toml`:
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["F821"]
```

----
[![installs](https://img.shields.io/pypi/dm/pytest-autofixture?label=installs)](https://pypi.org/project/pytest-autofixture)
