"""Browser automation layer."""

from __future__ import annotations

from .browsers import (
    CHROMIUM_FAMILY,
    BrowserInfo,
    BrowserKind,
    discover,
    find_browser,
    resolve_browser,
)
from .controller import BrowserController, ScrollDirection
from .xpath import xpath_literal

__all__ = [
    "CHROMIUM_FAMILY",
    "BrowserController",
    "BrowserInfo",
    "BrowserKind",
    "ScrollDirection",
    "discover",
    "find_browser",
    "resolve_browser",
    "xpath_literal",
]
