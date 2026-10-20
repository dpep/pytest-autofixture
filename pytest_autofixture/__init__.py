"""Let tests reference fixtures by bare name.

Any name in a test that would otherwise raise NameError is looked up as a
fixture, lazily, via `request.getfixturevalue`. pytest owns setup, caching,
scope, overrides and teardown; nothing is written to the test's module.
"""

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


# runtest_call, not pyfunc_call: plugins like pytest-asyncio wrap item.obj
# inside runtest(), so the swap has to happen first
@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    original = getattr(item, "obj", None)
    if isinstance(original, types.MethodType):
        rebound = types.MethodType(_rebind(original.__func__, item._request), original.__self__)
    elif isinstance(original, types.FunctionType):
        rebound = _rebind(original, item._request)
    else:
        return (yield)

    item.obj = rebound
    try:
        return (yield)
    finally:
        item.obj = original
