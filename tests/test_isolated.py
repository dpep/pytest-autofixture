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
