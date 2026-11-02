"""Speech capture.

Two behaviours changed from the original implementation:

*   Ambient-noise calibration ran on every single command, adding a second
    of dead air to each turn.  It now runs once at start-up and then only
    every ``recalibrate_every`` commands.
*   A recogniser-service outage was swallowed and reported as a generic
    error on every iteration.  It now raises
    :class:`~voice_automation.exceptions.SpeechServiceError` so the caller
    can back off instead of hammering the API in a tight loop.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

import speech_recognition as sr

from ..config import Settings
from ..exceptions import SpeechServiceError, SpeechUnavailableError
from .microphone import open_microphone

logger = logging.getLogger(__name__)


@runtime_checkable
class Listener(Protocol):
    """A source of user utterances."""

    def listen(self) -> str | None:
        """Return the next utterance, or ``None`` if nothing was heard."""

    def close(self) -> None:
        """Release any underlying resources."""


class ConsoleListener:
    """Reads commands from stdin.

    Lets the whole pipeline be exercised -- and demonstrated -- on a machine
    with no microphone, and makes end-to-end testing possible.
    """

    def __init__(self, prompt: str = "You: ") -> None:
        self._prompt = prompt

    def listen(self) -> str | None:
        try:
            return input(self._prompt).strip() or None
        except EOFError:
            return "exit"

    def close(self) -> None:
        return None


class GoogleSpeechListener:
    """Captures microphone audio and transcribes it with Google's free API."""

    def __init__(
        self,
        settings: Settings,
        recognizer: sr.Recognizer | None = None,
        microphone_factory=None,  # type: ignore[no-untyped-def]
    ) -> None:
        self._settings = settings
        self._recognizer = recognizer or sr.Recognizer()
        self._recognizer.pause_threshold = 0.8
        self._recognizer.dynamic_energy_threshold = settings.energy_threshold is None
        if settings.energy_threshold is not None:
            self._recognizer.energy_threshold = settings.energy_threshold
        self._microphone_factory = microphone_factory or (
            lambda: open_microphone(device_index=settings.microphone_index)
        )
        self._since_calibration = 0
        self._calibrated = False

    # ------------------------------------------------------------------
    def _open_microphone(self):  # type: ignore[no-untyped-def]
        try:
            return self._microphone_factory()
        except SpeechUnavailableError:
            raise
        except (OSError, AttributeError, ImportError) as exc:
            raise SpeechUnavailableError(
                "No usable microphone was found. Check that an input device is "
                "connected and that this application is permitted to use it."
            ) from exc

    def _maybe_calibrate(self, source) -> None:  # type: ignore[no-untyped-def]
        every = self._settings.recalibrate_every
        due = not self._calibrated or (every > 0 and self._since_calibration >= every)
        if not due or self._settings.ambient_calibration <= 0:
            return
        logger.debug("Calibrating for ambient noise")
        self._recognizer.adjust_for_ambient_noise(
            source, duration=self._settings.ambient_calibration
        )
        self._calibrated = True
        self._since_calibration = 0

    # ------------------------------------------------------------------
    def listen(self) -> str | None:
        """Capture one utterance.

        Returns ``None`` on silence or unintelligible audio (both normal).
        Raises :class:`SpeechUnavailableError` when the microphone is gone
        and :class:`SpeechServiceError` when the API cannot be reached.
        """
        try:
            with self._open_microphone() as source:
                self._maybe_calibrate(source)
                print("Listening...", flush=True)
                audio = self._recognizer.listen(
                    source,
                    timeout=self._settings.listen_timeout,
                    phrase_time_limit=self._settings.phrase_time_limit,
                )
        except sr.WaitTimeoutError:
            logger.debug("No speech detected within the listen timeout")
            return None
        except SpeechUnavailableError:
            raise
        except OSError as exc:
            raise SpeechUnavailableError(f"Microphone error: {exc}") from exc

        self._since_calibration += 1
        try:
            text = self._recognizer.recognize_google(
                audio, language=self._settings.speech_language
            )
        except sr.UnknownValueError:
            logger.debug("Speech was not intelligible")
            return None
        except sr.RequestError as exc:
            raise SpeechServiceError(
                f"Speech recognition service unavailable: {exc}"
            ) from exc

        text = (text or "").strip()
        if text:
            print(f"You: {text}", flush=True)
        return text or None

    def close(self) -> None:
        return None


def create_listener(settings: Settings, text_mode: bool = False) -> Listener:
    """Return a console listener in text mode, otherwise a microphone one."""
    if text_mode:
        return ConsoleListener()
    return GoogleSpeechListener(settings)
