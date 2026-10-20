"""Let tests reference fixtures by bare name.

Any name in a test that would otherwise raise NameError is looked up as a
fixture, lazily, via `request.getfixturevalue`. pytest owns setup, caching,
scope, overrides and teardown; nothing is written to the test's module.
"""

__version__ = "0.2.1"

import builtins
import types

import pytest
from _pytest.fixtures import FixtureFunctionDefinition


class _FixtureBuiltins(dict):
    """Builtins for one test call: real builtins first, then fixtures."""

    def __init__(self, request):
        super().__init__(vars(builtins))
        self._request = request

    def __missing__(self, name):
        try:
            value = self._request.getfixturevalue(name)
        except pytest.FixtureLookupError as e:
            if e.argname != name:
                raise  # a real fixture whose own dependency is missing
            raise NameError(f"name {name!r} is not defined (and no fixture by that name)") from None
        self[name] = value
        return value


def _rebind(func, request):
    # a fixture defined in the test's own module would shadow its value
    namespace = {
        k: v for k, v in func.__globals__.items() if not isinstance(v, FixtureFunctionDefinition)
    }
    # functions take builtins from their globals when created (3.10+), so
    # lambdas, nested defs and genexprs inside the test inherit the fallback
    namespace["__builtins__"] = _FixtureBuiltins(request)
    rebound = types.FunctionType(
        func.__code__, namespace, func.__name__, func.__defaults__, func.__closure__
    )
    rebound.__kwdefaults__ = func.__kwdefaults__
    rebound.__dict__.update(func.__dict__)
    return rebound


def _swap(obj, attr, request):
    """Temporarily replace obj.<attr> with a rebound copy, if it's a function."""
    original = getattr(obj, attr, None)
    if isinstance(original, types.MethodType):
        rebound = types.MethodType(_rebind(original.__func__, request), original.__self__)
    elif isinstance(original, types.FunctionType):
        rebound = _rebind(original, request)
    else:
        return (yield)

    setattr(obj, attr, rebound)
    try:
        return (yield)
    finally:
        setattr(obj, attr, original)


# runtest_call, not pyfunc_call: plugins like pytest-asyncio wrap item.obj
# inside runtest(), so the swap has to happen first
@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    return (yield from _swap(item, "obj", item._request))


# the request here is the fixture's own SubRequest, so lookups get pytest's
# scope checks and resolve overrides from the requesting test's position.
# tryfirst: wrap the user's function before pytest-asyncio wraps it.
@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_fixture_setup(fixturedef, request):
    return (yield from _swap(fixturedef, "func", request))
