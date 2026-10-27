# behavior that needs its own pytest session: state across tests,
# expected failures, and hooks that would affect the whole suite
import pytest

CONFTEST = """
        import itertools
        import pytest

        LOG = []
        _count = itertools.count(1)

        @pytest.fixture
        def counter():
            return next(_count)

        @pytest.fixture
        def name():
            return "conftest"
"""


@pytest.fixture
def run(pytester):
    def run(source, conftest=""):
        pytester.makeconftest(CONFTEST + conftest)
        pytester.makepyfile(source)
        return pytester.runpytest()

    return run


def test_fresh_value_per_test(run):
    result = run("""
        def test_1():
            assert counter == 1

        def test_2():
            assert counter == 2

        def test_explicit_param_is_not_stale(counter):
            assert counter == 3

        def test_memoized_within_a_test():
            assert counter == counter
    """)
    result.assert_outcomes(passed=4)


def test_lazy_setup_and_teardown(run):
    result = run("""
        import pytest
        from conftest import LOG

        @pytest.fixture
        def resource():
            LOG.append("setup")
            yield "r"
            LOG.append("teardown")

        def test_untaken_branch_skips_setup():
            if False:
                resource
            assert LOG == []

        def test_uses_it():
            assert resource == "r"

        def test_torn_down():
            assert LOG == ["setup", "teardown"]
    """)
    result.assert_outcomes(passed=3)


def test_respects_scope(run):
    result = run("""
        import itertools
        import pytest

        _count = itertools.count()

        @pytest.fixture(scope="session")
        def session_value():
            return next(_count)

        def test_1():
            assert session_value == 0

        def test_2():
            assert session_value == 0
    """)
    result.assert_outcomes(passed=2)


def test_missing_dependency_reports_the_dependency(run):
    result = run("""
        import pytest

        @pytest.fixture
        def broken(not_a_fixture):
            return 1

        def test_broken():
            broken
    """)
    result.assert_outcomes(errors=0, failed=1)
    result.stdout.fnmatch_lines(["*fixture 'not_a_fixture' not found*"])


def test_key_error_in_fixture_is_reported(run):
    result = run("""
        import pytest

        @pytest.fixture
        def config():
            return {}["db"]

        @pytest.fixture
        def client():
            return config

        def test_direct():
            config

        def test_through_fixture():
            client
    """)
    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(["*KeyError: 'db'*"])
    result.stdout.no_fnmatch_line("E *NameError*")


def test_fixture_body_teardown(run):
    result = run("""
        import pytest
        from conftest import LOG

        @pytest.fixture
        def resource():
            yield name
            LOG.append(f"teardown {name}")

        def test_uses_it():
            assert resource == "conftest"

        def test_torn_down():
            assert LOG == ["teardown conftest"]
    """)
    result.assert_outcomes(passed=2)


@pytest.mark.skipif(pytest.version_tuple < (9, 1), reason="pytest 9.1 refuses teardown lookups")
def test_first_lookup_during_teardown_reports_pytests_error(run):
    result = run("""
        import pytest

        @pytest.fixture
        def resource():
            yield
            name

        def test_uses_it():
            resource
    """)
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*not available during teardown*"])


def test_fixture_bodies_respect_scope(run):
    result = run("""
        import pytest

        @pytest.fixture(scope="session")
        def wide():
            return counter

        def test_scope_mismatch():
            wide
    """)
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*ScopeMismatch*"])


def test_fixture_bodies_under_other_wrappers(run):
    # mirrors pytest-asyncio, which wraps fixturedef.func and loads after us
    result = run(
        """
        import pytest

        @pytest.fixture
        def greeting():
            return f"hi {name}"

        def test_it():
            assert greeting == "hi conftest"
        """,
        conftest="""
        @pytest.hookimpl(wrapper=True)
        def pytest_fixture_setup(fixturedef, request):
            inner = fixturedef.func
            fixturedef.func = lambda *args, **kwargs: inner(*args, **kwargs)
            try:
                return (yield)
            finally:
                fixturedef.func = inner
        """,
    )
    result.assert_outcomes(passed=1)


