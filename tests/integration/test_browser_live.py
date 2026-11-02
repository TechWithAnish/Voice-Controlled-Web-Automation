"""Live-browser checks, skipped unless explicitly selected.

Run them with:

    pytest -m browser

They need Chrome and a ChromeDriver, so CI runs the rest of the suite
without them. Their job is to prove that the locator strategies the unit
tests assert on are accepted by a real browser -- in particular that a
phrase containing an apostrophe no longer raises InvalidSelectorException.
"""

from __future__ import annotations

import shutil

import pytest

from voice_automation.browser import BrowserController, ScrollDirection
from voice_automation.config import Settings
from voice_automation.exceptions import ElementNotFoundError

pytestmark = pytest.mark.browser


def _chrome_available() -> bool:
    return any(
        shutil.which(name)
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chrome")
    )


@pytest.fixture(scope="module")
def browser():
    if not _chrome_available():
        pytest.skip("Chrome is not installed")
    settings = Settings(
        headless=True,
        disable_sandbox=True,
        maximize_window=False,
        element_timeout=6.0,
        chromedriver_path=shutil.which("chromedriver"),
    )
    controller = BrowserController(settings)
    controller.start()
    try:
        yield controller
    finally:
        controller.quit()


def test_navigation_and_title(browser, fixture_site):
    browser.go(fixture_site)
    assert browser.title() == "Fixture Page"
    assert browser.current_url().startswith("http://127.0.0.1")


def test_click_on_text_containing_an_apostrophe(browser, fixture_site):
    """The 1.x locator produced invalid XPath for any phrase with an apostrophe."""
    browser.go(fixture_site)
    label = browser.click_text("don't have an account")
    assert "account" in label.lower()
    assert browser.title().startswith("clicked:")


def test_click_by_aria_label_containing_double_quotes(browser, fixture_site):
    browser.go(fixture_site)
    browser.click_text('Save "draft"')
    assert browser.title().startswith("clicked:")


def test_click_partial_text(browser, fixture_site):
    browser.go(fixture_site)
    assert browser.click_text("sign in").lower() == "sign in"


def test_missing_element_raises_quickly(browser, fixture_site):
    import time

    browser.go(fixture_site)
    started = time.monotonic()
    with pytest.raises(ElementNotFoundError):
        browser.click_text("no such control anywhere")
    assert time.monotonic() - started < 15


def test_scrolling_moves_the_viewport(browser, fixture_site):
    browser.go(fixture_site)
    browser.scroll(ScrollDirection.BOTTOM)
    offset = browser.driver.execute_script("return window.pageYOffset;")
    assert offset > 0
    browser.scroll(ScrollDirection.TOP)


def test_history_navigation(browser, fixture_site):
    browser.go(fixture_site)
    browser.go(fixture_site + "?second=1")
    browser.back()
    assert "second" not in browser.current_url()
    browser.forward()
    browser.refresh()
