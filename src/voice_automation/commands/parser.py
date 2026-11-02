"""Ordered, anchored rule-based command parsing.

The original implementation matched commands with substring tests
(``if "back" in command``).  That is unsafe because English words contain
one another: "search for laptop" contains "top", "open closet" contains
"close", "set a timer" contains "time".  Each of those silently triggered
the wrong action -- in the worst case quitting the application.

Every rule here is therefore a fully anchored regular expression evaluated
against a normalised utterance, and the rules are tried in a fixed order so
that specific patterns win over general ones.  No rule can fire on an
accidental substring.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from re import Pattern
from typing import NamedTuple

from .models import Command, Intent

__all__ = ["CommandParser", "normalise", "words_to_number"]


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

_FILLER_PREFIX = re.compile(
    r"^(?:"
    r"please|hey|ok(?:ay)?|um+|uh+|"
    r"can\s+you|could\s+you|would\s+you|will\s+you|"
    r"i\s+(?:want|need)\s+(?:you\s+)?to|i'?d\s+like\s+(?:you\s+)?to|"
    r"let'?s|try\s+to"
    r")\s+",
    re.IGNORECASE,
)
_FILLER_SUFFIX = re.compile(r"\s+(?:please|thanks|thank\s+you|for\s+me)$", re.IGNORECASE)
_PUNCTUATION_EDGE = re.compile(r"^[\s\"'“‘(]+|[\s\"'”’).,!?;:]+$")

_UNITS: Mapping[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}
_TENS: Mapping[str, int] = {
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_SCALES: Mapping[str, int] = {"hundred": 100, "thousand": 1000}
#: Words that carry a value on their own.
_CORE_NUMBER_WORDS = set(_UNITS) | set(_TENS) | set(_SCALES)
#: Words permitted inside a number phrase but meaningless alone.
_CONNECTOR_WORDS = {"and", "a"}
_NUMBER_WORDS = _CORE_NUMBER_WORDS | _CONNECTOR_WORDS


def words_to_number(text: str) -> int | None:
    """Convert a spoken number such as "three hundred" into ``300``.

    Returns ``None`` when ``text`` is not entirely a number phrase.
    """
    words = [w for w in re.split(r"[\s-]+", text.strip().lower()) if w]
    if not words or any(word not in _NUMBER_WORDS for word in words):
        return None
    if not any(word in _CORE_NUMBER_WORDS for word in words):
        return None

    total = 0
    current = 0
    seen_value = False
    for word in words:
        if word == "and":
            continue
        if word == "a":
            current = max(current, 1)
            seen_value = True
        elif word in _UNITS:
            current += _UNITS[word]
            seen_value = True
        elif word in _TENS:
            current += _TENS[word]
            seen_value = True
        elif word == "hundred":
            current = max(current, 1) * 100
            seen_value = True
        elif word == "thousand":
            total += max(current, 1) * 1000
            current = 0
            seen_value = True
    return total + current if seen_value else None


#: Scroll commands are the only place a spoken number is meaningful, so the
#: rewrite is scoped to them rather than applied to every utterance.
_SCROLL_AMOUNT_RE = re.compile(
    r"^(?P<head>(?:scroll|page|move|go)\s+(?:up|down)\s+(?:by\s+)?)"
    r"(?P<amount>[a-z\s-]+?)"
    r"(?P<tail>\s*(?:pixels?|px))?$",
    re.IGNORECASE,
)


def _substitute_spoken_numbers(text: str) -> str:
    """Rewrite "scroll down two hundred" as "scroll down 200".

    Leaves every other utterance untouched.
    """
    match = _SCROLL_AMOUNT_RE.match(text)
    if match is None:
        return text
    value = words_to_number(match.group("amount"))
    if value is None:
        return text
    return f"{match.group('head')}{value}{match.group('tail') or ''}"


def normalise(utterance: str) -> str:
    """Canonicalise an utterance before matching.

    Lower-cases, folds Unicode, collapses whitespace, strips edge
    punctuation and conversational filler, and rewrites spoken numbers as
    digits.  Punctuation inside the phrase is preserved because it carries
    meaning for URLs.
    """
    text = unicodedata.normalize("NFKC", utterance or "")
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"\s+", " ", text).strip().lower()
    text = _PUNCTUATION_EDGE.sub("", text)

    previous = None
    while previous != text:
        previous = text
        text = _FILLER_PREFIX.sub("", text, count=1).strip()
        text = _FILLER_SUFFIX.sub("", text, count=1).strip()

    text = _PUNCTUATION_EDGE.sub("", text)
    return _substitute_spoken_numbers(text).strip()


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


class Rule(NamedTuple):
    """One anchored pattern mapped to an intent."""

    intent: Intent
    pattern: Pattern[str]


def _rule(intent: Intent, *patterns: str) -> list[Rule]:
    return [Rule(intent, re.compile(p, re.IGNORECASE)) for p in patterns]


# Order matters: the first match wins, so narrower rules come first.
RULES: tuple[Rule, ...] = tuple(
    # -- lifecycle ---------------------------------------------------------
    _rule(
        Intent.EXIT,
        r"^(?:exit|quit|bye|goodbye|good\s+bye)$",
        r"^(?:close|stop|shut\s*down|end|terminate)"
        r"(?:\s+(?:the\s+)?"
        r"(?:browser|assistant|app|application|program|session|window|tab))?$",
        r"^that'?s\s+all$",
        r"^i'?m\s+done$",
    )
    + _rule(
        Intent.HELP,
        r"^(?:help|help\s+me)$",
        r"^(?:what\s+can\s+you\s+do|what\s+are\s+your\s+commands)$",
        r"^(?:list\s+|show\s+)?commands$",
    )
    # -- information -------------------------------------------------------
    + _rule(
        Intent.TIME,
        r"^(?:what(?:'s|\s+is)\s+)?(?:the\s+)?(?:current\s+)?time(?:\s+is\s+it)?$",
        r"^what\s+time\s+is\s+it(?:\s+now)?$",
        r"^tell\s+me\s+the\s+time$",
    )
    + _rule(
        Intent.DATE,
        r"^(?:what(?:'s|\s+is)\s+)?(?:the\s+|today'?s\s+)?date(?:\s+today)?$",
        r"^what\s+day\s+is\s+it(?:\s+today)?$",
    )
    + _rule(
        Intent.WEATHER,
        r"^(?:what(?:'s|\s+is)\s+the\s+)?weather"
        r"(?:\s+(?:like|forecast|report))?"
        r"(?:\s+(?:in|at|for|near))\s+(?P<arg>.+)$",
        r"^weather\s+(?P<arg>.+)$",
    )
    + _rule(
        Intent.WEATHER,
        r"^(?:what(?:'s|\s+is)\s+the\s+)?weather(?:\s+(?:like|now|today|outside))?$",
    )
    + _rule(
        Intent.WHERE_AM_I,
        r"^(?:where\s+am\s+i|what(?:'s|\s+is)\s+(?:the\s+)?(?:current\s+)?(?:url|page|address))$",
        r"^(?:read|tell\s+me)\s+the\s+(?:url|address)$",
    )
    # -- scrolling (absolute before relative) ------------------------------
    + _rule(
        Intent.SCROLL_BOTTOM,
        r"^(?:scroll\s+|go\s+|jump\s+)?(?:to\s+)?(?:the\s+)?bottom(?:\s+of\s+(?:the\s+)?page)?$",
        r"^(?:end|bottom)\s+of\s+(?:the\s+)?page$",
    )
    + _rule(
        Intent.SCROLL_TOP,
        r"^(?:scroll\s+|go\s+|jump\s+)?(?:to\s+)?(?:the\s+)?top(?:\s+of\s+(?:the\s+)?page)?$",
        r"^(?:start|top)\s+of\s+(?:the\s+)?page$",
    )
    + _rule(
        Intent.SCROLL_DOWN,
        r"^(?:scroll|page|move|go)\s+down"
        r"(?:\s+(?:by\s+)?(?P<amount>\d{1,6})(?:\s*(?:pixels?|px))?)?$",
    )
    + _rule(
        Intent.SCROLL_UP,
        r"^(?:scroll|page|move|go)\s+up"
        r"(?:\s+(?:by\s+)?(?P<amount>\d{1,6})(?:\s*(?:pixels?|px))?)?$",
    )
    # -- history -----------------------------------------------------------
    + _rule(
        Intent.BACK,
        r"^(?:go\s+back|back|navigate\s+back|previous\s+page|go\s+to\s+(?:the\s+)?previous\s+page)$",
    )
    + _rule(
        Intent.FORWARD,
        r"^(?:go\s+forward|forward|navigate\s+forward|next\s+page)$",
    )
    + _rule(
        Intent.REFRESH,
        r"^(?:refresh|reload)(?:\s+(?:the\s+)?page)?$",
    )
    # -- site-scoped search (before the generic search rule) ---------------
    + _rule(
        Intent.SEARCH_AMAZON,
        r"^(?:search\s+)?(?:on\s+)?amazon\s+(?:for\s+)?(?P<arg>.+)$",
        r"^search\s+(?:for\s+)?(?P<arg>.+?)\s+on\s+amazon$",
        r"^(?:buy|shop\s+for|order)\s+(?P<arg>.+)$",
    )
    + _rule(
        Intent.SEARCH_YOUTUBE,
        r"^(?:search\s+)?(?:on\s+)?youtube\s+(?:for\s+)?(?P<arg>.+)$",
        r"^(?:search|play|find)\s+(?:for\s+)?(?P<arg>.+?)\s+on\s+youtube$",
    )
    + _rule(
        Intent.SEARCH_WIKIPEDIA,
        r"^(?:search\s+)?(?:on\s+)?wikipedia\s+(?:for\s+)?(?P<arg>.+)$",
        r"^(?:search|look\s+up)\s+(?:for\s+)?(?P<arg>.+?)\s+on\s+wikipedia$",
        r"^who\s+(?:is|was)\s+(?P<arg>.+)$",
    )
    # -- generic search ----------------------------------------------------
    + _rule(
        Intent.SEARCH_WEB,
        r"^(?:search\s+the\s+web|look\s+up|search|google|find)\s+(?:for\s+)?(?P<arg>.+)$",
    )
    # -- page interaction --------------------------------------------------
    + _rule(
        Intent.CLICK,
        r"^(?:click|press|tap|select|choose)(?:\s+(?:on|the))*\s+(?P<arg>.+)$",
    )
    # -- navigation (last: "open" is a greedy catch-all) -------------------
    + _rule(
        Intent.OPEN,
        r"^(?:open|go\s+to|navigate\s+to|visit|launch|browse\s+to|take\s+me\s+to)"
        r"(?:\s+the)?\s+(?P<arg>.+)$",
    )
)

#: Canonical phrasings offered as "did you mean ...?" suggestions.
EXAMPLE_PHRASES: tuple[str, ...] = (
    "open youtube",
    "go to example.com",
    "search for python tutorials",
    "search amazon for headphones",
    "search youtube for jazz",
    "click on sign in",
    "scroll down 400",
    "scroll up",
    "scroll to bottom",
    "go back",
    "go forward",
    "refresh the page",
    "what time is it",
    "weather in london",
    "where am i",
    "help",
    "exit",
)

#: Minimum fuzzy score (0-100) before a suggestion is offered.
SUGGESTION_THRESHOLD = 72


class CommandParser:
    """Translate utterances into :class:`Command` objects.

    Parameters
    ----------
    known_sites:
        Shorthand site names.  A bare site name ("youtube") is treated as an
        implicit "open youtube".
    rules:
        Override the rule table; used by tests.
    suggestion_threshold:
        Fuzzy-match score above which an unrecognised utterance produces a
        "did you mean" suggestion.
    """

    def __init__(
        self,
        known_sites: Iterable[str] | None = None,
        rules: Sequence[Rule] | None = None,
        suggestion_threshold: int = SUGGESTION_THRESHOLD,
        examples: Sequence[str] = EXAMPLE_PHRASES,
    ) -> None:
        self._sites = {s.lower() for s in (known_sites or ())}
        self._rules = tuple(rules if rules is not None else RULES)
        self._threshold = suggestion_threshold
        self._examples = tuple(examples)

    # ------------------------------------------------------------------
    def parse(self, utterance: str) -> Command:
        """Parse ``utterance``; never raises."""
        raw = (utterance or "").strip()
        text = normalise(raw)
        if not text:
            return Command(Intent.UNKNOWN, raw=raw)

        for rule in self._rules:
            match = rule.pattern.match(text)
            if match is None:
                continue
            groups = match.groupdict()
            argument = (groups.get("arg") or "").strip() or None
            amount_text = groups.get("amount")
            amount = int(amount_text) if amount_text and amount_text.isdigit() else None
            return Command(
                intent=rule.intent, raw=raw, argument=argument, amount=amount
            )

        # A bare shorthand ("youtube") means "open youtube".
        if text in self._sites:
            return Command(Intent.OPEN, raw=raw, argument=text)

        return Command(Intent.UNKNOWN, raw=raw, suggestion=self._suggest(text))

    # ------------------------------------------------------------------
    def _suggest(self, text: str) -> str | None:
        """Return the closest canonical phrase, if any is close enough."""
        try:  # pragma: no cover - exercised indirectly
            from rapidfuzz import process
        except ImportError:  # pragma: no cover - optional at runtime
            return None

        best = process.extractOne(text, self._examples, score_cutoff=self._threshold)
        return best[0] if best else None