def test_decorated_tests(run):
    result = run("""
        import types
        from unittest import mock

        import pytest

        @pytest.fixture
        def local():
            return 1

        @mock.patch("os.getcwd")
        def test_local_fixture(getcwd):
            assert local == 1

        @mock.patch("os.getcwd")
        def test_conftest_fixture(getcwd):
            assert name == "conftest"

        def given(test):
            # mimics hypothesis, which exposes the original but sets no __wrapped__
            def wrapper():
                return test()

            wrapper.hypothesis = types.SimpleNamespace(inner_test=test)
            return wrapper

        @given
        def test_hypothesis_style():
            assert local == 1

        @mock.patch("os.getcwd")
        def test_explicit_params(getcwd, local):
            obj = types.SimpleNamespace(name="attr")
            assert local == 1
            assert obj.name == "attr"
    """)
    result.assert_outcomes(passed=1, failed=3)
    result.stdout.fnmatch_lines(
        [
            "*test_local_fixture is wrapped by a decorator*declare 'local' as a parameter*",
            "*NameError*",
            "*test_conftest_fixture is wrapped by a decorator*",
            "*test_hypothesis_style is wrapped by a decorator*declare 'local' as a parameter*",
        ]
    )


def test_non_function_items(run, pytester):
    pytester.makefile(".yaml", spec="")
    result = run(
        """
        def test_it():
            assert name == "conftest"
        """,
        conftest="""
        class YamlItem(pytest.Item):
            def runtest(self):
                pass

        class YamlFile(pytest.File):
            def collect(self):
                yield YamlItem.from_parent(self, name="yaml_item")

        def pytest_collect_file(parent, file_path):
            if file_path.suffix == ".yaml":
                return YamlFile.from_parent(parent, path=file_path)
        """,
    )
    result.assert_outcomes(passed=2)


def test_module_globals_stay_live(run):
    result = run("""
        import sys

        import pytest

        COUNT = 0
        TIMEOUT = 30
        _state = None
        _conn = None

        def set_state():
            global _state
            _state = 1

        @pytest.fixture
        def conn():
            global _conn
            _conn = "open"
            return _conn

        def test_global_write():
            global COUNT
            COUNT += 1

        def test_global_write_persists():
            assert COUNT == 1

        def test_helper_rebinds_a_global():
            set_state()
            assert _state == 1

        def test_fixture_rebinds_a_global(conn):
            assert _conn == "open"

        def test_class_body_in_a_test():
            class Config:
                timeout = TIMEOUT
                who = name

            assert (Config.timeout, Config.who) == (30, "conftest")

        def test_monkeypatch_own_module(monkeypatch):
            monkeypatch.setattr(sys.modules[__name__], "TIMEOUT", 0)
            assert TIMEOUT == 0
            assert name == "conftest"

        @pytest.fixture
        def server():
            global _conn
            yield
            _conn = "closed"

        def test_teardown_writes_a_global(server):
            pass

        def test_teardown_write_persists():
            assert _conn == "closed"

        def test_private_global_write():
            global __private
            __private = 1

        def test_private_global_write_persists():
            assert __private == 1
    """)
    result.assert_outcomes(passed=10)


def test_let_forgotten_lambda_fails_at_import(run):
    result = run("""
        from pytest_autofixture import let

        let.role = "member"
        let.label = f"role={role}"

        def test_it():
            pass
    """)
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*NameError: name 'role' is not defined*"])


def test_threads_share_one_setup(run):
    result = run("""
        import time
        from concurrent.futures import ThreadPoolExecutor

        import pytest

        @pytest.fixture
        def slow():
            time.sleep(0.05)
            return object()

        def test_threads():
            with ThreadPoolExecutor(4) as pool:
                values = list(pool.map(lambda _: slow, range(4)))
            assert len({id(v) for v in values}) == 1
    """)
    result.assert_outcomes(passed=1)


def test_let_overrides(run, pytester):
    pytester.makepyfile(
        shared="""
        import pytest
        from pytest_autofixture import let

        @pytest.fixture
        def role():
            return "member"

        class Base:
            @pytest.fixture
            def level(self):
                return "member"

        class AdminMixin(Base):
            let.level = "admin"
        """
    )
    result = run("""
        import shared
        from shared import role
        from pytest_autofixture import let

        let.role = "admin"

        # the mixin is reached only through the module, so it's never collected
        class TestMixin(shared.AdminMixin):
            def test_mixin_let_beats_inherited_fixture(self):
                assert level == "admin"

        def test_let_redefines_imported_fixture():
            assert role == "admin"

        class TestDoor:
            def _let_in(self):
                return "welcome"

            def test_other_attributes_left_alone(self):
                assert self._let_in() == "welcome"
    """)
    result.assert_outcomes(passed=3)


def test_thread_in_fixture_setup_can_look_up(run):
    result = run("""
        import threading

        import pytest

        @pytest.fixture
        def port():
            return 8000

        @pytest.fixture
        def server():
            seen = []
            thread = threading.Thread(target=lambda: seen.append(port))
            thread.start()
            thread.join(timeout=2)
            return seen

        def test_server():
            assert server == [8000]
    """)
    result.assert_outcomes(passed=1)
