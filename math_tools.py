"""Exact (SymPy) integration tools for the Cubik-Lite multi-agent tutor.

The agents explain and write the step-by-step reasoning, but final results and
the verdict on a student's answer come from here, so they don't depend on what
the model thinks. See docs/en/multi_agent_design.md, section 3.

Expressions arrive as text. The parser accepts SymPy syntax ("x*exp(x)") and
common student notation: "^" for powers, implicit multiplication ("2x",
"x sin(x)"), "e" for Euler's number and "ln" for the natural log. Every tool
returns the expression it interpreted, so the agent can show it to the student
and a mistranslation is visible instead of silently checking something else.
"""

from sympy import (
    E,
    Expr,
    Integral,
    Symbol,
    diff,
    integrate,
    log,
    nan,
    pi,
    simplify,
    zoo,
)
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

# Points where a non-simplifiable difference is evaluated numerically. Away from
# 0 and negative numbers so log/sqrt stay defined for typical exercises.
SAMPLE_POINTS = (0.37, 0.81, 1.29, 1.93, 2.61)
TOLERANCE = 1e-9


class ParseError(ValueError):
    """Raised when a math expression can't be parsed."""


def parse(expression: str, variable: Symbol) -> Expr:
    """Parse a math expression written in SymPy syntax or common student notation.

    Args:
        expression: The expression as text, e.g. "x^2 e^x" or "x**2*exp(x)".
        variable: The integration variable, so "x" is always that symbol.

    Returns:
        The parsed SymPy expression.

    Raises:
        ParseError: If the text is not a valid expression.
    """
    local_dict = {variable.name: variable, "e": E, "ln": log, "pi": pi}
    try:
        return parse_expr(
            expression, local_dict=local_dict, transformations=TRANSFORMATIONS
        )
    except Exception as e:  # parse_expr raises SyntaxError, TokenError, TypeError...
        raise ParseError(
            f"Could not parse the expression {expression!r}: {e}"
        ) from e


def _numeric_difference(expr: Expr, variable: Symbol) -> list[float]:
    """Evaluate expr at the sample points, skipping points where it is undefined."""
    values = []
    for point in SAMPLE_POINTS:
        value = expr.subs(variable, point).evalf()
        if value.has(nan, zoo) or not value.is_number:
            continue
        values.append(abs(complex(value)))
    return values


def _verdict(difference: Expr, variable: Symbol | None = None) -> str:
    """Decide whether two expressions are equal from their difference.

    "correct" only when SymPy proves the difference is 0, "incorrect" when it is
    clearly non-zero at some point, and "unconfirmed" otherwise: simplify() can
    fail to prove some valid equivalences (often trigonometric ones), and a
    correct answer must not be marked wrong because of that.
    """
    if simplify(difference) == 0:
        return "correct"
    if variable is None or not difference.has(variable):
        values = [abs(complex(difference.evalf()))]
    else:
        values = _numeric_difference(difference, variable)
    if any(v > TOLERANCE for v in values):
        return "incorrect"
    return "unconfirmed"


def solve_integral(
    integrand: str,
    variable: str = "x",
    lower: str | None = None,
    upper: str | None = None,
) -> dict:
    """Compute an integral exactly with SymPy. Give both limits for a definite integral, none for an indefinite one.

    Args:
        integrand: The function to integrate, e.g. "x*exp(x)" or "x^2 sin(x)".
        variable: The integration variable.
        lower: Lower limit of a definite integral, e.g. "0". Omit for an indefinite integral.
        upper: Upper limit of a definite integral, e.g. "pi". Omit for an indefinite integral.

    Returns:
        For an indefinite integral, the "antiderivative" (without + C). For a
        definite one, the exact "value" and its "approximation". If SymPy finds
        no closed form, "closed_form" is false. On bad input, an "error".
    """
    x = Symbol(variable)
    if (lower is None) != (upper is None):
        return {
            "error": "A definite integral needs both limits (lower and upper)."
        }
    try:
        f = parse(integrand, x)
        bounds = (parse(lower, x), parse(upper, x)) if lower is not None else None
    except ParseError as e:
        return {"error": str(e)}

    result = {"interpreted_integrand": str(f), "variable": variable}
    if bounds is None:
        antiderivative = integrate(f, x)
        if antiderivative.has(Integral):
            return {**result, "closed_form": False}
        return {**result, "closed_form": True, "antiderivative": str(antiderivative)}

    value = integrate(f, (x, *bounds))
    result["interpreted_limits"] = [str(b) for b in bounds]
    if value.has(Integral):
        approximation = Integral(f, (x, *bounds)).evalf()
        return {**result, "closed_form": False, "approximation": str(approximation)}
    return {
        **result,
        "closed_form": True,
        "value": str(value),
        "approximation": str(value.evalf()),
    }


def check_antiderivative(integrand: str, candidate: str, variable: str = "x") -> dict:
    """Check whether a candidate is an antiderivative of the integrand, by differentiating it with SymPy.

    The constant of integration doesn't matter: "+ C" (or any constant) has derivative 0.

    Args:
        integrand: The function that was integrated, e.g. "x*exp(x)".
        candidate: The proposed antiderivative, e.g. "x e^x - e^x + C".
        variable: The integration variable.

    Returns:
        A "verdict" ("correct", "incorrect" or "unconfirmed" when SymPy can't
        prove it either way), the interpreted expressions, and the candidate's
        derivative to explain a mistake. On bad input, an "error".
    """
    x = Symbol(variable)
    try:
        f = parse(integrand, x)
        candidate_expr = parse(candidate, x)
    except ParseError as e:
        return {"error": str(e)}

    derivative = diff(candidate_expr, x)
    return {
        "verdict": _verdict(derivative - f, x),
        "interpreted_integrand": str(f),
        "interpreted_candidate": str(candidate_expr),
        "candidate_derivative": str(simplify(derivative)),
    }


def check_definite_integral(
    integrand: str, lower: str, upper: str, candidate: str, variable: str = "x"
) -> dict:
    """Check a proposed value for a definite integral against the exact value computed with SymPy.

    Args:
        integrand: The function that was integrated, e.g. "sin(x)".
        lower: Lower limit, e.g. "0".
        upper: Upper limit, e.g. "pi".
        candidate: The proposed value, e.g. "2".
        variable: The integration variable.

    Returns:
        A "verdict" ("correct", "incorrect" or "unconfirmed"), the exact value and
        its approximation, and the interpreted expressions. On bad input, an "error".
    """
    x = Symbol(variable)
    try:
        f = parse(integrand, x)
        a, b = parse(lower, x), parse(upper, x)
        candidate_expr = parse(candidate, x)
    except ParseError as e:
        return {"error": str(e)}
    if candidate_expr.free_symbols:
        return {
            "error": f"The value of a definite integral must be a number, not {candidate!r}."
        }

    exact = integrate(f, (x, a, b))
    if exact.has(Integral):
        exact = Integral(f, (x, a, b)).evalf()
    return {
        "verdict": _verdict(candidate_expr - exact),
        "exact_value": str(exact),
        "approximation": str(exact.evalf()),
        "interpreted_integrand": str(f),
        "interpreted_limits": [str(a), str(b)],
        "interpreted_candidate": str(candidate_expr),
    }
