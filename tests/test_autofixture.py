import types

import pytest

from pytest_autofixture import let


@pytest.fixture
def one():
    return 1


@pytest.fixture
def two():
    return 2


@pytest.fixture
def three(one, two):
    return one + two


@pytest.fixture
def zero():
    return 0


@pytest.fixture
def role():
    return "member"


@pytest.fixture
def user():
    return f"{name}:{role}"


@pytest.fixture
def resource():
    yield user


def helper():
    return name


def test_explicit(one):
    assert one == 1


def test_implicit():
    assert one == 1
    assert three == 3


def test_conftest_fixture():
    assert name == "conftest"


def test_module_overrides_conftest():
    assert role == "member"


def test_unknown_name_is_still_a_name_error():
    with pytest.raises(NameError, match="no_such_thing"):
        no_such_thing


def test_falsy_values():
    assert zero == 0


def test_nested_scopes():
    assert (lambda: one)() == 1
    assert list(one for _ in range(1)) == [1]


def test_helpers_do_not_see_fixtures():
    assert name
    with pytest.raises(NameError):
        helper()


def test_attribute_named_like_a_fixture():
    obj = types.SimpleNamespace(one="attr")
    assert obj.one == "attr"


def test_builtin_fixtures():
    tmp_path.joinpath("x").write_text("hi")


def test_fixture_bodies():
    assert user == "conftest:member"
    assert resource == "conftest:member"


class TestOverride:
    @pytest.fixture
    def name(self):
        return "class"

    @pytest.fixture
    def role(self):
        return "admin"

    @pytest.fixture
    def badge(self):
        return f"{type(self).__name__}:{user}"

    def test_class_overrides_conftest(self):
        assert name == "class"

    def test_inner_override_reaches_outer_fixture(self):
        assert user == "class:admin"

    def test_method_fixture(self):
        assert badge == "TestOverride:class:admin"


let.greeting = lambda: f"hi {name}"
let.shout = lambda: greeting.upper()
let.answer = 42
let.model = dict


def test_let():
    assert greeting == "hi conftest"
    assert shout == "HI CONFTEST"


def test_let_constants():
    assert answer == 42
    assert model is dict


def test_let_as_parameter(greeting):
    assert greeting == "hi conftest"


def test_let_lambda_takes_no_arguments():
    with pytest.raises(TypeError, match="no arguments"):

        class _:
            let.bad = lambda x: x


def test_let_outside_module_or_class():
    with pytest.raises(TypeError, match="module or class"):
        let.bad = 1


class TestLet:
    let.name = "let"

    def test_override_reaches_outer_let(self):
        assert shout == "HI LET"
