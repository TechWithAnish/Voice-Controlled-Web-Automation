"""Speech-to-intent parsing.

This subpackage is deliberately free of I/O: given a string it returns a
:class:`~voice_automation.commands.models.Command`.  That makes the most
failure-prone part of the system exhaustively testable without a microphone,
a browser or a network connection.
"""

from __future__ import annotations

from .models import Command, Intent
from .parser import CommandParser, normalise

__all__ = ["Command", "CommandParser", "Intent", "normalise"]
