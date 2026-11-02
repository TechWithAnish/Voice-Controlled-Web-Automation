"""Speech input and output, with the audio stack faked."""

from __future__ import annotations

from typing import ClassVar

import pytest
import speech_recognition as sr

from voice_automation.config import Settings
from voice_automation.exceptions import SpeechServiceError, SpeechUnavailableError
from voice_automation.speech.listener import ConsoleListener, GoogleSpeechListener
from voice_automation.speech.tts import ConsoleSpeaker, Speaker, create_speaker


class FakeSource:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeRecognizer:
    """Stands in for ``sr.Recognizer`` without touching any audio hardware."""

    def __init__(self, transcript="open youtube", listen_error=None, recognise_error=None):
        self.transcript = transcript
        self.listen_error = listen_error
        self.recognise_error = recognise_error
        self.calibrations = 0
        self.pause_threshold = 0.0
        self.dynamic_energy_threshold = False
        self.energy_threshold = 0

    def adjust_for_ambient_noise(self, source, duration=1):
        self.calibrations += 1

    def listen(self, source, timeout=None, phrase_time_limit=None):
        if self.listen_error:
            raise self.listen_error
        return b"audio"

    def recognize_google(self, audio, language="en-US"):
        if self.recognise_error:
            raise self.recognise_error
        return self.transcript


def make_listener(**kwargs):
    recognizer = FakeRecognizer(**kwargs)
    listener = GoogleSpeechListener(
        Settings(ambient_calibration=0.5, recalibrate_every=3),
        recognizer=recognizer,
        microphone_factory=FakeSource,
    )
    return listener, recognizer


def test_transcribes_an_utterance():
    listener, _ = make_listener()
    assert listener.listen() == "open youtube"


def test_calibration_is_not_repeated_on_every_command():
    """Calibrating each turn added a second of dead air to every command."""
    listener, recognizer = make_listener()
    for _ in range(3):
        listener.listen()
    assert recognizer.calibrations == 1


def test_calibration_recurs_after_the_configured_interval():
    listener, recognizer = make_listener()
    for _ in range(4):
        listener.listen()
    assert recognizer.calibrations == 2


def test_silence_returns_none():
    listener, _ = make_listener(listen_error=sr.WaitTimeoutError())
    assert listener.listen() is None


def test_unintelligible_audio_returns_none():
    listener, _ = make_listener(recognise_error=sr.UnknownValueError())
    assert listener.listen() is None


def test_service_outage_raises_so_the_caller_can_back_off():
    listener, _ = make_listener(recognise_error=sr.RequestError("api down"))
    with pytest.raises(SpeechServiceError):
        listener.listen()


def test_missing_microphone_raises_a_clear_error():
    def explode():
        raise OSError("no default input device")

    listener = GoogleSpeechListener(
        Settings(), recognizer=FakeRecognizer(), microphone_factory=explode
    )
    with pytest.raises(SpeechUnavailableError, match="microphone"):
        listener.listen()


def test_blank_transcript_is_treated_as_silence():
    listener, _ = make_listener(transcript="   ")
    assert listener.listen() is None


def test_console_listener_reads_stdin(monkeypatch):
    responses = iter(["open youtube", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
    listener = ConsoleListener()
    assert listener.listen() == "open youtube"
    assert listener.listen() is None


def test_console_listener_exits_on_eof(monkeypatch):
    def raise_eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    assert ConsoleListener().listen() == "exit"


# ---------------------------------------------------------------------------
# Text to speech
# ---------------------------------------------------------------------------

def test_console_speaker_prints(capsys):
    ConsoleSpeaker().say("hello")
    assert "Assistant: hello" in capsys.readouterr().out


def test_disabled_tts_uses_the_console():
    assert isinstance(create_speaker(Settings(tts_enabled=False)), ConsoleSpeaker)


def test_tts_failure_falls_back_to_the_console(monkeypatch):
    """A machine with no audio engine must still run, printing instead."""
    import voice_automation.speech.tts as tts

    def explode(settings):
        raise RuntimeError("no speech engine")

    monkeypatch.setattr(tts, "Pyttsx3Speaker", explode)
    speaker = tts.create_speaker(Settings(tts_enabled=True))
    assert isinstance(speaker, ConsoleSpeaker)


def test_speakers_satisfy_the_protocol():
    assert isinstance(ConsoleSpeaker(), Speaker)


class FakeVoice:
    def __init__(self, name, identifier):
        self.name = name
        self.id = identifier


class FakeEngine:
    """Minimal stand-in for a pyttsx3 engine."""

    instances: ClassVar[list] = []

    def __init__(self, fail_times=0):
        self.properties = {}
        self.spoken = []
        self.stopped = False
        self.fail_times = fail_times
        self.run_calls = 0
        FakeEngine.instances.append(self)

    def setProperty(self, name, value):  # pyttsx3 API spelling
        self.properties[name] = value

    def getProperty(self, name):  # pyttsx3 API spelling
        if name == "voices":
            return [FakeVoice("Microsoft Zira", "zira-id"), FakeVoice("David", "david-id")]
        return self.properties.get(name)

    def say(self, text):
        self.spoken.append(text)

    def runAndWait(self):  # pyttsx3 API spelling
        self.run_calls += 1
        if self.run_calls <= self.fail_times:
            raise RuntimeError("run loop already started")

    def stop(self):
        self.stopped = True


@pytest.fixture
def fake_pyttsx3(monkeypatch):
    import sys
    import types

    FakeEngine.instances.clear()
    module = types.ModuleType("pyttsx3")
    module.init = lambda *a, **k: FakeEngine()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyttsx3", module)
    return module


def test_pyttsx3_speaker_applies_settings(fake_pyttsx3):
    from voice_automation.speech.tts import Pyttsx3Speaker

    speaker = Pyttsx3Speaker(Settings(tts_rate=210, tts_volume=0.5, tts_voice="zira"))
    engine = FakeEngine.instances[-1]
    assert engine.properties["rate"] == 210
    assert engine.properties["volume"] == 0.5
    assert engine.properties["voice"] == "zira-id"

    speaker.say("hello")
    assert engine.spoken == ["hello"]
    speaker.close()
    assert engine.stopped is True


def test_unknown_voice_falls_back_to_the_default(fake_pyttsx3, caplog):
    from voice_automation.speech.tts import Pyttsx3Speaker

    Pyttsx3Speaker(Settings(tts_voice="no-such-voice"))
    assert "no speech voice matching" in caplog.text.lower()


def test_engine_is_restarted_once_after_a_failure(fake_pyttsx3, monkeypatch):
    """pyttsx3 raises if its run loop is re-entered; one restart is attempted."""
    from voice_automation.speech.tts import Pyttsx3Speaker

    monkeypatch.setattr(fake_pyttsx3, "init", lambda *a, **k: FakeEngine(fail_times=1))
    speaker = Pyttsx3Speaker(Settings())
    speaker.say("hello")
    assert len(FakeEngine.instances) == 2
    assert FakeEngine.instances[-1].spoken == ["hello"]


def test_close_never_raises(fake_pyttsx3, monkeypatch):
    from voice_automation.speech.tts import Pyttsx3Speaker

    speaker = Pyttsx3Speaker(Settings())
    monkeypatch.setattr(
        FakeEngine.instances[-1],
        "stop",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    speaker.close()


def test_create_speaker_uses_pyttsx3_when_available(fake_pyttsx3):
    from voice_automation.speech.tts import Pyttsx3Speaker, create_speaker

    assert isinstance(create_speaker(Settings(tts_enabled=True)), Pyttsx3Speaker)
