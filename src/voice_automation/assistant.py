"""Orchestration: listen, parse, act, respond.

Every collaborator is injected, so the control flow -- including failure
handling and shutdown -- is testable with fakes and without a browser,
a microphone or a network connection.

Behavioural guarantees this layer provides:

*   one utterance can never terminate the process abruptly; ``run`` returns
    an exit code and the caller decides what to do with it;
*   a run of consecutive failures stops the assistant rather than letting it
    spin, which is what the original ``while True`` with a broad ``except``
    did when the browser died;
*   cleanup happens exactly once, on every exit path.
"""

from __future__ import annotations

import datetime as _datetime
import logging
from collections.abc import Callable

from .browser import BrowserController, ScrollDirection
from .commands import Command, CommandParser
from .config import Settings
from .exceptions import (
    BrowserError,
    BrowserUnavailableError,
    ElementNotFoundError,
    InvalidTargetError,
    SpeechServiceError,
    SpeechUnavailableError,
    VoiceAutomationError,
    WeatherError,
)
from .services import WeatherClient
from .speech import Listener, Speaker
from .urls import SITE_SEARCH, build_search_url, resolve_target

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_FAILURE = 1

GREETING = (
    "Hello. I can open sites, search the web, click things, scroll, and tell "
    "you the time or the weather. Say help for examples, or exit to stop."
)

HELP_TEXT = (
    "Try: open youtube. Go to example dot com. Search for python tutorials. "
    "Search amazon for headphones. Click on sign in. Scroll down 400. "
    "Scroll to bottom. Go back. Refresh. What time is it. Weather in London. "
    "Where am I. Exit."
)

