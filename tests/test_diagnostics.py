"""Pre-flight diagnostics."""

from __future__ import annotations

from pathlib import Path

from voice_automation import diagnostics
from voice_automation.config import Settings


def test_python_check_passes_on_a_supported_interpreter():
    assert diagnostics.check_python().ok is True


def test_config_check_reports_invalid_environment(monkeypatch):
    monkeypatch.setenv("VA_HEADLESS", "perhaps")
    result = diagnostics.check_config()
    assert result.ok is False
    assert "VA_HEADLESS" in result.detail


def test_config_check_passes_on_a_clean_environment(monkeypatch):
    monkeypatch.delenv("VA_HEADLESS", raising=False)
    assert diagnostics.check_config().ok is True


def test_browser_check_names_what_is_installed(monkeypatch):
    from voice_automation.browser import browsers

    monkeypatch.setattr(browsers, "_registry_path", lambda kind: None)
    monkeypatch.setattr(
        browsers,
        "_known_paths",
        lambda kind: [Path("/usr/bin/msedge")]
        if kind is browsers.BrowserKind.EDGE
        else [],
    )
    monkeypatch.setattr(browsers.shutil, "which", lambda name: None)
    monkeypatch.setattr(Path, "is_file", lambda self: self == Path("/usr/bin/msedge"))

    result = diagnostics.check_browsers(Settings())
    assert result.ok is True
    assert "Microsoft Edge" in result.detail


def test_browser_check_suggests_a_remedy_when_none_installed(monkeypatch):
    from voice_automation.browser import browsers

    monkeypatch.setattr(browsers, "_registry_path", lambda kind: None)
    monkeypatch.setattr(browsers, "_known_paths", lambda kind: [])
    monkeypatch.setattr(browsers.shutil, "which", lambda name: None)

    result = diagnostics.check_browsers(Settings())
    assert result.ok is False
    assert "VA_BROWSER_BINARY" in (result.remedy or "")
    assert "none" in result.detail


def test_tts_check_honours_the_disable_flag():
    result = diagnostics.check_tts(Settings(tts_enabled=False))
    assert result.ok is True
    assert "disabled" in result.detail


def test_microphone_with_no_backend_offers_the_compiler_free_option(monkeypatch):
    """PyAudio needs a C toolchain; the remedy must not require one."""
    from voice_automation.speech import microphone

    monkeypatch.setattr(microphone, "available_backend", lambda: None)
    result = diagnostics.check_microphone()
    assert result.ok is False
    assert "sounddevice" in (result.remedy or "")
    assert "--text" in (result.remedy or "")


def test_microphone_names_the_backend_in_use(monkeypatch):
    from voice_automation.speech import microphone

    monkeypatch.setattr(microphone, "available_backend", lambda: "sounddevice")
    monkeypatch.setattr(microphone, "list_microphones", lambda: ["Mic Array", "Webcam"])
    result = diagnostics.check_microphone()
    assert result.ok is True
    assert "sounddevice" in result.detail
    assert "Mic Array" in result.detail


def test_unusable_backend_is_distinguished_from_a_missing_one(monkeypatch):
    from voice_automation.exceptions import SpeechUnavailableError
    from voice_automation.speech import microphone

    def explode():
        raise SpeechUnavailableError("PortAudio device error")

    monkeypatch.setattr(microphone, "available_backend", lambda: "pyaudio")
    monkeypatch.setattr(microphone, "list_microphones", explode)
    result = diagnostics.check_microphone()
    assert result.ok is False
    assert "installed but unusable" in result.detail


def test_backend_with_no_devices_is_reported(monkeypatch):
    from voice_automation.speech import microphone

    monkeypatch.setattr(microphone, "available_backend", lambda: "sounddevice")
    monkeypatch.setattr(microphone, "list_microphones", list)
    result = diagnostics.check_microphone()
    assert result.ok is False
    assert "no input devices" in result.detail


def test_report_returns_nonzero_when_a_check_fails(monkeypatch, capsys):
    failing = diagnostics.CheckResult("Fake", False, "broken", remedy="fix it")
    monkeypatch.setattr(diagnostics, "run_checks", lambda settings=None: [failing])
    assert diagnostics.report() == 1
    out = capsys.readouterr().out
    assert "[FAIL] Fake" in out
    assert "fix it" in out


def test_report_returns_zero_when_all_pass(monkeypatch, capsys):
    passing = diagnostics.CheckResult("Fake", True, "fine")
    monkeypatch.setattr(diagnostics, "run_checks", lambda settings=None: [passing])
    assert diagnostics.report() == 0
    assert "All checks passed" in capsys.readouterr().out


def test_run_checks_never_raises(monkeypatch):
    monkeypatch.setattr(
        diagnostics,
        "check_network",
        lambda: diagnostics.CheckResult("Network", True, "skipped"),
    )
    results = diagnostics.run_checks(Settings(tts_enabled=False))
    assert len(results) == 6
    assert all(isinstance(r, diagnostics.CheckResult) for r in results)
