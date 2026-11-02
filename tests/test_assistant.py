"""End-to-end behaviour of the command loop, with every collaborator faked."""

from __future__ import annotations

import pytest

from voice_automation.assistant import EXIT_FAILURE, EXIT_OK, VoiceAssistant
from voice_automation.browser import ScrollDirection
from voice_automation.commands import CommandParser
from voice_automation.exceptions import (
    BrowserError,
    BrowserUnavailableError,
    SpeechServiceError,
    SpeechUnavailableError,
)
from voice_automation.urls import QUICK_SITES

from .conftest import FakeBrowser, FakeListener, FakeSpeaker, FakeWeather, RaisingListener


def build(utterances, *, settings, browser=None, speaker=None, weather=None, now=None):
    """Assemble an assistant wired to fakes."""
    fake_browser = browser or FakeBrowser()
    fake_speaker = speaker or FakeSpeaker()
    assistant = VoiceAssistant(
        settings=settings,
        browser=fake_browser,
        listener=FakeListener(utterances),
        speaker=fake_speaker,
        parser=CommandParser(known_sites=QUICK_SITES.keys()),
        weather=weather or FakeWeather(),
        now=now or (lambda: __import__("datetime").datetime(2026, 11, 2, 14, 5)),
    )
    return assistant, fake_browser, fake_speaker


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def test_open_navigates(settings):
    assistant, browser, _ = build(["open youtube", "exit"], settings=settings)
    assert assistant.run() == EXIT_OK
    assert browser.visited == ["https://www.youtube.com"]


def test_unresolvable_open_falls_back_to_search(settings):
    assistant, browser, speaker = build(
        ["open the thing i wanted", "exit"], settings=settings
    )
    assistant.run()
    assert len(browser.visited) == 1
    assert "google.com/search" in browser.visited[0]
    assert "search for it instead" in speaker.transcript


def test_search_encodes_the_query(settings):
    assistant, browser, _ = build(["search for c++ & rust", "exit"], settings=settings)
    assistant.run()
    assert browser.visited == ["https://www.google.com/search?q=c%2B%2B+%26+rust"]


def test_amazon_search_uses_the_amazon_endpoint(settings):
    assistant, browser, _ = build(
        ["search amazon for headphones", "exit"], settings=settings
    )
    assistant.run()
    assert browser.visited == ["https://www.amazon.com/s?k=headphones"]


def test_history_commands(settings):
    assistant, browser, _ = build(
        ["go back", "go forward", "refresh", "exit"], settings=settings
    )
    assistant.run()
    assert browser.history == ["back", "forward", "refresh"]


# ---------------------------------------------------------------------------
# Scrolling
# ---------------------------------------------------------------------------

def test_scroll_amount_is_passed_through(settings):
    assistant, browser, _ = build(
        ["scroll down 500", "scroll up", "scroll to bottom", "exit"], settings=settings
    )
    assistant.run()
    assert browser.scrolls == [
        (ScrollDirection.DOWN, 500),
        (ScrollDirection.UP, None),
        (ScrollDirection.BOTTOM, None),
    ]


# ---------------------------------------------------------------------------
# Clicking
# ---------------------------------------------------------------------------

def test_click_reports_the_label(settings):
    browser = FakeBrowser(click_result="Sign in")
    assistant, _, speaker = build(
        ["click on sign in", "exit"], settings=settings, browser=browser
    )
    assistant.run()
    assert browser.clicked == ["sign in"]
    assert "Clicked Sign in" in speaker.transcript


def test_missing_element_is_reported_and_the_loop_continues(settings):
    browser = FakeBrowser(click_result=None)
    assistant, _, speaker = build(
        ["click on nowhere", "go back", "exit"], settings=settings, browser=browser
    )
    assert assistant.run() == EXIT_OK
    assert "could not find nowhere" in speaker.transcript.lower()
    assert browser.history == ["back"]


# ---------------------------------------------------------------------------
# Information
# ---------------------------------------------------------------------------

def test_time_is_spoken(settings):
    assistant, _, speaker = build(["what time is it", "exit"], settings=settings)
    assistant.run()
    assert "2:05 PM" in speaker.transcript


def test_date_is_spoken(settings):
    assistant, _, speaker = build(["what is the date", "exit"], settings=settings)
    assistant.run()
    assert "02 November 2026" in speaker.transcript


def test_weather_uses_the_city(settings):
    weather = FakeWeather(result="Sunny, +21C")
    assistant, _, speaker = build(
        ["weather in london", "exit"], settings=settings, weather=weather
    )
    assistant.run()
    assert weather.requested == ["london"]
    assert "Sunny, +21C" in speaker.transcript


def test_weather_error_is_spoken_not_raised(settings):
    weather = FakeWeather(error="The weather service could not be reached")
    assistant, _, speaker = build(
        ["weather in london", "exit"], settings=settings, weather=weather
    )
    assert assistant.run() == EXIT_OK
    assert "could not be reached" in speaker.transcript


def test_weather_without_a_city_asks_for_one(settings):
    assistant, _, speaker = build(["what is the weather", "exit"], settings=settings)
    assistant.run()
    assert "Which city" in speaker.transcript


def test_where_am_i(settings):
    browser = FakeBrowser()
    browser.page_title = "Example Domain"
    assistant, _, speaker = build(["where am i", "exit"], settings=settings, browser=browser)
    assistant.run()
    assert "Example Domain" in speaker.transcript


# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------

def test_greeting_is_spoken_first(settings):
    assistant, _, speaker = build(["exit"], settings=settings)
    assistant.run()
    assert speaker.said[0].startswith("Hello")


def test_help_lists_examples(settings):
    assistant, _, speaker = build(["help", "exit"], settings=settings)
    assistant.run()
    assert "open youtube" in speaker.transcript.lower()


def test_unknown_command_suggests_a_correction(settings):
    assistant, _, speaker = build(["scrol down", "exit"], settings=settings)
    assistant.run()
    assert "did you mean" in speaker.transcript.lower()


def test_silence_is_ignored(settings):
    assistant, browser, _ = build([None, "", "open youtube", "exit"], settings=settings)
    assistant.run()
    assert browser.visited == ["https://www.youtube.com"]


def test_exit_stops_the_loop(settings):
    assistant, browser, _ = build(["exit", "open youtube"], settings=settings)
    assert assistant.run() == EXIT_OK
    assert browser.visited == []


def test_request_stop_ends_the_loop(settings):
    assistant, _, _ = build(["open youtube", "open github"], settings=settings)
    original = assistant.handle

    def handle_once(command):
        assistant.request_stop()
        return original(command)

    assistant.handle = handle_once  # type: ignore[assignment]
    assert assistant.run() == EXIT_OK


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

def test_lost_browser_session_stops_with_a_failure_code(settings):
    class DeadBrowser(FakeBrowser):
        def go(self, url):
            raise BrowserUnavailableError("session deleted")

    assistant, _, speaker = build(
        ["open youtube", "open github"], settings=settings, browser=DeadBrowser()
    )
    assert assistant.run() == EXIT_FAILURE
    assert "browser has closed" in speaker.transcript.lower()


def test_repeated_failures_stop_the_loop(settings):
    class BrokenBrowser(FakeBrowser):
        def go(self, url):
            raise BrowserError("boom")

    assistant, _, speaker = build(
        ["open youtube"] * 20, settings=settings, browser=BrokenBrowser()
    )
    assert assistant.run() == EXIT_FAILURE
    assert "too many problems" in speaker.transcript.lower()


def test_an_isolated_failure_does_not_stop_the_loop(settings):
    class FlakyBrowser(FakeBrowser):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def go(self, url):
            self.calls += 1
            if self.calls == 1:
                raise BrowserError("transient")
            super().go(url)

    browser = FlakyBrowser()
    assistant, _, _ = build(
        ["open youtube", "open github", "exit"], settings=settings, browser=browser
    )
    assert assistant.run() == EXIT_OK
    assert browser.visited == ["https://github.com"]


def test_unexpected_exception_does_not_kill_the_loop(settings):
    class ExplodingBrowser(FakeBrowser):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def go(self, url):
            self.calls += 1
            if self.calls == 1:
                raise ValueError("unexpected")
            super().go(url)

    assistant, browser, speaker = build(
        ["open youtube", "open github", "exit"],
        settings=settings,
        browser=ExplodingBrowser(),
    )
    assert assistant.run() == EXIT_OK
    assert "something went wrong" in speaker.transcript.lower()
    assert browser.visited == ["https://github.com"]


def test_missing_microphone_stops_cleanly(settings):
    speaker = FakeSpeaker()
    assistant = VoiceAssistant(
        settings=settings,
        browser=FakeBrowser(),
        listener=RaisingListener(SpeechUnavailableError("no mic")),
        speaker=speaker,
        weather=FakeWeather(),
    )
    assert assistant.run() == EXIT_FAILURE
    assert "no longer hear you" in speaker.transcript.lower()


def test_speech_service_outage_backs_off_then_stops(settings):
    speaker = FakeSpeaker()
    listener = RaisingListener(SpeechServiceError("api down"))
    assistant = VoiceAssistant(
        settings=settings,
        browser=FakeBrowser(),
        listener=listener,
        speaker=speaker,
        weather=FakeWeather(),
    )
    assert assistant.run() == EXIT_FAILURE
    assert listener.calls == settings.max_consecutive_failures


def test_transient_speech_outage_recovers(settings):
    speaker = FakeSpeaker()
    listener = RaisingListener(SpeechServiceError("blip"), times=1)
    assistant = VoiceAssistant(
        settings=settings,
        browser=FakeBrowser(),
        listener=listener,
        speaker=speaker,
        weather=FakeWeather(),
    )
    assert assistant.run() == EXIT_OK


def test_keyboard_interrupt_during_listen_exits_cleanly(settings):
    speaker = FakeSpeaker()
    assistant = VoiceAssistant(
        settings=settings,
        browser=FakeBrowser(),
        listener=RaisingListener(KeyboardInterrupt()),
        speaker=speaker,
        weather=FakeWeather(),
    )
    assert assistant.run() == EXIT_OK
    assert "stopping" in speaker.transcript.lower()


@pytest.mark.parametrize(
    "utterance",
    ["open closet", "search for laptop", "search for timer apps", "open backup plans"],
)
def test_regression_phrases_do_not_quit_or_scroll(settings, utterance):
    """These utterances used to quit the app or jump to the top of the page."""
    assistant, browser, _ = build([utterance, "exit"], settings=settings)
    assert assistant.run() == EXIT_OK
    assert browser.scrolls == []
    assert len(browser.visited) == 1
