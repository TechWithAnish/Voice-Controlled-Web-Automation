"""Audio input and output, behind protocols so they can be faked in tests."""

from __future__ import annotations

from .listener import ConsoleListener, GoogleSpeechListener, Listener
from .microphone import (
    SoundDeviceMicrophone,
    available_backend,
    list_microphones,
    open_microphone,
)
from .tts import ConsoleSpeaker, Pyttsx3Speaker, Speaker, create_speaker

__all__ = [
    "ConsoleListener",
    "ConsoleSpeaker",
    "GoogleSpeechListener",
    "Listener",
    "Pyttsx3Speaker",
    "SoundDeviceMicrophone",
    "Speaker",
    "available_backend",
    "create_speaker",
    "list_microphones",
    "open_microphone",
]
