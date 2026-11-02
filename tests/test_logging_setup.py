"""Logging configuration."""

from __future__ import annotations

import logging

from voice_automation.config import Settings
from voice_automation.logging_setup import configure_logging


def test_no_file_handler_by_default():
    path = configure_logging(Settings(), console=False)
    assert path is None
    assert not any(
        isinstance(h, logging.FileHandler) for h in logging.getLogger().handlers
    )


def test_file_logging_rotates(tmp_path):
    target = tmp_path / "nested" / "app.log"
    path = configure_logging(
        Settings(log_file=target, log_max_bytes=2048, log_backup_count=2), console=False
    )
    assert path == target
    assert target.parent.is_dir()
    logging.getLogger("voice_automation.test").error("hello")
    assert "hello" in target.read_text(encoding="utf-8")


def test_repeated_configuration_does_not_duplicate_handlers(tmp_path):
    settings = Settings(log_file=tmp_path / "a.log")
    configure_logging(settings, console=True)
    first = len(logging.getLogger().handlers)
    configure_logging(settings, console=True)
    assert len(logging.getLogger().handlers) == first


def test_unwritable_log_path_does_not_crash(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    path = configure_logging(Settings(log_file=blocker / "app.log"), console=False)
    assert path is None


def test_noisy_third_party_loggers_are_quietened():
    configure_logging(Settings(log_level="DEBUG"), console=False)
    assert logging.getLogger("selenium").level == logging.WARNING
    assert logging.getLogger("urllib3").level == logging.WARNING


def teardown_module(module):
    configure_logging(Settings(), console=False)
