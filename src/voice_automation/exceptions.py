"""Exception hierarchy for the assistant.

Every failure mode the application deliberately recognises is represented
here.  Code outside this package should only ever need to catch
:class:`VoiceAutomationError`.
"""

from __future__ import annotations


class VoiceAutomationError(Exception):
    """Base class for every error raised by this package."""


class ConfigError(VoiceAutomationError):
    """Raised when configuration is missing, malformed or out of range."""


class BrowserError(VoiceAutomationError):
    """Raised when the browser cannot be started or driven."""


class BrowserUnavailableError(BrowserError):
    """Raised when the browser session has died and cannot be recovered."""


class ElementNotFoundError(BrowserError):
    """Raised when no element matching a spoken description could be found."""


class InvalidTargetError(VoiceAutomationError):
    """Raised when a spoken phrase cannot be resolved to a safe URL."""


class SpeechError(VoiceAutomationError):
    """Base class for speech-input failures."""


class SpeechUnavailableError(SpeechError):
    """Raised when no usable microphone or audio backend exists."""


class SpeechServiceError(SpeechError):
    """Raised when the remote speech-recognition service cannot be reached."""


class WeatherError(VoiceAutomationError):
    """Raised when weather information cannot be retrieved."""
