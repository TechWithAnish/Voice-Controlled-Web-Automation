"""Discovery of installed browsers.

The assistant drives any Chromium-based browser (Chrome, Edge, Brave) or
Firefox.  Which one is used is a configuration choice, and by default the
first one actually installed is picked, so the project works on a machine
that has Edge and Brave but no Chrome.

Discovery looks in three places, in order of reliability:

1. the Windows registry ``App Paths`` keys, which are authoritative and
   survive non-standard install locations;
2. the usual install directories for the platform;
3. ``PATH``.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

__all__ = [
    "CHROMIUM_FAMILY",
    "BrowserInfo",
    "BrowserKind",
    "discover",
    "find_browser",
    "resolve_browser",
]


class BrowserKind(str, Enum):
    """A browser the assistant knows how to drive."""

    CHROME = "chrome"
    EDGE = "edge"
    BRAVE = "brave"
    FIREFOX = "firefox"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value

    @property
    def label(self) -> str:
        """Human-readable name."""
        return {
            BrowserKind.CHROME: "Google Chrome",
            BrowserKind.EDGE: "Microsoft Edge",
            BrowserKind.BRAVE: "Brave",
            BrowserKind.FIREFOX: "Mozilla Firefox",
        }[self]


#: Browsers that speak the Chrome DevTools Protocol and share ChromeOptions.
CHROMIUM_FAMILY = frozenset(
    {BrowserKind.CHROME, BrowserKind.EDGE, BrowserKind.BRAVE}
)

#: Order used when no browser is configured explicitly.
PREFERENCE_ORDER: tuple[BrowserKind, ...] = (
    BrowserKind.CHROME,
    BrowserKind.EDGE,
    BrowserKind.BRAVE,
    BrowserKind.FIREFOX,
)

#: Executable names to look for on PATH.
_COMMANDS: dict[BrowserKind, tuple[str, ...]] = {
    BrowserKind.CHROME: ("google-chrome", "google-chrome-stable", "chrome"),
    BrowserKind.EDGE: ("msedge", "microsoft-edge", "microsoft-edge-stable"),
    BrowserKind.BRAVE: ("brave", "brave-browser", "brave-browser-stable"),
    BrowserKind.FIREFOX: ("firefox", "firefox-esr"),
}

#: Windows ``App Paths`` registry keys.
_APP_PATHS: dict[BrowserKind, str] = {
    BrowserKind.CHROME: "chrome.exe",
    BrowserKind.EDGE: "msedge.exe",
    BrowserKind.BRAVE: "brave.exe",
    BrowserKind.FIREFOX: "firefox.exe",
}

#: Install locations relative to a Windows program-files root.
_WINDOWS_SUFFIXES: dict[BrowserKind, tuple[str, ...]] = {
    BrowserKind.CHROME: (r"Google\Chrome\Application\chrome.exe",),
    BrowserKind.EDGE: (r"Microsoft\Edge\Application\msedge.exe",),
    BrowserKind.BRAVE: (r"BraveSoftware\Brave-Browser\Application\brave.exe",),
    BrowserKind.FIREFOX: (r"Mozilla Firefox\firefox.exe",),
}

_MACOS_PATHS: dict[BrowserKind, tuple[str, ...]] = {
    BrowserKind.CHROME: (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ),
    BrowserKind.EDGE: (
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ),
    BrowserKind.BRAVE: (
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ),
    BrowserKind.FIREFOX: ("/Applications/Firefox.app/Contents/MacOS/firefox",),
}

_LINUX_PATHS: dict[BrowserKind, tuple[str, ...]] = {
    BrowserKind.CHROME: ("/opt/google/chrome/chrome", "/usr/bin/google-chrome"),
    BrowserKind.EDGE: ("/opt/microsoft/msedge/msedge", "/usr/bin/microsoft-edge"),
    BrowserKind.BRAVE: (
        "/opt/brave.com/brave/brave",
        "/usr/bin/brave-browser",
    ),
    BrowserKind.FIREFOX: ("/usr/bin/firefox", "/snap/bin/firefox"),
}


@dataclass(frozen=True)
class BrowserInfo:
    """An installed browser and where its executable lives."""

    kind: BrowserKind
    path: Path | None = None

    @property
    def label(self) -> str:
        return self.kind.label

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.label} ({self.path})" if self.path else self.label


# ---------------------------------------------------------------------------
# Platform-specific lookups
# ---------------------------------------------------------------------------


def _registry_path(kind: BrowserKind) -> Path | None:
    """Read a browser's location from the Windows ``App Paths`` registry key.

    This is the authoritative source on Windows: it is written by the
    installer and is correct even when the browser lives somewhere unusual.
    """
    if sys.platform != "win32":
        return None
    import winreg

    key_name = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{_APP_PATHS[kind]}"
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, key_name) as handle:
                value, _ = winreg.QueryValueEx(handle, None)
        except OSError:
            continue
        if not value:
            continue
        candidate = Path(str(value).strip('"'))
        if candidate.is_file():
            return candidate
    return None


def _windows_paths(kind: BrowserKind) -> list[Path]:
    roots = [
        os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    return [
        Path(root) / suffix
        for root in roots
        if root
        for suffix in _WINDOWS_SUFFIXES[kind]
    ]


def _known_paths(kind: BrowserKind) -> list[Path]:
    system = platform.system()
    if system == "Windows":
        return _windows_paths(kind)
    if system == "Darwin":
        return [Path(p) for p in _MACOS_PATHS[kind]]
    return [Path(p) for p in _LINUX_PATHS[kind]]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_browser(kind: BrowserKind) -> Path | None:
    """Return the executable for ``kind``, or ``None`` if it is not installed."""
    registry = _registry_path(kind)
    if registry is not None:
        return registry

    for candidate in _known_paths(kind):
        try:
            if candidate.is_file():
                return candidate
        except OSError:  # pragma: no cover - permission oddities
            continue

    for command in _COMMANDS[kind]:
        found = shutil.which(command)
        if found:
            return Path(found)
    return None


def discover(
    order: Sequence[BrowserKind] = PREFERENCE_ORDER,
) -> list[BrowserInfo]:
    """Return every installed browser, in preference order."""
    results = []
    for kind in order:
        path = find_browser(kind)
        if path is not None:
            results.append(BrowserInfo(kind=kind, path=path))
    return results


def resolve_browser(
    preference: str = "auto", binary: str | None = None
) -> BrowserInfo:
    """Decide which browser to drive.

    ``preference`` is a :class:`BrowserKind` value or ``"auto"``.  ``binary``
    overrides discovery with an explicit executable path.  Raises
    :class:`LookupError` when nothing suitable is installed, with a message
    naming what was searched for.
    """
    choice = (preference or "auto").strip().lower()

    if binary:
        kind = BrowserKind(choice) if choice != "auto" else _guess_kind(binary)
        return BrowserInfo(kind=kind, path=Path(binary))

    if choice == "auto":
        found = discover()
        if found:
            return found[0]
        names = ", ".join(kind.label for kind in PREFERENCE_ORDER)
        raise LookupError(
            f"No supported browser was found. Install one of: {names}; "
            f"or set VA_BROWSER_BINARY to an executable path."
        )

    try:
        kind = BrowserKind(choice)
    except ValueError as exc:
        options = ", ".join(k.value for k in BrowserKind)
        raise LookupError(
            f"Unknown browser {preference!r}. Choose one of: auto, {options}."
        ) from exc

    path = find_browser(kind)
    if path is None:
        raise LookupError(
            f"{kind.label} is not installed, or could not be found. "
            f"Set VA_BROWSER_BINARY to its executable path, or choose a "
            f"different VA_BROWSER."
        )
    return BrowserInfo(kind=kind, path=path)


def _guess_kind(binary: str) -> BrowserKind:
    """Infer the browser family from an executable path."""
    name = Path(binary).name.lower()
    if "firefox" in name:
        return BrowserKind.FIREFOX
    if "edge" in name:
        return BrowserKind.EDGE
    if "brave" in name:
        return BrowserKind.BRAVE
    return BrowserKind.CHROME
