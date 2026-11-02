"""Audio input and output, behind protocols so they can be faked in tests."""

from __future__ import annotations

from .listener import ConsoleListener, GoogleSpeechListener, Listener
from .tts import ConsoleSpeaker, Pyttsx3Speaker, Speaker, create_speaker

__all__ = [
    "ConsoleListener",
    "ConsoleSpeaker",
    "GoogleSpeechListener",
    "Listener",
    "Pyttsx3Speaker",
    "Speaker",
    "create_speaker",
]
