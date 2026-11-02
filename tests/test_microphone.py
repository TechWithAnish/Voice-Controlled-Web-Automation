"""Microphone backends, with the audio stack faked."""

from __future__ import annotations

import struct
import sys
import types

import pytest
import speech_recognition as sr

from voice_automation.exceptions import SpeechUnavailableError
from voice_automation.speech import microphone
from voice_automation.speech.microphone import (
    BACKENDS,
    SoundDeviceMicrophone,
    available_backend,
    list_microphones,
    open_microphone,
)


def pcm(amplitude: int, frames: int) -> bytes:
    """A mono 16-bit PCM buffer of constant amplitude."""
    return struct.pack(f"<{frames}h", *([amplitude] * frames))


class FakeRawStream:
    """Stands in for ``sounddevice.RawInputStream``."""

    def __init__(self, chunks=None, overflow=False, **kwargs):
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.closed = False
        self._chunks = list(chunks or [])
        self._overflow = overflow

    def start(self):
        self.started = True

    def read(self, frames):
        chunk = self._chunks.pop(0) if self._chunks else pcm(0, frames)
        return chunk, self._overflow

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


def fake_sounddevice(monkeypatch, stream=None, devices=None):
    """Install a fake ``sounddevice`` module and report which stream was made."""
    created = {}

    def RawInputStream(**kwargs):
        built = stream or FakeRawStream(**kwargs)
        built.kwargs = kwargs
        created["stream"] = built
        return built

    module = types.ModuleType("sounddevice")
    module.RawInputStream = RawInputStream
    module.query_devices = lambda: devices or []
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    return created


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

def test_pyaudio_is_preferred_when_present(monkeypatch):
    monkeypatch.setattr(microphone, "_installed", lambda name: name == "pyaudio")
    assert available_backend() == "pyaudio"


def test_sounddevice_is_used_when_pyaudio_is_absent(monkeypatch):
    """PyAudio has no prebuilt wheel for every Python; sounddevice does."""
    monkeypatch.setattr(microphone, "_installed", lambda name: name == "sounddevice")
    assert available_backend() == "sounddevice"


def test_no_backend_returns_none(monkeypatch):
    monkeypatch.setattr(microphone, "_installed", lambda name: False)
    assert available_backend() is None


def test_backend_order_is_stable():
    assert BACKENDS == ("pyaudio", "sounddevice")


def test_open_microphone_explains_both_install_routes(monkeypatch):
    monkeypatch.setattr(microphone, "_installed", lambda name: False)
    with pytest.raises(SpeechUnavailableError) as excinfo:
        open_microphone()
    message = str(excinfo.value)
    assert "sounddevice" in message
    assert "PyAudio" in message
    assert "--text" in message


