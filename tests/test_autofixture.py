import pytest


@pytest.fixture
def one():
    return 1


@pytest.fixture
def two():
    return 2


@pytest.fixture
def three(one, two):
    return one + two


def test_explicit(one):
    assert one == 1


def test_implicit():
    assert one == 1
    assert three == 3


def test_unknown_name_is_still_a_name_error():
    with pytest.raises(NameError, match="no_such_thing"):
        no_such_thing


@pytest.fixture
def run(pytester):
    pytester.makeconftest("""
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
    """)

    def run(source):
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


def test_closest_override_wins(run):
    result = run("""
        import pytest

        @pytest.fixture
        def name():
            return "module"

        def test_module():
            assert name == "module"

        class TestClass:
            @pytest.fixture
            def name(self):
                return "class"

            def test_class(self):
                assert name == "class"
    """)
    result.assert_outcomes(passed=2)


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


def test_edge_cases(run):
    result = run("""
        import types
        import pytest

        @pytest.fixture
        def zero():
            return 0

        def helper():
            return name

        def test_falsy_values():
            assert zero == 0

        def test_nested_scopes():
            assert (lambda: name)() == "conftest"
            assert list(name for _ in range(1)) == ["conftest"]

        def test_helpers_do_not_see_fixtures():
            assert name
            with pytest.raises(NameError):
                helper()

        def test_attribute_named_like_a_fixture():
            obj = types.SimpleNamespace(counter="attr")
            assert obj.counter == "attr"

        def test_builtin_fixtures():
            tmp_path.joinpath("x").write_text("hi")
    """)
    result.assert_outcomes(passed=5)


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
