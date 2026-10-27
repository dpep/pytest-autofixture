# Changelog

## Unreleased
- Breaking: `let` deep-copies every non-lambda value for each test, not just lists, dicts and sets, so `let.user = User()` no longer leaks state between tests. If you relied on one object shared by every test, write `let.name = lambda: OBJ`. A value that can't be copied now raises `TypeError` at the `let` line.
- Breaking: a `let` named like an existing module global, such as an import, now raises `TypeError`, since the global would hide it. Rename the let or the global.
- In a test body, a parametrized name beats a builtin or module global of the same name. Before, `parametrize("input", ...)` silently gave the test the builtin `input`.
- A `let` overrides a fixture of the same name inherited from a base class, or imported into the same module. Before, the other fixture silently won.
- Threads that first use the same bare-name fixture at once share one setup. Before, it was set up once per thread, or pytest 9.1 crashed.
- `global` writes in a yield fixture's teardown, and to names like `__private`, now reach the module.
- A builtin monkeypatched during a test is seen by the test itself, and reading globals and builtins is faster.
- A `KeyError` raised inside a bare-name fixture is reported as itself, not as a misleading `NameError` for the fixture.

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
