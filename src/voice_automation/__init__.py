"""Voice-controlled web automation.

A hands-free assistant that drives a real browser from spoken commands.

The package is organised in layers so that each one can be tested on its own:

``config``      typed settings loaded from the environment
``commands``    speech-to-intent parsing (pure functions, no I/O)
``browser``     Selenium wrapper exposing a small, safe action surface
``speech``      microphone capture and text-to-speech, behind protocols
``services``    outbound HTTP integrations (weather)
``assistant``   orchestration of the above
``cli``         argument parsing and process lifecycle
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "2.1.0"
