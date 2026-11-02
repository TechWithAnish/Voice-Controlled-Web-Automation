"""Value types produced by the command parser."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    """A recognised user intention."""

    OPEN = "open"
    SEARCH_WEB = "search_web"
    SEARCH_AMAZON = "search_amazon"
    SEARCH_YOUTUBE = "search_youtube"
    SEARCH_WIKIPEDIA = "search_wikipedia"
    CLICK = "click"
    SCROLL_DOWN = "scroll_down"
    SCROLL_UP = "scroll_up"
    SCROLL_TOP = "scroll_top"
    SCROLL_BOTTOM = "scroll_bottom"
    BACK = "back"
    FORWARD = "forward"
    REFRESH = "refresh"
    WHERE_AM_I = "where_am_i"
    TIME = "time"
    DATE = "date"
    WEATHER = "weather"
    HELP = "help"
    EXIT = "exit"
    UNKNOWN = "unknown"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


@dataclass(frozen=True)
class Command:
    """The parsed form of one utterance.

    ``argument`` carries the free-text payload (a site, a query, an element
    description).  ``amount`` carries a numeric payload such as a scroll
    distance.  ``suggestion`` is set on :attr:`Intent.UNKNOWN` when a close
    match was found, so the assistant can say "did you mean ...".
    """

    intent: Intent
    raw: str
    argument: str | None = None
    amount: int | None = None
    suggestion: str | None = None

    @property
    def recognised(self) -> bool:
        """True when the utterance mapped to an actionable intent."""
        return self.intent is not Intent.UNKNOWN
