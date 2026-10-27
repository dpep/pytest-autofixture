# Changelog

## Unreleased
- Reading globals and builtins in a test or fixture is faster, and a builtin monkeypatched during the test is seen by the test itself.
- Threads in a test that first use a fixture by bare name at the same time now share one setup. Before, the fixture was set up once per thread, or pytest 9.1 crashed.
- `global` writes in a yield fixture's teardown, and to globals named like `__private`, now reach the module.
- A parametrized name used by bare name wins over a builtin or module global of the same name. Before, `parametrize("input", ...)` silently gave the test the builtin `input`.
- `let.name` raises `TypeError` when a module global (such as an import) already has that name, since the global would hide the let.
- A `let` in a test class now overrides a fixture of the same name inherited from a base class. Before, the inherited fixture silently won.
- `let` deep-copies every non-lambda value for each test, not just lists, dicts and sets, so `let.user = User()` no longer leaks state between tests. A value that can't be copied fails at the `let` line. If you relied on one object shared by every test, write `let.name = lambda: OBJ`.
- A `KeyError` raised inside a fixture used by bare name is reported as itself, instead of as a misleading `NameError` for the fixture.

## 0.3.0 (2026-10-21)
- `@pytest.mark.parametrize` can target a name the test only uses by bare name.
- Decorated tests (`@mock.patch`, `@given`) that use bare fixture names now fail with an error saying to declare them as parameters, instead of silently getting the fixture object.
- `let.name = value` defines a one-line fixture, at module level or in a test class. A `lambda` value is called lazily, once per test; a list, dict or set is deep-copied for each test.
- Fixture bodies can reference other fixtures by bare name too.
- Fixtures now resolve lazily through pytest, so scope, overrides, teardown and caching behave like declared fixtures. This fixes stale values between tests and the wrong override winning.
- Requires pytest >= 8.4 and Python >= 3.11.

## 0.2.1 (2024-08-01)
- fix build

## 0.2.0 (2024-08-01)
- rename and readme

## 0.1.0 (2024-07-23)
