"""Settings parsing and validation."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from voice_automation.config import SEARCH_ENGINES, Settings
from voice_automation.exceptions import ConfigError


def test_defaults_are_usable():
    settings = Settings.from_env({})
    assert settings.headless is False
    assert settings.search_engine == "google"
    assert settings.log_file is None
    assert settings.max_consecutive_failures >= 1


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on", "y"])
def test_truthy_booleans(raw):
    assert Settings.from_env({"VA_HEADLESS": raw}).headless is True


@pytest.mark.parametrize("raw", ["0", "false", "no", "off", "n"])
def test_falsy_booleans(raw):
    assert Settings.from_env({"VA_HEADLESS": raw}).headless is False


def test_bad_boolean_names_the_variable():
    with pytest.raises(ConfigError, match="VA_HEADLESS"):
        Settings.from_env({"VA_HEADLESS": "maybe"})


def test_bad_integer_names_the_variable():
    with pytest.raises(ConfigError, match="VA_SCROLL_STEP"):
        Settings.from_env({"VA_SCROLL_STEP": "lots"})


def test_out_of_range_values_are_rejected():
    with pytest.raises(ConfigError, match="VA_TTS_VOLUME"):
        Settings.from_env({"VA_TTS_VOLUME": "5"})
    with pytest.raises(ConfigError, match="VA_SCROLL_STEP"):
        Settings.from_env({"VA_SCROLL_STEP": "0"})


def test_unknown_search_engine_is_rejected():
    with pytest.raises(ConfigError, match="VA_SEARCH_ENGINE"):
        Settings.from_env({"VA_SEARCH_ENGINE": "altavista"})


@pytest.mark.parametrize("engine", sorted(SEARCH_ENGINES))
def test_each_engine_template_has_a_query_placeholder(engine):
    settings = Settings.from_env({"VA_SEARCH_ENGINE": engine})
    assert "{query}" in settings.search_url_template


def test_unknown_log_level_is_rejected():
    with pytest.raises(ConfigError, match="VA_LOG_LEVEL"):
        Settings.from_env({"VA_LOG_LEVEL": "CHATTY"})


def test_log_file_is_expanded(tmp_path):
    target = tmp_path / "logs" / "app.log"
    settings = Settings.from_env({"VA_LOG_FILE": str(target)})
    assert settings.log_file == Path(target)


def test_empty_values_fall_back_to_defaults():
    settings = Settings.from_env({"VA_HEADLESS": "", "VA_SCROLL_STEP": "  "})
    assert settings.headless is False
    assert settings.scroll_step == Settings().scroll_step


def test_overrides_are_recorded():
    settings = Settings.from_env({"VA_HEADLESS": "1", "UNRELATED": "x"})
    assert settings.overrides == ("VA_HEADLESS",)


def test_settings_are_immutable():
    settings = Settings()
    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.headless = True  # type: ignore[misc]


def test_energy_threshold_is_optional():
    assert Settings.from_env({}).energy_threshold is None
    assert Settings.from_env({"VA_ENERGY_THRESHOLD": "350"}).energy_threshold == 350
