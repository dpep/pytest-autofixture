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

    A lambda is called on first use, at most once per test; any other value is
    shared by every test, so mutable containers must be wrapped in a lambda.
    """

    def __setattr__(self, name, value):
        frame = sys._getframe(1)
        # a function's locals are gone once it returns, and pytest never sees them
        if frame.f_code.co_flags & inspect.CO_OPTIMIZED:
            raise TypeError(f"let.{name} must be set at module or class level")
        # builtins resolve before fixtures, so the let would never be seen
        if hasattr(builtins, name):
            raise TypeError(f"let.{name} would be hidden by the builtin {name!r}")

        if isinstance(value, types.LambdaType) and value.__name__ == "<lambda>":
            if inspect.signature(value).parameters:
                raise TypeError(f"let.{name} lambda takes no arguments; use bare names instead")
            factory = value
        elif isinstance(value, (list, dict, set, bytearray)):
            raise TypeError(
                f"let.{name} = {value!r} would be shared by every test; "
                f"use let.{name} = lambda: {value!r}"
            )
        else:
            factory = lambda: value  # noqa: E731

        # stored under another name so `role` stays undefined at import: a
        # forgotten lambda or a helper reading it raises NameError instead of
        # getting the fixture object. staticmethod so a let in a test class
        # isn't bound to the instance.
        frame.f_locals[f"_let_{name}"] = pytest.fixture(staticmethod(factory), name=name)


let = _Let()


def _module_value(module, name):
    """A module global, unless it's a fixture object, whose value should win."""
    value = module[name]
    if isinstance(value, FixtureFunctionDefinition):
        raise KeyError(name)
    return value


class _FixtureBuiltins(dict):
    """Builtins for one test call: real builtins first, then fixtures."""

    def __init__(self, request, module):
        super().__init__(vars(builtins))
        self._request = request
        self._module = module

    def __missing__(self, name):
        # LOAD_NAME (class bodies, exec) reads globals without __getitem__, so
        # module globals can land here; read them live, without caching
        try:
            return _module_value(self._module, name)
        except KeyError:
            pass

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


_MODULE_DUNDERS = (
    "__name__",
    "__qualname__",
    "__doc__",
    "__package__",
    "__loader__",
    "__spec__",
    "__file__",
    "__cached__",
    "__path__",
)


class _LiveGlobals(dict):
    """A function's module globals, read live, with fixture objects hidden.

    Reads go through __getitem__ (globals that aren't an exact dict take the slow
    path), so rebinds by helpers or monkeypatch are seen. Hiding a fixture object
    raises KeyError, which falls through to builtins and then to the fixture.
    STORE_GLOBAL bypasses __setitem__, so `global` writes land here until
    write_back copies them to the module.
    """

    def __init__(self, module, request):
        # C code reads these directly, without __getitem__ (e.g. __name__ for
        # the __module__ of functions and classes made in the test)
        super().__init__({k: module[k] for k in _MODULE_DUNDERS if k in module})
        # functions take builtins from their globals when created (3.10+), so
        # lambdas, nested defs and genexprs inside the test inherit the fallback
        self["__builtins__"] = _FixtureBuiltins(request, module)
        self._module = module

    def __getitem__(self, name):
        try:
            return super().__getitem__(name)
        except KeyError:
            return _module_value(self._module, name)

    def write_back(self):
        for name, value in self.items():
            if not name.startswith("__"):
                self._module[name] = value


def _swap(obj, attr, request):
    """Temporarily replace obj.<attr> with a rebound copy, if it's a function."""
    original = getattr(obj, attr, None)
    # staticmethod is a module-level let: unwrapped, a plain function is never
    # bound to a test instance
    func = getattr(original, "__func__", original)
    if not isinstance(func, types.FunctionType):
        return (yield)

    namespace = _LiveGlobals(func.__globals__, request)
    rebound = types.FunctionType(
        func.__code__, namespace, func.__name__, func.__defaults__, func.__closure__
    )
    rebound.__kwdefaults__ = func.__kwdefaults__
    rebound.__dict__.update(func.__dict__)
    if isinstance(original, types.MethodType):
        rebound = types.MethodType(rebound, original.__self__)

    setattr(obj, attr, rebound)
    try:
        return (yield)
    finally:
        setattr(obj, attr, original)
        namespace.write_back()


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


# pytest rejects parametrizing a name the test doesn't declare, so add the
# parametrized names to the fixtures it requests before pytest's own hook runs
@pytest.hookimpl(tryfirst=True)
def pytest_generate_tests(metafunc):
    for marker in metafunc.definition.iter_markers("parametrize"):
        argnames = marker.args[0] if marker.args else marker.kwargs.get("argnames", ())
        if isinstance(argnames, str):
            argnames = [name.strip() for name in argnames.split(",") if name.strip()]
        for name in argnames:
            if name not in metafunc.fixturenames:
                metafunc.fixturenames.append(name)
