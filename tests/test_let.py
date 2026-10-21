import pytest

from pytest_autofixture import let

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
