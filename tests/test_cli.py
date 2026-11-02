"""CLI argument handling and process lifecycle."""

from __future__ import annotations

import pytest

from voice_automation import cli
from voice_automation.config import Settings
from voice_automation.exceptions import BrowserError

from .conftest import FakeBrowser, FakeSpeaker


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    from voice_automation import __version__

    assert __version__ in capsys.readouterr().out


def test_flags_override_environment_settings():
    args = cli.build_parser().parse_args(
        [
            "--headless",
            "--no-speech",
            "--browser",
            "brave",
            "--search-engine",
            "duckduckgo",
            "--log-level",
            "DEBUG",
        ]
    )
    settings = cli.apply_overrides(Settings(), args)
    assert settings.browser == "brave"
    assert settings.headless is True
    assert settings.tts_enabled is False
    assert settings.search_engine == "duckduckgo"
    assert settings.log_level == "DEBUG"


def test_no_flags_leaves_settings_untouched():
    args = cli.build_parser().parse_args([])
    base = Settings()
    assert cli.apply_overrides(base, args) is base


def test_invalid_configuration_returns_exit_code_two(monkeypatch, capsys):
    monkeypatch.setenv("VA_HEADLESS", "perhaps")
    assert cli.main(["--text"]) == cli.EXIT_CONFIG_ERROR
    assert "Configuration error" in capsys.readouterr().err


def test_browser_failure_returns_failure_code(monkeypatch, capsys):
    class FailingBrowser:
        def __init__(self, settings):
            pass

        def start(self):
            raise BrowserError("chrome not found")

        def quit(self):
            pass

    monkeypatch.setattr(cli, "BrowserController", FailingBrowser)
    monkeypatch.setattr(cli, "create_speaker", lambda settings: FakeSpeaker())
    assert cli.main(["--command", "exit"]) == 1
    assert "chrome not found" in capsys.readouterr().err


def test_scripted_commands_run_then_exit(monkeypatch):
    browser = FakeBrowser()
    monkeypatch.setattr(cli, "BrowserController", lambda settings: browser)
    monkeypatch.setattr(cli, "create_speaker", lambda settings: FakeSpeaker())
    browser.start = lambda: None  # type: ignore[assignment]

    assert cli.main(["--command", "open youtube", "--command", "go back"]) == 0
    assert browser.visited == ["https://www.youtube.com"]
    assert browser.history == ["back"]
    assert browser.quit_calls == 1


def test_browser_is_closed_even_when_the_loop_raises(monkeypatch):
    browser = FakeBrowser()
    browser.start = lambda: None  # type: ignore[assignment]
    monkeypatch.setattr(cli, "BrowserController", lambda settings: browser)
    monkeypatch.setattr(cli, "create_speaker", lambda settings: FakeSpeaker())

    class Exploding(cli.VoiceAssistant):
        def run(self):
            raise BrowserError("mid-run failure")

    monkeypatch.setattr(cli, "VoiceAssistant", Exploding)
    assert cli.main(["--command", "exit"]) == 1
    assert browser.quit_calls == 1


def test_scripted_listener_exhausts_then_exits():
    listener = cli._ScriptedListener(["open youtube"])
    assert listener.listen() == "open youtube"
    assert listener.listen() == "exit"
    assert listener.listen() == "exit"


def test_doctor_runs_without_a_browser(monkeypatch, capsys):
    monkeypatch.setattr(cli, "report", lambda settings: 0)
    assert cli.main(["--doctor"]) == 0


def test_signal_handlers_are_installed(monkeypatch, settings):
    installed = {}

    def fake_signal(sig, handler):
        installed[sig] = handler

    monkeypatch.setattr(cli.signal, "signal", fake_signal)
    assistant = cli.VoiceAssistant(
        settings=settings,
        browser=FakeBrowser(),
        listener=cli.ConsoleListener(),
        speaker=FakeSpeaker(),
    )
    cli._install_signal_handlers(assistant)
    assert installed
    handler = next(iter(installed.values()))
    assistant._running = True
    handler(2, None)
    assert assistant._running is False


def test_close_swallows_errors():
    class Bad:
        def close(self):
            raise RuntimeError("nope")

    cli._close(Bad(), object(), None)