class VoiceAssistant:
    """Wires the parser, browser, speech and services together."""

    def __init__(
        self,
        settings: Settings,
        browser: BrowserController,
        listener: Listener,
        speaker: Speaker,
        parser: CommandParser | None = None,
        weather: WeatherClient | None = None,
        now: Callable[[], _datetime.datetime] = _datetime.datetime.now,
    ) -> None:
        self.settings = settings
        self.browser = browser
        self.listener = listener
        self.speaker = speaker
        self.parser = parser or CommandParser(known_sites=_known_sites())
        self.weather = weather or WeatherClient(timeout=settings.weather_timeout)
        self._now = now
        self._running = False
        self._consecutive_failures = 0

    # -- lifecycle ------------------------------------------------------
    def request_stop(self) -> None:
        """Ask the main loop to finish after the current utterance.

        Safe to call from a signal handler.
        """
        self._running = False

    def run(self) -> int:
        """Run the command loop until the user exits or a fatal error occurs."""
        self._running = True
        self._consecutive_failures = 0
        self.speaker.say(GREETING)

        exit_code = EXIT_OK
        while self._running:
            try:
                utterance = self.listener.listen()
            except SpeechUnavailableError as exc:
                self.speaker.say("I can no longer hear you, so I am stopping.")
                logger.error("Microphone unavailable: %s", exc)
                exit_code = EXIT_FAILURE
                break
            except SpeechServiceError as exc:
                logger.warning("Speech service error: %s", exc)
                self.speaker.say("I cannot reach the speech service right now.")
                if self._register_failure():
                    exit_code = EXIT_FAILURE
                    break
                continue
            except KeyboardInterrupt:
                self.speaker.say("Stopping.")
                break

            if not utterance:
                continue

            try:
                keep_going = self.handle(self.parser.parse(utterance))
                self._consecutive_failures = 0
                if not keep_going:
                    break
            except BrowserUnavailableError as exc:
                logger.error("Browser session lost: %s", exc)
                self.speaker.say("The browser has closed, so I am stopping.")
                exit_code = EXIT_FAILURE
                break
            except KeyboardInterrupt:
                self.speaker.say("Stopping.")
                break
            except VoiceAutomationError as exc:
                logger.warning("Command failed: %s", exc)
                self.speaker.say(str(exc))
                if self._register_failure():
                    exit_code = EXIT_FAILURE
                    break
            except Exception:
                logger.exception("Unexpected error while handling a command")
                self.speaker.say("Something went wrong. Please try again.")
                if self._register_failure():
                    exit_code = EXIT_FAILURE
                    break

        self._running = False
        return exit_code

    def _register_failure(self) -> bool:
        """Record a failure; return True when the loop should give up."""
        self._consecutive_failures += 1
        if self._consecutive_failures < self.settings.max_consecutive_failures:
            return False
        logger.error(
            "Stopping after %s consecutive failures", self._consecutive_failures
        )
        self.speaker.say("Too many problems in a row, so I am stopping.")
        return True

    # -- dispatch -------------------------------------------------------
    def handle(self, command: Command) -> bool:
        """Act on ``command``.  Returns ``False`` when the user asked to exit."""
        logger.info("Intent %s from %r", command.intent.value, command.raw)
        handler = getattr(self, f"_do_{command.intent.value}", None)
        if handler is None:  # pragma: no cover - every intent has a handler
            self.speaker.say("I do not know how to do that yet.")
            return True
        return bool(handler(command))

    # -- handlers -------------------------------------------------------
    def _do_exit(self, _: Command) -> bool:
        self.speaker.say("Goodbye.")
        return False

    def _do_help(self, _: Command) -> bool:
        self.speaker.say(HELP_TEXT)
        return True

    def _do_unknown(self, command: Command) -> bool:
        if command.suggestion:
            self.speaker.say(f"I did not catch that. Did you mean: {command.suggestion}?")
        else:
            self.speaker.say("I did not understand that. Say help for examples.")
        return True

    def _do_open(self, command: Command) -> bool:
        target = command.argument or ""
        try:
            url = resolve_target(target)
        except InvalidTargetError:
            # A phrase that is not a site is almost always a search.
            self.speaker.say(f"I could not open {target}, so I will search for it instead.")
            self.browser.go(
                build_search_url(self.settings.search_url_template, target)
            )
            return True
        self.speaker.say(f"Opening {target}")
        self.browser.go(url)
        return True

    def _do_search_web(self, command: Command) -> bool:
        query = command.argument or ""
        url = build_search_url(self.settings.search_url_template, query)
        self.speaker.say(f"Searching for {query}")
        self.browser.go(url)
        return True

    def _do_search_amazon(self, command: Command) -> bool:
        return self._site_search(command, "amazon", "Amazon")

    def _do_search_youtube(self, command: Command) -> bool:
        return self._site_search(command, "youtube", "YouTube")

    def _do_search_wikipedia(self, command: Command) -> bool:
        return self._site_search(command, "wikipedia", "Wikipedia")

    def _site_search(self, command: Command, key: str, label: str) -> bool:
        query = command.argument or ""
        url = build_search_url(SITE_SEARCH[key], query)
        self.speaker.say(f"Searching {label} for {query}")
        self.browser.go(url)
        return True

    def _do_click(self, command: Command) -> bool:
        description = command.argument or ""
        try:
            label = self.browser.click_text(description)
        except ElementNotFoundError:
            self.speaker.say(f"I could not find {description} on this page.")
            return True
        self.speaker.say(f"Clicked {label}")
        return True

    def _do_scroll_down(self, command: Command) -> bool:
        return self._scroll(ScrollDirection.DOWN, command.amount, "Scrolling down")

    def _do_scroll_up(self, command: Command) -> bool:
        return self._scroll(ScrollDirection.UP, command.amount, "Scrolling up")

    def _do_scroll_top(self, _: Command) -> bool:
        return self._scroll(ScrollDirection.TOP, None, "Going to the top")

    def _do_scroll_bottom(self, _: Command) -> bool:
        return self._scroll(ScrollDirection.BOTTOM, None, "Going to the bottom")

    def _scroll(
        self, direction: ScrollDirection, pixels: int | None, message: str
    ) -> bool:
        self.speaker.say(message)
        self.browser.scroll(direction, pixels)
        return True

    def _do_back(self, _: Command) -> bool:
        self.speaker.say("Going back")
        self.browser.back()
        return True

    def _do_forward(self, _: Command) -> bool:
        self.speaker.say("Going forward")
        self.browser.forward()
        return True

    def _do_refresh(self, _: Command) -> bool:
        self.speaker.say("Refreshing")
        self.browser.refresh()
        return True

    def _do_where_am_i(self, _: Command) -> bool:
        try:
            self.speaker.say(f"You are on {self.browser.title() or self.browser.current_url()}")
        except BrowserError:
            self.speaker.say("I cannot tell which page is open.")
        return True

    def _do_time(self, _: Command) -> bool:
        self.speaker.say(f"It is {self._now().strftime('%I:%M %p').lstrip('0')}")
        return True

    def _do_date(self, _: Command) -> bool:
        self.speaker.say(f"Today is {self._now().strftime('%A, %d %B %Y')}")
        return True

    def _do_weather(self, command: Command) -> bool:
        city = command.argument or self.settings.default_weather_city
        if not city:
            self.speaker.say("Which city would you like the weather for?")
            return True
        try:
            summary = self.weather.summary(city)
        except WeatherError as exc:
            self.speaker.say(str(exc))
            return True
        self.speaker.say(f"In {city}: {summary}")
        return True


def _known_sites():  # type: ignore[no-untyped-def]
    from .urls import QUICK_SITES

    return QUICK_SITES.keys()
