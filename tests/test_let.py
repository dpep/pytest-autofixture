import pytest

from pytest_autofixture import let

# `name` comes from tests/conftest.py

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


def helper():
    return answer


def test_helpers_do_not_see_lets():
    assert answer  # resolved for the test itself
    with pytest.raises(NameError):
        helper()


class TestLetContainer:
    let.items = [[]]

    # each test appends, so a shared list would fail whichever runs second
    def test_first(self):
        items[0].append(1)
        assert items == [[1]]

    def test_second(self):
        items[0].append(1)
        assert items == [[1]]


def test_let_builtin_name():
    with pytest.raises(TypeError, match="builtin"):

        class _:
            let.id = 5
