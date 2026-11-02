"""URL resolution, scheme safety and query encoding."""

from __future__ import annotations

import pytest

from voice_automation.exceptions import InvalidTargetError
from voice_automation.urls import (
    QUICK_SITES,
    SITE_SEARCH,
    build_search_url,
    despeak,
    resolve_target,
)


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("youtube", "https://www.youtube.com"),
        ("YouTube", "https://www.youtube.com"),
        ("stack overflow", "https://stackoverflow.com"),
        ("wikipedia", "https://www.wikipedia.org"),
    ],
)
def test_quick_sites(phrase, expected):
    assert resolve_target(phrase) == expected


def test_wikipedia_points_at_the_real_domain():
    """The original table sent 'wikipedia' to wikipedia.com, a parked domain."""
    assert QUICK_SITES["wikipedia"].endswith("wikipedia.org")


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("example.com", "https://example.com"),
        ("example.com/docs", "https://example.com/docs"),
        ("https://example.com/a?b=c", "https://example.com/a?b=c"),
        ("http://example.com", "http://example.com"),
        ("sub.domain.example.co.uk", "https://sub.domain.example.co.uk"),
    ],
)
def test_hostnames(phrase, expected):
    assert resolve_target(phrase) == expected


def test_single_word_becomes_a_dot_com():
    assert resolve_target("netflix") == QUICK_SITES["netflix"]
    assert resolve_target("someunknownbrand") == "https://www.someunknownbrand.com"


def test_spoken_punctuation():
    assert despeak("example dot com slash docs") == "example.com/docs"
    assert resolve_target("example dot com") == "https://example.com"


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "phrase",
    [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "ftp://example.com",
        "chrome://settings",
        "about:config",
    ],
)
def test_unsafe_schemes_are_rejected(phrase):
    with pytest.raises(InvalidTargetError):
        resolve_target(phrase)


def test_embedded_credentials_are_rejected():
    with pytest.raises(InvalidTargetError):
        resolve_target("https://user:password@evil.example.com")


@pytest.mark.parametrize("phrase", ["", "   ", "some random words here", "the thing i wanted"])
def test_unresolvable_phrases_raise(phrase):
    with pytest.raises(InvalidTargetError):
        resolve_target(phrase)


# ---------------------------------------------------------------------------
# Search URLs
# ---------------------------------------------------------------------------

def test_query_is_percent_encoded():
    """Naive space-to-plus replacement corrupted queries containing &, # or ?."""
    url = build_search_url("https://www.google.com/search?q={query}", "c++ & rust #1")
    assert url == "https://www.google.com/search?q=c%2B%2B+%26+rust+%231"


def test_unicode_queries_survive():
    url = build_search_url("https://www.google.com/search?q={query}", "café résumé")
    assert "caf%C3%A9" in url


def test_whitespace_is_collapsed():
    url = build_search_url("https://x/?q={query}", "  too   many   spaces ")
    assert url == "https://x/?q=too+many+spaces"


def test_empty_query_raises():
    with pytest.raises(InvalidTargetError):
        build_search_url("https://x/?q={query}", "   ")


@pytest.mark.parametrize("key", sorted(SITE_SEARCH))
def test_site_search_templates_render(key):
    assert "{query}" not in build_search_url(SITE_SEARCH[key], "test query")


@pytest.mark.parametrize("url", sorted(QUICK_SITES.values()))
def test_every_quick_site_is_https(url):
    assert url.startswith("https://")
