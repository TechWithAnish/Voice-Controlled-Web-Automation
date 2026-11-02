"""Resolution of spoken phrases into safe, well-formed URLs.

Speech recognition produces free text, so every string that reaches the
browser is treated as untrusted input:

* only ``http`` and ``https`` are ever navigated to, which blocks
  ``javascript:``, ``data:`` and ``file:`` payloads;
* embedded credentials (``user:pass@host``) are rejected;
* search queries are percent-encoded rather than having spaces swapped for
  ``+``, so ``&``, ``#``, ``?`` and non-ASCII characters survive intact;
* a phrase that is not plausibly a hostname raises
  :class:`InvalidTargetError` instead of being coerced into
  ``https://www.some random words.com``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.parse import quote_plus, urlparse, urlunparse

from .exceptions import InvalidTargetError

#: The only URL schemes the assistant will navigate to.
SAFE_SCHEMES = frozenset({"http", "https"})

#: Shorthand names that map to a canonical URL.
QUICK_SITES: Mapping[str, str] = {
    "amazon": "https://www.amazon.com",
    "bbc": "https://www.bbc.com",
    "chatgpt": "https://chat.openai.com",
    "facebook": "https://www.facebook.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "google": "https://www.google.com",
    "google drive": "https://drive.google.com",
    "google maps": "https://maps.google.com",
    "hacker news": "https://news.ycombinator.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "netflix": "https://www.netflix.com",
    "reddit": "https://www.reddit.com",
    "spotify": "https://open.spotify.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
    "twitter": "https://twitter.com",
    "wikipedia": "https://www.wikipedia.org",
    "x": "https://x.com",
    "youtube": "https://www.youtube.com",
}

#: A hostname label: alphanumeric, inner hyphens allowed.
_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_HOSTNAME_RE = re.compile(rf"^{_LABEL}(?:\.{_LABEL})+$", re.IGNORECASE)
_SINGLE_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,61}$", re.IGNORECASE)

#: Spoken punctuation, e.g. "example dot com slash docs".
_SPOKEN = (
    (re.compile(r"\s+dot\s+", re.IGNORECASE), "."),
    (re.compile(r"\s+slash\s+", re.IGNORECASE), "/"),
    (re.compile(r"\s+dash\s+", re.IGNORECASE), "-"),
    (re.compile(r"\s+underscore\s+", re.IGNORECASE), "_"),
)


def despeak(text: str) -> str:
    """Convert spoken punctuation into real punctuation.

    >>> despeak("example dot com slash docs")
    'example.com/docs'
    """
    result = text.strip()
    for pattern, replacement in _SPOKEN:
        result = pattern.sub(replacement, result)
    return result.strip()


def _reject(reason: str, phrase: str) -> InvalidTargetError:
    return InvalidTargetError(f"{reason}: {phrase!r}")


def resolve_target(
    phrase: str, quick_sites: Mapping[str, str] | None = None
) -> str:
    """Turn a spoken phrase into a safe absolute URL.

    Resolution order: known shorthand, explicit URL, bare hostname, single
    word (treated as ``www.<word>.com``).  Anything else raises
    :class:`InvalidTargetError` so the caller can offer a web search instead.
    """
    sites = QUICK_SITES if quick_sites is None else quick_sites
    cleaned = despeak(phrase)
    if not cleaned:
        raise _reject("empty navigation target", phrase)

    key = re.sub(r"\s+", " ", cleaned).strip().lower().rstrip(".")
    if key in sites:
        return sites[key]

    # Strip a leading "www." the speaker may or may not have said, but keep
    # the original for hostname construction.
    if "://" in cleaned:
        return _validate_absolute(cleaned, phrase)

    # Looks like "example.com" or "example.com/path".
    host_part, _, path_part = cleaned.partition("/")
    if _HOSTNAME_RE.match(host_part):
        return _validate_absolute(
            f"https://{host_part}" + (f"/{path_part}" if path_part else ""), phrase
        )

    if _SINGLE_TOKEN_RE.match(cleaned):
        return _validate_absolute(f"https://www.{cleaned.lower()}.com", phrase)

    raise _reject("not a recognisable website", phrase)


def _validate_absolute(candidate: str, original: str) -> str:
    """Parse ``candidate`` and confirm it is a safe absolute http(s) URL."""
    try:
        parsed = urlparse(candidate)
    except ValueError as exc:  # pragma: no cover - urlparse rarely raises
        raise _reject(f"unparsable URL ({exc})", original) from exc

    scheme = parsed.scheme.lower()
    if scheme not in SAFE_SCHEMES:
        raise _reject(f"unsupported URL scheme {scheme!r}", original)
    if not parsed.netloc:
        raise _reject("URL has no host", original)
    if "@" in parsed.netloc:
        raise _reject("URLs with embedded credentials are not allowed", original)

    host = parsed.hostname or ""
    if not host:
        raise _reject("URL has no host", original)

    return urlunparse(
        (scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )


def build_search_url(template: str, query: str) -> str:
    """Render a search-engine template with a percent-encoded ``query``.

    >>> build_search_url("https://www.google.com/search?q={query}", "c++ & rust")
    'https://www.google.com/search?q=c%2B%2B+%26+rust'
    """
    cleaned = " ".join(query.split())
    if not cleaned:
        raise InvalidTargetError("empty search query")
    return template.format(query=quote_plus(cleaned))


#: Site-specific search templates used by the "search amazon …" family.
SITE_SEARCH = {
    "amazon": "https://www.amazon.com/s?k={query}",
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "wikipedia": "https://en.wikipedia.org/w/index.php?search={query}",
}
