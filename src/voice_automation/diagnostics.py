"""Pre-flight checks, exposed as ``voice-automation doctor``.

Replaces the old interactive ``test_speech.py`` script.  Each check is
independent and reports a clear pass/fail plus a remedy, so a user can tell
whether a problem is their microphone, their audio output, their Chrome
installation or their network before they report a bug.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass

from .config import Settings
from .exceptions import ConfigError

MIN_PYTHON = (3, 10)


@dataclass
class CheckResult:
    """The outcome of a single diagnostic."""

    name: str
    ok: bool
    detail: str
    remedy: str | None = None

    def render(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        line = f"[{status}] {self.name}: {self.detail}"
        if not self.ok and self.remedy:
            line += f"\n         -> {self.remedy}"
        return line


def check_python() -> CheckResult:
    version = ".".join(str(part) for part in sys.version_info[:3])
    ok = sys.version_info[:2] >= MIN_PYTHON
    return CheckResult(
        "Python version",
        ok,
        f"{version} on {platform.system()} {platform.machine()}",
        remedy=f"Python {'.'.join(map(str, MIN_PYTHON))} or newer is required.",
    )


def check_config() -> CheckResult:
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        return CheckResult(
            "Configuration", False, str(exc), remedy="Fix the variable in your .env file."
        )
    overrides = ", ".join(settings.overrides) or "none"
    return CheckResult("Configuration", True, f"valid (overrides: {overrides})")


def check_browsers(settings: Settings) -> CheckResult:
    """Report which browsers are installed and which one would be used."""
    from .browser.browsers import discover, resolve_browser

    installed = discover()
    names = ", ".join(info.label for info in installed) or "none"

    try:
        chosen = resolve_browser(settings.browser, settings.browser_binary)
    except LookupError as exc:
        return CheckResult(
            "Browser",
            False,
            f"installed: {names}",
            remedy=str(exc),
        )

    detail = f"using {chosen.label} ({chosen.path}); installed: {names}"
    return CheckResult("Browser", True, detail)


def check_tts(settings: Settings) -> CheckResult:
    if not settings.tts_enabled:
        return CheckResult("Text to speech", True, "disabled by configuration")
    try:
        import pyttsx3

        engine = pyttsx3.init()
        voices = engine.getProperty("voices") or []
        engine.stop()
    except Exception as exc:
        return CheckResult(
            "Text to speech",
            False,
            f"unavailable ({exc})",
            remedy=(
                "The assistant will fall back to printed output. On Linux install "
                "espeak-ng; on Windows check the SAPI5 voices in Settings."
            ),
        )
    names = ", ".join((v.name or v.id) for v in voices[:3]) or "default only"
    return CheckResult("Text to speech", True, f"{len(voices)} voice(s): {names}")


def check_microphone() -> CheckResult:
    try:
        import speech_recognition as sr
    except ImportError as exc:  # pragma: no cover - dependency is required
        return CheckResult(
            "Microphone", False, str(exc), remedy="pip install SpeechRecognition"
        )
    try:
        names = sr.Microphone.list_microphone_names()
    except Exception as exc:
        return CheckResult(
            "Microphone",
            False,
            f"audio backend unavailable ({exc})",
            remedy=(
                "Install PyAudio (pip install 'voice-web-automation[mic]'). On Linux "
                "install portaudio19-dev first. Text mode (--text) works without it."
            ),
        )
    if not names:
        return CheckResult(
            "Microphone",
            False,
            "no input devices detected",
            remedy="Connect a microphone and grant the terminal permission to use it.",
        )
    return CheckResult("Microphone", True, f"{len(names)} device(s), default: {names[0]}")


def check_network() -> CheckResult:
    import requests

    try:
        response = requests.head("https://www.google.com", timeout=5)
        ok = response.status_code < 500
        return CheckResult("Network", ok, f"reached google.com (HTTP {response.status_code})")
    except Exception as exc:
        return CheckResult(
            "Network",
            False,
            f"could not reach google.com ({exc})",
            remedy=(
                "Speech recognition and search both need internet access. Check your "
                "connection or proxy settings."
            ),
        )


def run_checks(settings: Settings | None = None) -> list[CheckResult]:
    """Run every diagnostic and return the results in display order."""
    resolved = settings
    if resolved is None:
        try:
            resolved = Settings.from_env()
        except ConfigError:
            resolved = Settings()
    return [
        check_python(),
        check_config(),
        check_browsers(resolved),
        check_microphone(),
        check_tts(resolved),
        check_network(),
    ]


def report(settings: Settings | None = None) -> int:
    """Print the diagnostic report.  Returns a process exit code."""
    results = run_checks(settings)
    print("Voice automation pre-flight checks")
    print("-" * 46)
    for result in results:
        print(result.render())
    failures = [r for r in results if not r.ok]
    print("-" * 46)
    if failures:
        print(f"{len(failures)} check(s) failed. See the remedies above.")
        return 1
    print("All checks passed.")
    return 0
