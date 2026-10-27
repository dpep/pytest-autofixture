pytest-autofixture
======
Use pytest fixtures by bare name. Tests and fixtures can reference any fixture without declaring it as a function parameter.


### Install
```
pip install pytest-autofixture
```

Requires Python 3.11+ and pytest 8.4+. The plugin is active once installed; turn it off for a run with `-p no:autofixture`.


### Usage
Any name in a test or fixture body that would otherwise raise `NameError` is looked up as a fixture. Lookup is lazy, so a fixture is set up only if the code reaches it, and scope, overrides and teardown work as they do for declared fixtures. Declared parameters still work and mix freely with bare names.

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

`parametrize` needs no declaration either:
```python
@pytest.mark.parametrize("role", ["admin", "owner"])
def test_can_delete():
    assert user.can_delete()
```

A parametrized name belongs to the test, like an argument, so in the test body it beats a builtin or module global of the same name: `parametrize("input", ...)` is fine. Fixture bodies keep the real builtin or global.


### `let`
`let` defines a one-line fixture where it's written, at module level or in a test class, like RSpec's `let(:role) { "member" }`:
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
- A `lambda` is called on first use, at most once per test, and can use other fixtures by bare name.
- Anything else is deep-copied for each test, so `let.items = []` or `let.user = User()` starts fresh every time. Strings, numbers, classes and functions pass through as-is (`let.model = User` is the class itself). If a value can't be copied, or must stay one shared object, use a lambda.

A `let` in a class overrides a fixture of the same name from outside it or from a base class, and can build on the value it replaces, like RSpec's `super()`: `let.role = lambda: role.upper()` gets the outer `role`.

`let` raises `TypeError` on the spot for a lambda with parameters, a value that can't be copied, or a name already taken by a builtin or module global, such as `let.id` or `let.json` after `import json` (the other name would always win).

Use a regular fixture when you need more than one expression, a scope, params or teardown. There's no special `subject`: `let.subject = lambda: Order(items=items)` is just a fixture named `subject`.


### Coming from RSpec
| RSpec | pytest-autofixture |
|---|---|
| `let(:user) { User.new(role:) }` | `let.user = lambda: User(role=role)` |
| `let!` / `before` | `@pytest.fixture(autouse=True)` (not `setup_method`, which can't see bare names) |
| `after` | a `yield` fixture |
| `subject` | `let.subject = lambda: ...` |
| `describe` / `context` | a nested class, named `Test...` so pytest collects it |
| `shared_examples` | a base test class |
| same examples with a different `let` | `@pytest.mark.parametrize("role", [...])` |


### Limitations
Declare the fixture as a parameter instead when:
- the test is wrapped by a decorator such as `@mock.patch` or hypothesis's `@given`, or by a plugin (the test fails with an error saying so)
- the fixture is parametrized
- an async test uses an async fixture
- a yield fixture first uses the name after its `yield` (pytest 9.1+ refuses fixture lookups during teardown)

Only test and fixture bodies see bare names; a module-level helper raises `NameError`, so pass the value in. Inside a test, `globals()` isn't the module's dict; use `sys.modules[__name__]` to reach the module.

Linters flag bare fixture names as undefined (ruff `F821`, pyright). Silence that for test files, e.g. in `pyproject.toml`:
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["F821"]
```

----
[![installs](https://img.shields.io/pypi/dm/pytest-autofixture?label=installs)](https://pypi.org/project/pytest-autofixture)
