"""Command-line entry point and process lifecycle.

Responsibilities kept here rather than in the library: argument parsing,
loading ``.env``, configuring logging, installing signal handlers and
translating exceptions into exit codes.  Nothing below this module calls
``sys.exit``.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from . import __version__
from .assistant import EXIT_FAILURE, EXIT_OK, VoiceAssistant
from .browser import BrowserController
from .commands import CommandParser
from .config import SEARCH_ENGINES, Settings
from .diagnostics import report
from .exceptions import BrowserError, ConfigError, VoiceAutomationError
from .logging_setup import configure_logging
from .speech import ConsoleListener, Speaker, create_speaker
from .speech.listener import GoogleSpeechListener, Listener
from .urls import QUICK_SITES

logger = logging.getLogger(__name__)

EXIT_CONFIG_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="voice-automation",
        description="Control a web browser with spoken commands.",
        epilog="Settings can also be supplied as VA_* environment variables or in a .env file.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="run pre-flight checks on audio, browser and network, then exit",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="read typed commands from stdin instead of the microphone",
    )
    parser.add_argument(
        "--command",
        "-c",
        action="append",
        metavar="TEXT",
        help="run a single command and exit; repeatable. Implies --text",
    )
    parser.add_argument(
        "--headless", action="store_true", help="run Chrome without a visible window"
    )
    parser.add_argument(
        "--no-speech",
        action="store_true",
        help="print responses instead of speaking them",
    )
    parser.add_argument(
        "--search-engine",
        choices=sorted(SEARCH_ENGINES),
        help="search engine used for generic web searches",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="logging verbosity",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        metavar="PATH",
        help="write rotating logs to PATH (no file logging by default)",
    )
    return parser


def apply_overrides(settings: Settings, args: argparse.Namespace) -> Settings:
    """Apply command-line flags on top of environment-derived settings."""
    changes: dict[str, Any] = {}
    if args.headless:
        changes["headless"] = True
    if args.no_speech:
        changes["tts_enabled"] = False
    if args.search_engine:
        changes["search_engine"] = args.search_engine
    if args.log_level:
        changes["log_level"] = args.log_level
    if args.log_file is not None:
        changes["log_file"] = args.log_file
    return replace(settings, **changes) if changes else settings


class _ScriptedListener:
    """Replays a fixed list of commands, then exits.  Backs ``--command``."""

    def __init__(self, commands: Sequence[str]) -> None:
        self._remaining: list[str] = list(commands)

    def listen(self) -> str | None:
        if self._remaining:
            command = self._remaining.pop(0)
            print(f"You: {command}", flush=True)
            return command
        return "exit"

    def close(self) -> None:
        return None


def _make_listener(settings: Settings, args: argparse.Namespace) -> Listener:
    if args.command:
        return _ScriptedListener(args.command)
    if args.text:
        return ConsoleListener()
    return GoogleSpeechListener(settings)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point.  Returns a process exit code; never raises."""
    args = build_parser().parse_args(argv)

    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except ImportError:  # pragma: no cover - dependency is declared
        pass

    try:
        settings = apply_overrides(Settings.from_env(), args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    log_path = configure_logging(settings)
    if log_path:
        logger.info("Logging to %s", log_path)

    if args.doctor:
        return report(settings)

    speaker: Speaker = create_speaker(settings)
    listener = _make_listener(settings, args)
    browser = BrowserController(settings)

    try:
        browser.start()
    except BrowserError as exc:
        speaker.say("I could not start the browser.")
        print(f"Browser error: {exc}", file=sys.stderr)
        logger.error("Browser start failed: %s", exc)
        _close(speaker, listener)
        return EXIT_FAILURE

    assistant = VoiceAssistant(
        settings=settings,
        browser=browser,
        listener=listener,
        speaker=speaker,
        parser=CommandParser(known_sites=QUICK_SITES.keys()),
    )
    _install_signal_handlers(assistant)

    try:
        return assistant.run()
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        return EXIT_OK
    except VoiceAutomationError as exc:
        logger.error("Fatal error: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    finally:
        browser.quit()
        _close(speaker, listener)


def _install_signal_handlers(assistant: VoiceAssistant) -> None:
    """Ask the assistant to stop on SIGINT/SIGTERM rather than dying mid-action."""

    def _handler(signum, _frame):  # type: ignore[no-untyped-def]
        logger.info("Received signal %s; shutting down", signum)
        assistant.request_stop()

    for name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):  # pragma: no cover - non-main thread
            logger.debug("Could not install a handler for %s", name)


def _close(*closeables: object) -> None:
    for item in closeables:
        close = getattr(item, "close", None)
        if close is None:
            continue
        try:
            close()
        except Exception:
            logger.debug("Error closing %r", item, exc_info=True)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
