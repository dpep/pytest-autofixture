"""Let tests reference fixtures by bare name.

Any name in a test that would otherwise raise NameError is looked up as a
fixture, lazily, via `request.getfixturevalue`. pytest owns setup, caching,
scope, overrides and teardown; nothing is written to the test's module.
"""

__version__ = "0.2.1"

import builtins
import dis
import inspect
import sys
import types

import pytest
from _pytest.fixtures import FixtureFunctionDefinition


class _Let:
    """`let.role = "member"` defines a fixture named `role` where it's written.

    A lambda is called lazily, once per test; any other value is used as is.
    """

    def __setattr__(self, name, value):
        frame = sys._getframe(1)
        # a function's locals are gone once it returns, and pytest never sees them
        if frame.f_code.co_flags & inspect.CO_OPTIMIZED:
            raise TypeError(f"let.{name} must be set at module or class level")

        if isinstance(value, types.LambdaType) and value.__name__ == "<lambda>":
            if inspect.signature(value).parameters:
                raise TypeError(f"let.{name} lambda takes no arguments; use bare names instead")
            factory = value
        else:
            factory = lambda: value  # noqa: E731

        # staticmethod so a let in a test class isn't bound to the instance
        frame.f_locals[name] = pytest.fixture(staticmethod(factory), name=name)


let = _Let()


class _FixtureBuiltins(dict):
    """Builtins for one test call: real builtins first, then fixtures."""

    def __init__(self, request):
        super().__init__(vars(builtins))
        self._request = request

    def __missing__(self, name):
        try:
            value = self._request.getfixturevalue(name)
        except pytest.FixtureLookupError as e:
            # a missing dependency of a real fixture, or pytest refusing the lookup
            # (e.g. first request during teardown) carries its own message
            if e.argname != name or e.msg is not None:
                raise
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
    elif isinstance(original, staticmethod):
        # a module-level let; a plain function is never bound to a test instance
        rebound = _rebind(original.__func__, request)
    elif isinstance(original, types.FunctionType):
        rebound = _rebind(original, request)
    else:
        return (yield)

    setattr(obj, attr, rebound)
    try:
        return (yield)
    finally:
        setattr(obj, attr, original)


def _loaded_globals(code):
    for instruction in dis.get_instructions(code):
        if instruction.opname == "LOAD_GLOBAL":
            yield instruction.argval
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            yield from _loaded_globals(const)


def _check_decorated(item):
    """Whether the test is wrapped by a decorator, which keeps its real globals.

    Fails up front if a bare name would silently get a module's fixture object.
    """
    # hypothesis's @given doesn't set __wrapped__, but exposes the test this way
    hypothesis = getattr(item.obj, "hypothesis", None)
    inner = getattr(hypothesis, "inner_test", None) or inspect.unwrap(item.obj)
    if inner is item.obj or not hasattr(inner, "__code__"):
        return False

    names = sorted(
        {
            name
            for name in _loaded_globals(inner.__code__)
            if isinstance(inner.__globals__.get(name), FixtureFunctionDefinition)
        }
    )
    if names:
        listed = ", ".join(repr(name) for name in names)
        plural = "a parameter" if len(names) == 1 else "parameters"
        pytest.fail(f"{_decorated_message(item)}: declare {listed} as {plural}", pytrace=False)
    return True


def _decorated_message(item):
    return f"{item.name} is wrapped by a decorator, so autofixture can't resolve its bare names"


# runtest_call, not pyfunc_call: plugins like pytest-asyncio wrap item.obj
# inside runtest(), so the swap has to happen first
@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    # e.g. pytest-mypy or yaml-collected items: no Python function to rebind
    if not isinstance(item, pytest.Function):
        return (yield)

    decorated = _check_decorated(item)
    try:
        return (yield from _swap(item, "obj", item._request))
    except NameError as e:
        if decorated:
            e.add_note(f"{_decorated_message(item)}: declare the fixtures it uses as parameters")
        raise


# the request here is the fixture's own SubRequest, so lookups get pytest's
# scope checks and resolve overrides from the requesting test's position.
# tryfirst: rebind the user's function before plugins like pytest-asyncio wrap it.
@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_fixture_setup(fixturedef, request):
    return (yield from _swap(fixturedef, "func", request))
