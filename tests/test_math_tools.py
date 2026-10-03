"""Tests for the SymPy integration tools in math_tools.py.

Everything here is exact symbolic math, so no model or embedding provider is
needed.
"""

import pytest

import math_tools


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("x*exp(x)", "x*exp(x)"),
        ("x^2", "x**2"),
        ("2x", "2*x"),
        ("e^x", "exp(x)"),
        ("ln(x)", "log(x)"),
        ("x sin(x)", "x*sin(x)"),
    ],
)
def test_parse_accepts_student_notation(text: str, expected: str) -> None:
    """Verify "^", implicit multiplication, e and ln are read the way a student means them."""
    x = math_tools.Symbol("x")
    assert str(math_tools.parse(text, x)) == expected


def test_parse_rejects_invalid_expression() -> None:
    """Verify malformed text raises ParseError instead of a raw SymPy exception."""
    with pytest.raises(math_tools.ParseError):
        math_tools.parse("x^^2 +", math_tools.Symbol("x"))


def test_solve_indefinite_integral() -> None:
    """Verify an indefinite integral returns its antiderivative without + C."""
    result = math_tools.solve_integral("x e^x")

    assert result["closed_form"] is True
    assert result["antiderivative"] == "(x - 1)*exp(x)"
    assert result["interpreted_integrand"] == "x*exp(x)"


def test_solve_definite_integral() -> None:
    """Verify a definite integral returns the exact value and its approximation."""
    result = math_tools.solve_integral("sin(x)", lower="0", upper="pi")

    assert result["closed_form"] is True
    assert result["value"] == "2"
    assert result["interpreted_limits"] == ["0", "pi"]


def test_solve_integral_without_closed_form() -> None:
    """Verify an integral SymPy can't evaluate is flagged instead of invented."""
    result = math_tools.solve_integral("sin(x)/log(x)")

    assert result["closed_form"] is False
    assert "antiderivative" not in result


def test_solve_integral_needs_both_limits() -> None:
    """Verify a single limit is rejected rather than treated as indefinite."""
    assert "error" in math_tools.solve_integral("x", lower="0")


def test_solve_integral_reports_parse_errors() -> None:
    """Verify bad input comes back as an error the agent can relay."""
    assert "error" in math_tools.solve_integral("x^^2 +")


@pytest.mark.parametrize(
    "candidate",
    [
        "x e^x - e^x + C",  # student notation, with constant
        "(x - 1)*exp(x)",  # factored form
        "x*exp(x) - exp(x) + 7",  # any constant works
    ],
)
def test_check_antiderivative_correct(candidate: str) -> None:
    """Verify equivalent answers are accepted regardless of form or constant."""
    result = math_tools.check_antiderivative("x*exp(x)", candidate)

    assert result["verdict"] == "correct"


def test_check_antiderivative_incorrect_returns_derivative() -> None:
    """Verify a wrong answer is rejected and its derivative is returned to explain why."""
    result = math_tools.check_antiderivative("x*exp(x)", "x e^x + e^x")

    assert result["verdict"] == "incorrect"
    assert result["candidate_derivative"] == "(x + 2)*exp(x)"


def test_check_antiderivative_trig_identity() -> None:
    """Verify answers that differ by a trig identity are still recognized as correct."""
    result = math_tools.check_antiderivative("sin(2x)", "sin(x)^2")

    assert result["verdict"] == "correct"


def test_check_antiderivative_reports_parse_errors() -> None:
    """Verify an unreadable candidate comes back as an error, not a verdict."""
    result = math_tools.check_antiderivative("x", "x^^2 +")

    assert "error" in result
    assert "verdict" not in result


def test_check_definite_integral_correct() -> None:
    """Verify an exact value written differently is accepted."""
    result = math_tools.check_definite_integral("x^2", "0", "3", "27/3")

    assert result["verdict"] == "correct"
    assert result["exact_value"] == "9"


def test_check_definite_integral_incorrect() -> None:
    """Verify a wrong value is rejected and the exact value is returned."""
    result = math_tools.check_definite_integral("sin(x)", "0", "pi", "1")

    assert result["verdict"] == "incorrect"
    assert result["exact_value"] == "2"


def test_check_definite_integral_rejects_non_numeric_candidate() -> None:
    """Verify an antiderivative given as the value of a definite integral is an error."""
    assert "error" in math_tools.check_definite_integral("x", "0", "1", "x^2/2")


def test_verdict_is_unconfirmed_when_not_provable_but_numerically_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a difference simplify() can't prove but that is 0 numerically is not marked wrong."""
    x = math_tools.Symbol("x")
    hidden_zero = math_tools.parse("sin(x)^2 + cos(x)^2 - 1", x)
    # Simulate simplify() failing to prove the identity.
    monkeypatch.setattr(math_tools, "simplify", lambda expr: expr)

    assert math_tools._verdict(hidden_zero, x) == "unconfirmed"
