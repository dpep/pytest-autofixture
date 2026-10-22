pytest-autofixture
======
Use pytest fixtures by bare name. Tests and fixtures can reference any fixture without declaring it as a function parameter.


### Install
```
pip install pytest-autofixture
```

Requires Python 3.11+ and pytest 8.4+. The plugin is active once installed; turn it off for a run with `-p no:autofixture`.


### Usage
Any name in a test or fixture that would otherwise raise `NameError` is looked up as a fixture. Lookup is lazy, so a fixture is set up only if the code reaches it. Scope, overrides and teardown work exactly as they do for declared fixtures.

Fixtures resolve their dependencies from where the test is, so an inner class can override one value and outer fixtures pick it up, like a nested `let` in RSpec:
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

Declared parameters still work and mix freely with bare names.

`parametrize` works the same way, no declaration needed:
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

What you assign decides how it behaves:
- A `lambda` is called on first use, at most once per test, so it can use other fixtures by bare name.
- A list, dict, set or bytearray is deep-copied for each test, so `let.items = []` starts empty every time. Use a lambda if the contents must stay the same objects.
- Anything else is shared by every test. That's fine for strings, numbers and classes (`let.model = User` is the class, not an instance).

A builtin name such as `let.id` raises `TypeError`, since the builtin would always win. Use a regular fixture when you need a scope, params or teardown. There's no special `subject`: `let.subject = lambda: Order(items=items)` is just a fixture named `subject`.


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

Only test and fixture bodies resolve bare names. A module-level helper raises `NameError` for them, so pass the value in instead.

Linters flag bare fixture names as undefined (ruff `F821`, pyright). Silence that for test files, e.g. in `pyproject.toml`:
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["F821"]
```

----
[![installs](https://img.shields.io/pypi/dm/pytest-autofixture?label=installs)](https://pypi.org/project/pytest-autofixture)
