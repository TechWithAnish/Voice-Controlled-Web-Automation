"""Shared fixtures and test doubles.

The whole suite runs without a browser, a microphone or network access:
every collaborator the assistant uses is replaced with a recording fake.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

import pytest

from voice_automation.browser import ScrollDirection
from voice_automation.config import Settings
from voice_automation.exceptions import ElementNotFoundError, WeatherError


class FakeSpeaker:
    """Records everything the assistant says."""

    def __init__(self) -> None:
        self.said: list[str] = []
        self.closed = False

    def say(self, text: str) -> None:
        self.said.append(text)

    def close(self) -> None:
        self.closed = True

    @property
    def transcript(self) -> str:
        return " | ".join(self.said)


class FakeListener:
    """Replays scripted utterances, then returns ``None`` forever."""

    def __init__(self, utterances: Sequence[str | None]) -> None:
        self._queue = list(utterances)
        self.closed = False

    def listen(self) -> str | None:
        if not self._queue:
            return "exit"
        item = self._queue.pop(0)
        if isinstance(item, BaseException):  # pragma: no cover - defensive
            raise item
        return item

    def close(self) -> None:
        self.closed = True


class RaisingListener:
    """Raises a given exception on every call; used for failure paths."""

    def __init__(self, error: BaseException, times: int = 1_000) -> None:
        self._error = error
        self._times = times
        self.calls = 0

    def listen(self) -> str | None:
        self.calls += 1
        if self.calls <= self._times:
            raise self._error
        return "exit"

    def close(self) -> None:
        return None


class FakeBrowser:
    """Records browser actions instead of driving Chrome."""

    def __init__(self, click_result: str | None = "the link") -> None:
        self.visited: list[str] = []
        self.scrolls: list[tuple] = []
        self.history: list[str] = []
        self.clicked: list[str] = []
        self.click_result = click_result
        self.page_title = "Example Domain"
        self.url = "https://example.com/"
        self.quit_calls = 0

    def go(self, url: str) -> None:
        self.visited.append(url)
        self.url = url

    def scroll(self, direction: ScrollDirection, pixels: int | None = None) -> None:
        self.scrolls.append((direction, pixels))

    def back(self) -> None:
        self.history.append("back")

    def forward(self) -> None:
        self.history.append("forward")

    def refresh(self) -> None:
        self.history.append("refresh")

    def click_text(self, description: str, timeout: float | None = None) -> str:
        self.clicked.append(description)
        if self.click_result is None:
            raise ElementNotFoundError(f"Could not find {description!r}")
        return self.click_result

    def current_url(self) -> str:
        return self.url

    def title(self) -> str:
        return self.page_title

    def quit(self) -> None:
        self.quit_calls += 1


class FakeWeather:
    """Returns a canned forecast or raises."""

    def __init__(self, result: str = "Sunny, +21C", error: str | None = None) -> None:
        self.result = result
        self.error = error
        self.requested: list[str] = []

    def summary(self, city: str) -> str:
        self.requested.append(city)
        if self.error:
            raise WeatherError(self.error)
        return self.result


FIXED_NOW = dt.datetime(2026, 11, 2, 14, 5, 0)


@pytest.fixture
def settings() -> Settings:
    """Deterministic settings with speech and file logging disabled."""
    return Settings(tts_enabled=False, headless=True, max_consecutive_failures=3)


@pytest.fixture
def speaker() -> FakeSpeaker:
    return FakeSpeaker()


@pytest.fixture
def browser() -> FakeBrowser:
    return FakeBrowser()


@pytest.fixture
def frozen_now():
    return lambda: FIXED_NOW
