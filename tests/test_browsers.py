"""Browser discovery and selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from voice_automation.browser import browsers
from voice_automation.browser.browsers import (
    CHROMIUM_FAMILY,
    PREFERENCE_ORDER,
    BrowserInfo,
    BrowserKind,
    discover,
    find_browser,
    resolve_browser,
)


@pytest.fixture
def no_browsers(monkeypatch):
    """Simulate a machine with nothing installed."""
    monkeypatch.setattr(browsers, "_registry_path", lambda kind: None)
    monkeypatch.setattr(browsers, "_known_paths", lambda kind: [])
    monkeypatch.setattr(browsers.shutil, "which", lambda name: None)


def install(monkeypatch, mapping):
    """Pretend the browsers in ``mapping`` ({BrowserKind: path}) are installed.

    Membership is tested with Path objects rather than strings: Path equality
    normalises separators, so the same fixture works on POSIX and Windows.
    """
    installed = {Path(location) for location in mapping.values()}
    monkeypatch.setattr(browsers, "_registry_path", lambda kind: None)
    monkeypatch.setattr(
        browsers,
        "_known_paths",
        lambda kind: [Path(mapping[kind])] if kind in mapping else [],
    )
    monkeypatch.setattr(browsers.shutil, "which", lambda name: None)
    monkeypatch.setattr(Path, "is_file", lambda self: self in installed)


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------

def test_every_kind_has_a_label():
    for kind in BrowserKind:
        assert kind.label and kind.label != kind.value


def test_chromium_family_excludes_firefox():
    assert BrowserKind.FIREFOX not in CHROMIUM_FAMILY
    assert {BrowserKind.CHROME, BrowserKind.EDGE, BrowserKind.BRAVE} == CHROMIUM_FAMILY


def test_preference_order_covers_every_kind():
    assert set(PREFERENCE_ORDER) == set(BrowserKind)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def test_nothing_installed(no_browsers):
    assert discover() == []
    for kind in BrowserKind:
        assert find_browser(kind) is None


def test_discovery_returns_preference_order(monkeypatch):
    install(
        monkeypatch,
        {
            BrowserKind.BRAVE: "/usr/bin/brave",
            BrowserKind.EDGE: "/usr/bin/msedge",
            BrowserKind.FIREFOX: "/usr/bin/firefox",
        },
    )
    found = discover()
    assert [info.kind for info in found] == [
        BrowserKind.EDGE,
        BrowserKind.BRAVE,
        BrowserKind.FIREFOX,
    ]


def test_path_lookup_is_used_as_a_fallback(monkeypatch):
    monkeypatch.setattr(browsers, "_registry_path", lambda kind: None)
    monkeypatch.setattr(browsers, "_known_paths", lambda kind: [])
    monkeypatch.setattr(
        browsers.shutil,
        "which",
        lambda name: "/snap/bin/firefox" if name == "firefox" else None,
    )
    assert find_browser(BrowserKind.FIREFOX) == Path("/snap/bin/firefox")
    assert find_browser(BrowserKind.CHROME) is None


def test_registry_wins_over_standard_paths(monkeypatch):
    """The Windows registry is authoritative for non-standard installs."""
    monkeypatch.setattr(
        browsers,
        "_registry_path",
        lambda kind: Path("D:/Apps/brave.exe") if kind is BrowserKind.BRAVE else None,
    )
    monkeypatch.setattr(browsers, "_known_paths", lambda kind: [Path("/wrong/brave")])
    monkeypatch.setattr(browsers.shutil, "which", lambda name: None)
    assert find_browser(BrowserKind.BRAVE) == Path("D:/Apps/brave.exe")


def test_registry_is_skipped_off_windows(monkeypatch):
    monkeypatch.setattr(browsers.sys, "platform", "linux")
    assert browsers._registry_path(BrowserKind.CHROME) is None


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def test_auto_picks_the_first_installed(monkeypatch):
    """A machine with Edge and Brave but no Chrome must still work."""
    install(
        monkeypatch,
        {BrowserKind.EDGE: "/usr/bin/msedge", BrowserKind.BRAVE: "/usr/bin/brave"},
    )
    assert resolve_browser("auto").kind is BrowserKind.EDGE


def test_explicit_choice_is_honoured(monkeypatch):
    install(
        monkeypatch,
        {BrowserKind.EDGE: "/usr/bin/msedge", BrowserKind.BRAVE: "/usr/bin/brave"},
    )
    chosen = resolve_browser("brave")
    assert chosen.kind is BrowserKind.BRAVE
    assert chosen.path == Path("/usr/bin/brave")


def test_explicit_choice_that_is_not_installed_explains_itself(monkeypatch):
    install(monkeypatch, {BrowserKind.EDGE: "/usr/bin/msedge"})
    with pytest.raises(LookupError, match="Brave is not installed"):
        resolve_browser("brave")


def test_auto_with_nothing_installed_lists_the_options(no_browsers):
    with pytest.raises(LookupError, match="No supported browser"):
        resolve_browser("auto")


def test_unknown_browser_name_is_rejected(no_browsers):
    with pytest.raises(LookupError, match="Unknown browser"):
        resolve_browser("netscape")


def test_explicit_binary_skips_discovery(no_browsers):
    chosen = resolve_browser("auto", binary="/opt/weird/brave-browser")
    assert chosen.kind is BrowserKind.BRAVE
    assert chosen.path == Path("/opt/weird/brave-browser")


@pytest.mark.parametrize(
    ("binary", "kind"),
    [
        ("/usr/bin/firefox", BrowserKind.FIREFOX),
        (r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", BrowserKind.EDGE),
        (r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe", BrowserKind.BRAVE),
        ("/opt/google/chrome/chrome", BrowserKind.CHROME),
        ("/some/unknown/binary", BrowserKind.CHROME),
    ],
)
def test_binary_family_is_inferred(binary, kind, no_browsers):
    assert resolve_browser("auto", binary=binary).kind is kind


def test_explicit_kind_with_binary_is_not_overridden(no_browsers):
    chosen = resolve_browser("edge", binary="/custom/path/to/browser")
    assert chosen.kind is BrowserKind.EDGE


def test_browser_info_renders_readably():
    info = BrowserInfo(kind=BrowserKind.BRAVE, path=Path("/usr/bin/brave"))
    assert "Brave" in str(info)
    assert info.label == "Brave"
