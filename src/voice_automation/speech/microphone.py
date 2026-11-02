"""Microphone backends.

``SpeechRecognition`` captures audio through PyAudio, which is a C extension.
PyPI carries prebuilt PyAudio wheels only for some Python versions, so on a
newer interpreter pip falls back to compiling it, and that needs a full C
toolchain -- "Microsoft Visual C++ 14.0 or greater is required" on Windows.
Requiring a 6 GB compiler install to use a voice assistant is not reasonable.

``sounddevice`` solves this: its wheels are tagged ``py3-none``, so one build
serves every Python 3 version, and the PortAudio library is bundled. This
module adapts it to the ``AudioSource`` interface the recogniser expects, and
picks whichever backend is installed.
"""

from __future__ import annotations

import importlib.util
import logging
from typing import Any

import speech_recognition as sr

from ..exceptions import SpeechUnavailableError

logger = logging.getLogger(__name__)

#: Backends in the order they are preferred. PyAudio first, because an
#: existing working install should keep being used.
BACKENDS = ("pyaudio", "sounddevice")

#: 16 kHz mono 16-bit is what the speech API wants, and keeps uploads small.
DEFAULT_SAMPLE_RATE = 16_000
DEFAULT_CHUNK = 1024
SAMPLE_WIDTH_BYTES = 2


def _installed(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):  # pragma: no cover - broken install
        return False


def available_backend() -> str | None:
    """Return the name of the first usable backend, or ``None``."""
    for name in BACKENDS:
        if _installed(name):
            return name
    return None


class _SoundDeviceStream:
    """Adapts a sounddevice raw stream to the ``read()`` contract.

    ``Recognizer`` calls ``source.stream.read(CHUNK)`` and expects exactly
    that many frames back as PCM bytes.
    """

    def __init__(self, stream: Any) -> None:
        self._stream = stream

    def read(self, frames: int) -> bytes:
        data, overflowed = self._stream.read(frames)
        if overflowed:
            # Dropped frames degrade recognition but are not fatal; the
            # recogniser simply sees a slightly shorter phrase.
            logger.debug("Audio input overflowed; some frames were dropped")
        return bytes(data)


class SoundDeviceMicrophone(sr.AudioSource):
    """An ``AudioSource`` backed by ``sounddevice`` instead of PyAudio."""

    def __init__(
        self,
        device: int | None = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        chunk_size: int = DEFAULT_CHUNK,
    ) -> None:
        # sr.AudioSource.__init__ raises by design; this is a sibling
        # implementation of the same interface, not a subclass extension.
        self.device = device
        self.SAMPLE_RATE = int(sample_rate)
        self.SAMPLE_WIDTH = SAMPLE_WIDTH_BYTES
        self.CHUNK = int(chunk_size)
        self.stream: _SoundDeviceStream | None = None
        self._raw: Any = None

    def __enter__(self) -> SoundDeviceMicrophone:
        try:
            import sounddevice
        except ImportError as exc:  # pragma: no cover - guarded by caller
            raise SpeechUnavailableError(
                "The sounddevice package is not installed."
            ) from exc

        try:
            self._raw = sounddevice.RawInputStream(
                samplerate=self.SAMPLE_RATE,
                blocksize=self.CHUNK,
                device=self.device,
                channels=1,
                dtype="int16",
            )
            self._raw.start()
        except Exception as exc:
            self._raw = None
            raise SpeechUnavailableError(
                f"Could not open the microphone: {exc}"
            ) from exc

        self.stream = _SoundDeviceStream(self._raw)
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.stream = None
        raw, self._raw = self._raw, None
        if raw is None:
            return
        try:
            raw.stop()
            raw.close()
        except Exception:
            logger.debug("Error closing the audio stream", exc_info=True)


def open_microphone(
    device_index: int | None = None,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    chunk_size: int = DEFAULT_CHUNK,
) -> sr.AudioSource:
    """Return an unopened microphone source using the best available backend.

    Raises :class:`SpeechUnavailableError`, naming both install options, when
    neither backend is present.
    """
    if _installed("pyaudio"):
        try:
            return sr.Microphone(
                device_index=device_index,
                sample_rate=sample_rate,
                chunk_size=chunk_size,
            )
        except (AttributeError, ImportError, OSError) as exc:
            # PyAudio is present but unusable; prefer a working backend over
            # failing outright.
            logger.warning("PyAudio is installed but unusable (%s)", exc)

    if _installed("sounddevice"):
        return SoundDeviceMicrophone(
            device=device_index, sample_rate=sample_rate, chunk_size=chunk_size
        )

    raise SpeechUnavailableError(
        "No audio input backend is installed. Install one with "
        "'pip install sounddevice' (prebuilt, no compiler needed) or "
        "'pip install PyAudio'. Text mode (--text) works without either."
    )


def list_microphones() -> list[str]:
    """Return the names of available input devices, newest backend first."""
    backend = available_backend()
    if backend == "pyaudio":
        try:
            return list(sr.Microphone.list_microphone_names())
        except Exception as exc:
            raise SpeechUnavailableError(f"PyAudio could not list devices: {exc}") from exc
    if backend == "sounddevice":
        try:
            import sounddevice

            return [
                str(device["name"])
                for device in sounddevice.query_devices()
                if int(device.get("max_input_channels", 0)) > 0
            ]
        except Exception as exc:
            raise SpeechUnavailableError(
                f"sounddevice could not list devices: {exc}"
            ) from exc
    raise SpeechUnavailableError("No audio input backend is installed.")
