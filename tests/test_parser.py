"""Command parsing, including regressions for the substring-matching bugs."""

from __future__ import annotations

import pytest

from voice_automation.commands import CommandParser, Intent, normalise
from voice_automation.commands.parser import words_to_number
from voice_automation.urls import QUICK_SITES


@pytest.fixture
def parser() -> CommandParser:
    return CommandParser(known_sites=QUICK_SITES.keys())


# ---------------------------------------------------------------------------
# Regressions: phrases the previous substring matcher mis-routed.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("utterance", "intent", "argument"),
    [
        # "laptop" contains "top" -> used to scroll to the top of the page.
        ("search for laptop", Intent.SEARCH_WEB, "laptop"),
        ("search for a laptop stand", Intent.SEARCH_WEB, "a laptop stand"),
        # "closet" contains "close" -> used to quit the application.
        ("open closet", Intent.OPEN, "closet"),
        ("open closed captions", Intent.OPEN, "closed captions"),
        # "backup" and "feedback" contain "back" -> used to navigate back.
        ("open backup dashboard", Intent.OPEN, "backup dashboard"),
        ("search for feedback forms", Intent.SEARCH_WEB, "feedback forms"),
        # "timer" and "sometimes" contain "time" -> used to read the clock.
        ("search for timer apps", Intent.SEARCH_WEB, "timer apps"),
        # "stopwatch" contains both "stop" and "top".
        ("search for stopwatch reviews", Intent.SEARCH_WEB, "stopwatch reviews"),
        # "forward" inside a longer phrase.
        ("search for forward contracts", Intent.SEARCH_WEB, "forward contracts"),
    ],
)
def test_substring_regressions(parser, utterance, intent, argument):
    command = parser.parse(utterance)
    assert command.intent is intent
    assert command.argument == argument


# ---------------------------------------------------------------------------
# Intent coverage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("utterance", "intent"),
    [
        ("exit", Intent.EXIT),
        ("quit", Intent.EXIT),
        ("goodbye", Intent.EXIT),
        ("close the browser", Intent.EXIT),
        ("stop", Intent.EXIT),
        ("help", Intent.HELP),
        ("what can you do", Intent.HELP),
        ("what time is it", Intent.TIME),
        ("time", Intent.TIME),
        ("what is the date", Intent.DATE),
        ("where am i", Intent.WHERE_AM_I),
        ("scroll to bottom", Intent.SCROLL_BOTTOM),
        ("bottom of the page", Intent.SCROLL_BOTTOM),
        ("scroll to the top", Intent.SCROLL_TOP),
        ("scroll down", Intent.SCROLL_DOWN),
        ("page up", Intent.SCROLL_UP),
        ("go back", Intent.BACK),
        ("back", Intent.BACK),
        ("go forward", Intent.FORWARD),
        ("refresh the page", Intent.REFRESH),
        ("reload", Intent.REFRESH),
    ],
)
def test_simple_intents(parser, utterance, intent):
    assert parser.parse(utterance).intent is intent


@pytest.mark.parametrize(
    ("utterance", "intent", "argument"),
    [
        ("open youtube", Intent.OPEN, "youtube"),
        ("go to example.com", Intent.OPEN, "example.com"),
        ("visit the github", Intent.OPEN, "github"),
        ("take me to wikipedia", Intent.OPEN, "wikipedia"),
        ("search for python tutorials", Intent.SEARCH_WEB, "python tutorials"),
        ("google machine learning", Intent.SEARCH_WEB, "machine learning"),
        ("look up tide times", Intent.SEARCH_WEB, "tide times"),
        ("search the web for rust", Intent.SEARCH_WEB, "rust"),
        ("search amazon for headphones", Intent.SEARCH_AMAZON, "headphones"),
        ("amazon wireless mouse", Intent.SEARCH_AMAZON, "wireless mouse"),
        ("search for shoes on amazon", Intent.SEARCH_AMAZON, "shoes"),
        ("buy milk", Intent.SEARCH_AMAZON, "milk"),
        ("search youtube for jazz", Intent.SEARCH_YOUTUBE, "jazz"),
        ("play lo-fi beats on youtube", Intent.SEARCH_YOUTUBE, "lo-fi beats"),
        ("who is ada lovelace", Intent.SEARCH_WIKIPEDIA, "ada lovelace"),
        ("click on sign in", Intent.CLICK, "sign in"),
        ("press the submit button", Intent.CLICK, "submit button"),
        ("weather in new york", Intent.WEATHER, "new york"),
        ("what is the weather in paris", Intent.WEATHER, "paris"),
    ],
)
def test_intents_with_arguments(parser, utterance, intent, argument):
    command = parser.parse(utterance)
    assert command.intent is intent
    assert command.argument == argument


