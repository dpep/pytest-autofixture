# Changelog

## Unreleased
- `let(lambda: ...)` defines a one-line lazy fixture, at module level or in a test class.
- Fixture bodies can reference other fixtures by bare name too.
- Fixtures now resolve lazily through pytest, so scope, overrides, teardown and caching behave like declared fixtures. This fixes stale values between tests and the wrong override winning.
- Requires pytest >= 8.4 and Python >= 3.11.

## 0.2.1 (2024-08-01)
- fix build

## 0.2.0 (2024-08-01)
- rename and readme

## 0.1.0 (2024-07-23)