def test_open_microphone_uses_pyaudio_when_it_works(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(microphone, "_installed", lambda name: name == "pyaudio")
    monkeypatch.setattr(microphone.sr, "Microphone", lambda **kwargs: sentinel)
    assert open_microphone() is sentinel


def test_broken_pyaudio_falls_back_to_sounddevice(monkeypatch):
    """A half-installed PyAudio must not block a working backend."""

    def explode(**kwargs):
        raise AttributeError("Could not find PyAudio; check installation")

    monkeypatch.setattr(microphone, "_installed", lambda name: True)
    monkeypatch.setattr(microphone.sr, "Microphone", explode)
    assert isinstance(open_microphone(), SoundDeviceMicrophone)


def test_open_microphone_returns_a_sounddevice_source(monkeypatch):
    monkeypatch.setattr(microphone, "_installed", lambda name: name == "sounddevice")
    assert isinstance(open_microphone(device_index=3), SoundDeviceMicrophone)


# ---------------------------------------------------------------------------
# The AudioSource contract
# ---------------------------------------------------------------------------

def test_it_is_a_real_audio_source():
    """Recognizer asserts isinstance(source, AudioSource)."""
    assert isinstance(SoundDeviceMicrophone(), sr.AudioSource)


def test_stream_is_only_available_inside_the_context(monkeypatch):
    """Recognizer asserts source.stream is not None before reading."""
    fake_sounddevice(monkeypatch)
    mic = SoundDeviceMicrophone()
    assert mic.stream is None
    with mic as entered:
        assert entered.stream is not None
    assert mic.stream is None


def test_stream_settings_are_passed_through(monkeypatch):
    created = fake_sounddevice(monkeypatch)
    with SoundDeviceMicrophone(device=2, sample_rate=22050, chunk_size=512):
        kwargs = created["stream"].kwargs
    assert kwargs["device"] == 2
    assert kwargs["samplerate"] == 22050
    assert kwargs["blocksize"] == 512
    assert kwargs["channels"] == 1
    assert kwargs["dtype"] == "int16"


def test_read_returns_bytes_of_the_expected_length(monkeypatch):
    fake_sounddevice(monkeypatch, stream=FakeRawStream())
    with SoundDeviceMicrophone(chunk_size=256) as mic:
        buffer = mic.stream.read(mic.CHUNK)
    assert isinstance(buffer, bytes)
    assert len(buffer) == 256 * mic.SAMPLE_WIDTH


def test_overflow_is_tolerated(monkeypatch):
    """A dropped frame shortens the phrase; it must not raise."""
    fake_sounddevice(monkeypatch, stream=FakeRawStream(overflow=True))
    with SoundDeviceMicrophone(chunk_size=128) as mic:
        assert len(mic.stream.read(mic.CHUNK)) == 128 * 2


def test_stream_is_closed_on_exit(monkeypatch):
    stream = FakeRawStream()
    fake_sounddevice(monkeypatch, stream=stream)
    with SoundDeviceMicrophone():
        pass
    assert stream.started and stream.stopped and stream.closed


def test_close_errors_are_swallowed(monkeypatch):
    class BadStream(FakeRawStream):
        def stop(self):
            raise RuntimeError("device vanished")

    fake_sounddevice(monkeypatch, stream=BadStream())
    with SoundDeviceMicrophone():
        pass  # teardown must not raise


def test_open_failure_is_reported_clearly(monkeypatch):
    module = types.ModuleType("sounddevice")

    def explode(**kwargs):
        raise OSError("Invalid device")

    module.RawInputStream = explode
    module.query_devices = list
    monkeypatch.setitem(sys.modules, "sounddevice", module)

    with (
        pytest.raises(SpeechUnavailableError, match="Could not open the microphone"),
        SoundDeviceMicrophone(),
    ):
        pass


# ---------------------------------------------------------------------------
# End to end against the real recogniser
# ---------------------------------------------------------------------------

def test_recognizer_captures_a_phrase_through_the_adapter(monkeypatch):
    """The strongest check: the real Recognizer drives the fake device."""
    chunk = 1024
    speech = [pcm(6000, chunk)] * 8
    silence = [pcm(0, chunk)] * 30
    fake_sounddevice(monkeypatch, stream=FakeRawStream(chunks=silence[:2] + speech + silence))

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = 300
    recognizer.non_speaking_duration = 0.2
    recognizer.pause_threshold = 0.3

    with SoundDeviceMicrophone(chunk_size=chunk) as mic:
        audio = recognizer.listen(mic, timeout=10, phrase_time_limit=5)

    assert isinstance(audio, sr.AudioData)
    assert audio.sample_rate == mic.SAMPLE_RATE
    assert audio.sample_width == mic.SAMPLE_WIDTH
    assert len(audio.get_raw_data()) > 0


def test_ambient_calibration_works_through_the_adapter(monkeypatch):
    fake_sounddevice(monkeypatch, stream=FakeRawStream())
    recognizer = sr.Recognizer()
    with SoundDeviceMicrophone() as mic:
        recognizer.adjust_for_ambient_noise(mic, duration=0.2)
    assert recognizer.energy_threshold >= 0


# ---------------------------------------------------------------------------
# Device listing
# ---------------------------------------------------------------------------

def test_only_input_devices_are_listed(monkeypatch):
    monkeypatch.setattr(microphone, "_installed", lambda name: name == "sounddevice")
    fake_sounddevice(
        monkeypatch,
        devices=[
            {"name": "Speakers", "max_input_channels": 0},
            {"name": "Mic Array", "max_input_channels": 2},
            {"name": "Webcam", "max_input_channels": 1},
        ],
    )
    assert list_microphones() == ["Mic Array", "Webcam"]


def test_listing_without_a_backend_raises(monkeypatch):
    monkeypatch.setattr(microphone, "_installed", lambda name: False)
    with pytest.raises(SpeechUnavailableError):
        list_microphones()
