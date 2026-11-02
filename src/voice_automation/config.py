"""Typed application settings, loaded from the environment.

All tunables live here rather than being scattered as literals through the
code.  ``Settings.from_env`` performs validation up front so that a bad value
fails at start-up with a precise message instead of surfacing as a confusing
error deep inside a browser call.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

from .exceptions import ConfigError

ENV_PREFIX = "VA_"

#: Search engines the assistant knows how to drive.
SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={query}",
    "duckduckgo": "https://duckduckgo.com/?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
}

#: Accepted values for VA_BROWSER. "auto" picks the first one installed.
BROWSER_CHOICES = frozenset({"auto", "chrome", "edge", "brave", "firefox"})

_TRUE = {"1", "true", "yes", "on", "y"}
_FALSE = {"0", "false", "no", "off", "n"}


def _env_name(key: str) -> str:
    return f"{ENV_PREFIX}{key.upper()}"


def _get_bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = env.get(_env_name(key))
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ConfigError(
        f"{_env_name(key)} must be a boolean (one of {sorted(_TRUE | _FALSE)}), got {raw!r}"
    )


def _get_int(
    env: Mapping[str, str],
    key: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = env.get(_env_name(key))
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"{_env_name(key)} must be an integer, got {raw!r}") from exc
    return _check_range(_env_name(key), value, minimum, maximum)


def _get_float(
    env: Mapping[str, str],
    key: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    raw = env.get(_env_name(key))
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"{_env_name(key)} must be a number, got {raw!r}") from exc
    return _check_range(_env_name(key), value, minimum, maximum)


def _check_range(name, value, minimum, maximum):  # type: ignore[no-untyped-def]
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}, got {value}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be <= {maximum}, got {value}")
    return value


def _get_str(
    env: Mapping[str, str], key: str, default: str | None
) -> str | None:
    raw = env.get(_env_name(key))
    if raw is None or raw.strip() == "":
        return default
    return raw.strip()


@dataclass(frozen=True)
class Settings:
    """Immutable runtime configuration.

    Every field maps to an environment variable named ``VA_<FIELD>``; for
    example ``headless`` is read from ``VA_HEADLESS``.
    """

    # --- browser -------------------------------------------------------
    #: "auto" picks the first installed browser; otherwise one of
    #: chrome, edge, brave or firefox.
    browser: str = "auto"
    headless: bool = False
    maximize_window: bool = True
    page_load_timeout: float = 30.0
    element_timeout: float = 8.0
    scroll_step: int = 400
    max_scroll_step: int = 20_000
    #: Explicit path to the browser executable, when discovery cannot find it.
    browser_binary: str | None = None
    #: Explicit driver path; by default Selenium Manager resolves one.
    driver_path: str | None = None
    #: ``--no-sandbox`` weakens Chrome's sandbox. Required inside most
    #: containers, never appropriate on a workstation, hence opt-in.
    disable_sandbox: bool = False

    # --- speech input --------------------------------------------------
    speech_language: str = "en-US"
    #: Index of the input device; None uses the system default.
    microphone_index: int | None = None
    listen_timeout: float = 8.0
    phrase_time_limit: float = 10.0
    ambient_calibration: float = 1.0
    #: Re-calibrate for background noise every N commands (0 disables).
    recalibrate_every: int = 25
    energy_threshold: int | None = None

    # --- speech output -------------------------------------------------
    tts_enabled: bool = True
    tts_rate: int = 180
    tts_volume: float = 0.9
    tts_voice: str | None = None

    # --- services ------------------------------------------------------
    search_engine: str = "google"
    weather_timeout: float = 10.0
    default_weather_city: str | None = None

    # --- logging -------------------------------------------------------
    log_level: str = "INFO"
    log_file: Path | None = None
    log_max_bytes: int = 1_048_576
    log_backup_count: int = 3

    # --- resilience ----------------------------------------------------
    max_consecutive_failures: int = 5

    #: Populated by ``from_env`` so callers can report what was overridden.
    overrides: tuple = field(default=(), compare=False, repr=False)

    # ------------------------------------------------------------------
    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        """Build settings from ``env`` (defaults to ``os.environ``).

        Raises :class:`ConfigError` with the offending variable name when a
        value cannot be parsed or falls outside its permitted range.
        """
        source: Mapping[str, str] = os.environ if env is None else env
        defaults = cls()

        log_file_raw = _get_str(source, "log_file", None)
        engine = (_get_str(source, "search_engine", defaults.search_engine) or "").lower()
        if engine not in SEARCH_ENGINES:
            raise ConfigError(
                f"{_env_name('search_engine')} must be one of "
                f"{sorted(SEARCH_ENGINES)}, got {engine!r}"
            )

        browser = (_get_str(source, "browser", defaults.browser) or "").lower()
        if browser not in BROWSER_CHOICES:
            raise ConfigError(
                f"{_env_name('browser')} must be one of "
                f"{sorted(BROWSER_CHOICES)}, got {browser!r}"
            )

        level = (_get_str(source, "log_level", defaults.log_level) or "").upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigError(
                f"{_env_name('log_level')} must be a standard logging level, got {level!r}"
            )

        settings = cls(
            headless=_get_bool(source, "headless", defaults.headless),
            maximize_window=_get_bool(source, "maximize_window", defaults.maximize_window),
            page_load_timeout=_get_float(
                source, "page_load_timeout", defaults.page_load_timeout, minimum=1.0, maximum=600.0
            ),
            element_timeout=_get_float(
                source, "element_timeout", defaults.element_timeout, minimum=0.5, maximum=120.0
            ),
            scroll_step=_get_int(
                source, "scroll_step", defaults.scroll_step, minimum=1, maximum=20_000
            ),
            browser=browser,
            browser_binary=_get_str(source, "browser_binary", defaults.browser_binary),
            driver_path=_get_str(source, "driver_path", defaults.driver_path),
            disable_sandbox=_get_bool(source, "disable_sandbox", defaults.disable_sandbox),
            speech_language=_get_str(source, "speech_language", defaults.speech_language)
            or defaults.speech_language,
            microphone_index=(
                None
                if _get_str(source, "microphone_index", None) is None
                else _get_int(source, "microphone_index", 0, minimum=0, maximum=512)
            ),
            listen_timeout=_get_float(
                source, "listen_timeout", defaults.listen_timeout, minimum=1.0, maximum=300.0
            ),
            phrase_time_limit=_get_float(
                source, "phrase_time_limit", defaults.phrase_time_limit, minimum=1.0, maximum=300.0
            ),
            ambient_calibration=_get_float(
                source,
                "ambient_calibration",
                defaults.ambient_calibration,
                minimum=0.0,
                maximum=10.0,
            ),
            recalibrate_every=_get_int(
                source, "recalibrate_every", defaults.recalibrate_every, minimum=0, maximum=10_000
            ),
            energy_threshold=(
                None
                if _get_str(source, "energy_threshold", None) is None
                else _get_int(source, "energy_threshold", 300, minimum=0, maximum=100_000)
            ),
            tts_enabled=_get_bool(source, "tts_enabled", defaults.tts_enabled),
            tts_rate=_get_int(source, "tts_rate", defaults.tts_rate, minimum=50, maximum=500),
            tts_volume=_get_float(
                source,
                "tts_volume",
                defaults.tts_volume,
                minimum=0.0,
                maximum=1.0,
            ),
            tts_voice=_get_str(source, "tts_voice", defaults.tts_voice),
            search_engine=engine,
            weather_timeout=_get_float(
                source, "weather_timeout", defaults.weather_timeout, minimum=1.0, maximum=120.0
            ),
            default_weather_city=_get_str(
                source, "default_weather_city", defaults.default_weather_city
            ),
            log_level=level,
            log_file=Path(log_file_raw).expanduser() if log_file_raw else None,
            log_max_bytes=_get_int(
                source, "log_max_bytes", defaults.log_max_bytes, minimum=1024
            ),
            log_backup_count=_get_int(
                source, "log_backup_count", defaults.log_backup_count, minimum=0, maximum=100
            ),
            max_consecutive_failures=_get_int(
                source,
                "max_consecutive_failures",
                defaults.max_consecutive_failures,
                minimum=1,
                maximum=1000,
            ),
        )

        overrides = tuple(sorted(k for k in source if k.startswith(ENV_PREFIX)))
        return replace(settings, overrides=overrides)

    # ------------------------------------------------------------------
    @property
    def search_url_template(self) -> str:
        """URL template for the configured search engine."""
        return SEARCH_ENGINES[self.search_engine]
