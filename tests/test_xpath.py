"""XPath literal escaping."""

from __future__ import annotations

import pytest

from voice_automation.browser.xpath import lowercase_expr, xpath_literal


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("sign in", "'sign in'"),
        ("", "''"),
        ("don't", '"don\'t"'),
        ('say "hi"', "'say \"hi\"'"),
    ],
)
def test_simple_literals(value, expected):
    assert xpath_literal(value) == expected


def test_both_quote_kinds_use_concat():
    result = xpath_literal("""it's a "test\"""")
    assert result.startswith("concat(")
    assert "\"'\"" in result


def test_apostrophe_literals_are_wellformed():
    """An apostrophe used to produce an InvalidSelectorException at runtime."""
    import re

    # A well-formed XPath literal is a sequence of quoted chunks, optionally
    # joined by concat(); it must never contain an unbalanced quote.
    for value in ("don't", "it's", "O'Brien", """mix 'a' and "b\""""):
        literal = xpath_literal(value)
        chunks = re.findall(r"'[^']*'|\"[^\"]*\"", literal)
        assert "".join(
            chunk[1:-1] for chunk in chunks
        ) == value, f"round-trip failed for {value!r}"


def test_lowercase_expr_is_xpath1_compatible():
    expr = lowercase_expr("text()")
    assert expr.startswith("translate(text()")
    assert "lower-case" not in expr
