# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-11-02

A production-readiness release. The behaviour a user sees is broadly the
same, but the command matching is now correct, the process is safe to leave
running, and the parts that used to be untestable are covered by tests.

### Fixed

- **Commands were matched by substring, so common phrases ran the wrong
  action.** `"search for laptop"` contains `top` and jumped to the top of the
  page; `"open closet"` contains `close` and quit the application;
  `"search for timer apps"` contains `time` and read out the clock;
  `"open backup dashboard"` contains `back` and navigated backwards. Matching
  is now a fixed-order table of fully anchored regular expressions, so no rule
  can fire on an accidental substring.
- **Any spoken apostrophe broke element lookup.** `"click on don't have an
  account"` produced `//*[contains(text(), 'don't have an account')]`, which
  is invalid XPath and raised `InvalidSelectorException`. All interpolated
  text now goes through an XPath 1.0 literal escaper.
- **Search queries were not URL-encoded.** `query.replace(" ", "+")` corrupted
  any query containing `&`, `#`, `?` or non-ASCII characters. Queries are now
  percent-encoded with `urllib.parse.quote_plus`.
- **A failed click cost about thirty seconds of silence.** Six locator
  strategies were each given their own five-second wait, run in sequence. A
  single bounded wait now tries every strategy on each poll.
- **Ambient-noise calibration ran before every command**, adding a second of
  dead air to each turn. It now runs once at start-up and then only every
  `VA_RECALIBRATE_EVERY` commands.
- **`"open <anything>"` was coerced into a URL.** `"open my bank"` became
  `https://www.my bank.com`. Unresolvable phrases now fall back to a web
  search.
- **`quick_sites["wikipedia"]` pointed at `wikipedia.com`**, a parked domain,
  rather than `wikipedia.org`.
- **The weather lookup read any HTTP 200 out loud**, including error pages and
  rate-limit notices. The response is now validated before it is spoken.
- **`cleanup()` called `sys.exit(0)` from a `finally` block** inside the
  command loop. Shutdown is now ordinary control flow and the process exit
  code is decided in one place.
- **A dead browser session left the loop spinning**, speaking an error for
  every iteration forever. Consecutive failures are now counted and the
  assistant stops after `VA_MAX_CONSECUTIVE_FAILURES`.
- **Text-to-speech failure aborted start-up.** It now degrades to printed
  output, and a run-loop error re-initialises the engine once.
- **Logging was configured at import time** with a hard-coded relative path
  and no rotation, so the log file landed wherever the process started and
  grew without bound. File logging is now opt-in, explicit and rotating.

### Security

- Only `http` and `https` URLs are navigated to. `javascript:`, `data:`,
  `file:`, `chrome:` and `about:` targets are rejected, as are URLs carrying
  embedded credentials.
- Scroll distances are clamped, so a misheard number cannot be passed through
  to the page.
- `--no-sandbox` is opt-in (`VA_DISABLE_SANDBOX`) instead of always on. It is
  needed inside containers and inappropriate on a workstation.
- City names are validated and percent-encoded before the weather request.
- `bandit` rules run as part of linting.

### Added

- An installable package with a `voice-automation` console script.
- `--doctor`: pre-flight checks for Python, configuration, Chrome, the
  microphone, text-to-speech and network reachability, each with a remedy.
- `--text` and `--command`, which drive the whole pipeline without a
  microphone. `--command` makes the assistant scriptable.
- Typed configuration from `VA_*` environment variables or a `.env` file,
  validated at start-up with errors that name the offending variable.
- New commands: `where am i`, `what is the date`, `search youtube for ...`,
  `search wikipedia for ...`, `who is ...`, and `help`.
- Spoken numbers in scroll commands ("scroll down two hundred").
- Spoken punctuation in URLs ("example dot com slash docs").
- Selectable search engine: Google, DuckDuckGo or Bing.
- Signal handling, so SIGINT and SIGTERM end the current turn and shut down
  cleanly rather than killing the process mid-action.
- A test suite of 292 tests covering the parser, URL handling, XPath
  escaping, configuration, the weather client, the speech layer, the browser
  controller and the full command loop. It needs no browser, microphone or
  network.
- GitHub Actions CI: ruff, mypy, the test suite on Python 3.10-3.13 across
  Linux and Windows, and a packaging check.

### Changed

- Minimum Python is now 3.10 (3.9 reached end of life in October 2025).
- `fuzzywuzzy` replaced with `rapidfuzz`, which is maintained and needs no
  separate C extension.
- Dependencies carry upper bounds so a major release of Selenium cannot break
  an install.
- The four unwired scripts in the repository root moved to `examples/`, which
  is excluded from packaging, linting and CI. See `examples/README.md`.
- `test_speech.py` became `voice-automation --doctor`.

### Removed

- `DEEPSEEK_API_KEY` and the surrounding documentation. The assistant never
  contained any LLM code; the key was dead configuration.
- The duplicated assistant implementation that shipped alongside the main one.

[2.0.0]: https://github.com/TechWithAnish/Voice-Controlled-Web-Automation/releases/tag/v2.0.0
