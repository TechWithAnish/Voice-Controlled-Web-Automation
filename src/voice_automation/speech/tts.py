"""Text-to-speech output with a guaranteed fallback.

``pyttsx3`` depends on a platform speech engine (SAPI5, NSSpeechSynthesizer,
espeak).  On a server, in a container, or on a machine with no audio device
it fails at ``init()`` -- previously that aborted start-up.  Here a failure
degrades to console output so the assistant stays usable, and a run-loop
error re-initialises the engine once before giving up.
"""

from __future__ import annotations

import logging
import threading
from typing import Protocol, TextIO, runtime_checkable

from ..config import Settings

logger = logging.getLogger(__name__)


@runtime_checkable
class Speaker(Protocol):
    """Anything that can voice a line of text."""

    def say(self, text: str) -> None:
        """Speak (or otherwise present) ``text``."""

    def close(self) -> None:
        """Release any underlying resources."""


class ConsoleSpeaker:
    """Prints instead of speaking.  Used headless, in tests and as a fallback."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream

    def say(self, text: str) -> None:
        print(f"Assistant: {text}", file=self._stream)

    def close(self) -> None:
        return None


class Pyttsx3Speaker:
    """Speaks through ``pyttsx3``, echoing to the console as well.

    ``pyttsx3`` is not thread-safe and raises if ``runAndWait`` is re-entered,
    so calls are serialised with a lock.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._engine = self._create_engine()

    # -- engine management ----------------------------------------------
    def _create_engine(self):  # type: ignore[no-untyped-def]
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", self._settings.tts_rate)
        engine.setProperty("volume", self._settings.tts_volume)
        wanted = (self._settings.tts_voice or "").lower()
        if wanted:
            try:
                for voice in engine.getProperty("voices") or ():
                    if wanted in (voice.name or "").lower() or wanted == voice.id:
                        engine.setProperty("voice", voice.id)
                        break
                else:
                    logger.warning("No speech voice matching %r; using the default", wanted)
            except Exception:
                logger.debug("Could not enumerate voices", exc_info=True)
        return engine

    # -- Speaker --------------------------------------------------------
    def say(self, text: str) -> None:
        print(f"Assistant: {text}")
        with self._lock:
            for attempt in (1, 2):
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                    return
                except Exception:
                    logger.warning(
                        "Speech synthesis failed (attempt %s)", attempt, exc_info=True
                    )
                    if attempt == 1:
                        try:
                            self._engine = self._create_engine()
                        except Exception:
                            logger.error("Could not restart the speech engine", exc_info=True)
                            return

    def close(self) -> None:
        with self._lock:
            try:
                self._engine.stop()
            except Exception:
                logger.debug("Error stopping the speech engine", exc_info=True)


def create_speaker(settings: Settings) -> Speaker:
    """Build the best speaker available, never raising.

    Falls back to :class:`ConsoleSpeaker` when text-to-speech is disabled or
    unavailable, so the assistant always has a voice channel of some kind.
    """
    if not settings.tts_enabled:
        return ConsoleSpeaker()
    try:
        return Pyttsx3Speaker(settings)
    except Exception as exc:
        logger.warning("Text-to-speech unavailable (%s); falling back to console output", exc)
        return ConsoleSpeaker()
