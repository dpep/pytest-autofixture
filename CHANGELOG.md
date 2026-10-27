# Changelog

## Unreleased
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
