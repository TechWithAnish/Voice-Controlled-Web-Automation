"""Safe construction of XPath string literals.

XPath 1.0 has no escape sequence for quotes inside a string literal, so a
spoken phrase containing an apostrophe -- "don't have an account", which
speech recognition produces constantly -- turns an interpolated expression
into a syntax error.  The standard workaround is ``concat()``.
"""

from __future__ import annotations

_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LOWER = "abcdefghijklmnopqrstuvwxyz"


def xpath_literal(value: str) -> str:
    """Return ``value`` as an XPath 1.0 string literal.

    >>> xpath_literal("sign in")
    "'sign in'"
    >>> xpath_literal("don't")
    '"don\\'t"'
    >>> xpath_literal(\"\"\"mix 'single' and "double"\"\"\")
    'concat(\\'mix \\', "\\'", \\'single\\', "\\'", \\' and "double"\\')'
    """
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"


def lowercase_expr(expression: str) -> str:
    """Wrap ``expression`` in an XPath 1.0 case-folding ``translate()``.

    XPath 1.0 has no ``lower-case()``; ``translate()`` is the portable
    equivalent and is what every browser's engine supports.
    """
    return f"translate({expression}, '{_UPPER}', '{_LOWER}')"