def test_site_specific_search_beats_generic_search(parser):
    """'amazon' must win over the generic 'search' rule."""
    assert parser.parse("search amazon for shoes").intent is Intent.SEARCH_AMAZON
    assert parser.parse("search for shoes").intent is Intent.SEARCH_WEB


def test_bare_site_name_opens_it(parser):
    command = parser.parse("youtube")
    assert command.intent is Intent.OPEN
    assert command.argument == "youtube"


def test_unknown_site_name_is_not_an_open(parser):
    assert parser.parse("bananas").intent is Intent.UNKNOWN


def test_weather_without_a_city_has_no_argument(parser):
    command = parser.parse("what is the weather")
    assert command.intent is Intent.WEATHER
    assert command.argument is None


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("utterance", "amount"),
    [
        ("scroll down", None),
        ("scroll down 500", 500),
        ("scroll down 500 pixels", 500),
        ("scroll down by 250", 250),
        ("scroll down two hundred", 200),
        ("scroll up fifty", 50),
        ("scroll down a thousand", 1000),
    ],
)
def test_scroll_amounts(parser, utterance, amount):
    command = parser.parse(utterance)
    assert command.intent in (Intent.SCROLL_DOWN, Intent.SCROLL_UP)
    assert command.amount == amount


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("three", 3),
        ("twenty one", 21),
        ("two hundred", 200),
        ("a thousand", 1000),
        ("one thousand five hundred", 1500),
        ("", None),
        ("a", None),
        ("and", None),
        ("laptop", None),
    ],
)
def test_words_to_number(phrase, expected):
    assert words_to_number(phrase) == expected


def test_spoken_numbers_are_not_rewritten_outside_scroll_commands(parser):
    """'the seven wonders' must stay a phrase, not become 'the 7 wonders'."""
    command = parser.parse("search for the seven wonders")
    assert command.argument == "the seven wonders"


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Open   YouTube  ", "open youtube"),
        ("Please open youtube", "open youtube"),
        ("Can you open youtube please", "open youtube"),
        ("Open YouTube.", "open youtube"),
        ("“go back”", "go back"),
        ("don’t have an account", "don't have an account"),
        ("", ""),
    ],
)
def test_normalise(raw, expected):
    assert normalise(raw) == expected


def test_apostrophes_survive_parsing(parser):
    command = parser.parse("click on don't have an account")
    assert command.intent is Intent.CLICK
    assert command.argument == "don't have an account"


# ---------------------------------------------------------------------------
# Unknown handling
# ---------------------------------------------------------------------------

def test_empty_utterance_is_unknown(parser):
    assert parser.parse("").intent is Intent.UNKNOWN
    assert parser.parse("   ").intent is Intent.UNKNOWN


def test_near_miss_gets_a_suggestion(parser):
    command = parser.parse("scrol down")
    assert command.intent is Intent.UNKNOWN
    assert command.suggestion is not None


def test_gibberish_gets_no_suggestion(parser):
    command = parser.parse("qwertyuiop zxcvbnm")
    assert command.intent is Intent.UNKNOWN
    assert command.suggestion is None


def test_parse_never_raises(parser):
    for weird in ("((", "\x00", "a" * 5000, "你好", "'; DROP TABLE --"):
        assert parser.parse(weird) is not None


def test_command_recognised_property(parser):
    assert parser.parse("go back").recognised is True
    assert parser.parse("florbish").recognised is False
