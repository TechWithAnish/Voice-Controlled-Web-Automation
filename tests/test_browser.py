"""Browser controller logic, exercised against a fake WebDriver."""

from __future__ import annotations

import pytest
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    InvalidSelectorException,
    TimeoutException,
    WebDriverException,
)

from voice_automation.browser.controller import BrowserController, ScrollDirection
from voice_automation.config import Settings
from voice_automation.exceptions import (
    BrowserError,
    BrowserUnavailableError,
    ElementNotFoundError,
)


class FakeElement:
    def __init__(self, text="Sign in", displayed=True, enabled=True, click_error=None):
        self._text = text
        self._displayed = displayed
        self._enabled = enabled
        self._click_error = click_error
        self.clicks = 0

    @property
    def text(self):
        return self._text

    def get_attribute(self, name):
        return None

    def is_displayed(self):
        return self._displayed

    def is_enabled(self):
        return self._enabled

    def click(self):
        self.clicks += 1
        if self._click_error:
            raise self._click_error


class FakeDriver:
    def __init__(self, elements: list[FakeElement] | None = None, find_error=None):
        self.elements = elements or []
        self.find_error = find_error
        self.scripts: list[str] = []
        self.urls: list[str] = []
        self.history: list[str] = []
        self.current_url = "https://example.com/"
        self.title = "Example Domain"
        self.quit_calls = 0
        self.page_load_timeout = None

    def set_page_load_timeout(self, value):
        self.page_load_timeout = value

    def get(self, url):
        self.urls.append(url)
        self.current_url = url

    def back(self):
        self.history.append("back")

    def forward(self):
        self.history.append("forward")

    def refresh(self):
        self.history.append("refresh")

    def execute_script(self, script, *args):
        self.scripts.append(script)

    def find_elements(self, by, value):
        if self.find_error:
            raise self.find_error
        return list(self.elements)

    def quit(self):
        self.quit_calls += 1


def controller_with(driver, **overrides):
    defaults = {"element_timeout": 0.6, "scroll_step": 400}
    defaults.update(overrides)
    settings = Settings(**defaults)
    controller = BrowserController(settings)
    controller._driver = driver
    return controller


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def test_quit_is_idempotent():
    driver = FakeDriver()
    controller = controller_with(driver)
    controller.quit()
    controller.quit()
    assert driver.quit_calls == 1


def test_quit_never_raises():
    class BadDriver(FakeDriver):
        def quit(self):
            raise WebDriverException("already gone")

    controller_with(BadDriver()).quit()


def test_actions_before_start_raise_unavailable():
    controller = BrowserController(Settings())
    with pytest.raises(BrowserUnavailableError):
        controller.current_url()


def test_is_alive_reflects_the_session():
    controller = BrowserController(Settings())
    assert controller.is_alive is False
    controller._driver = FakeDriver()
    assert controller.is_alive is True


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def test_go_navigates():
    driver = FakeDriver()
    controller_with(driver).go("https://example.com")
    assert driver.urls == ["https://example.com"]


def test_page_load_timeout_is_not_fatal():
    class SlowDriver(FakeDriver):
        def get(self, url):
            raise TimeoutException("too slow")

    controller_with(SlowDriver()).go("https://example.com")  # must not raise


def test_navigation_error_is_wrapped():
    class BadDriver(FakeDriver):
        def get(self, url):
            raise WebDriverException("DNS failure")

    with pytest.raises(BrowserError, match="Could not open"):
        controller_with(BadDriver()).go("https://example.com")


def test_history_actions():
    driver = FakeDriver()
    controller = controller_with(driver)
    controller.back()
    controller.forward()
    controller.refresh()
    assert driver.history == ["back", "forward", "refresh"]


# ---------------------------------------------------------------------------
# Scrolling
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("direction", "fragment"),
    [
        (ScrollDirection.DOWN, "top: 400"),
        (ScrollDirection.UP, "top: -400"),
        (ScrollDirection.TOP, "top: 0"),
        (ScrollDirection.BOTTOM, "document.body.scrollHeight"),
    ],
)
def test_scroll_scripts(direction, fragment):
    driver = FakeDriver()
    controller_with(driver).scroll(direction)
    assert fragment in driver.scripts[0]


def test_scroll_distance_is_clamped():
    """A misheard 'scroll down nine million' must not reach the page."""
    driver = FakeDriver()
    controller = controller_with(driver)
    controller.scroll(ScrollDirection.DOWN, 9_000_000)
    assert "top: 20000" in driver.scripts[0]
    controller.scroll(ScrollDirection.DOWN, -5)
    assert "top: 1" in driver.scripts[1]


# ---------------------------------------------------------------------------
# Clicking
# ---------------------------------------------------------------------------

def test_click_returns_the_element_label():
    element = FakeElement(text="Sign in")
    controller = controller_with(FakeDriver([element]))
    assert controller.click_text("sign in") == "Sign in"
    assert element.clicks == 1


def test_click_skips_invisible_elements():
    hidden = FakeElement(text="Hidden", displayed=False)
    visible = FakeElement(text="Visible")
    controller = controller_with(FakeDriver([hidden, visible]))
    assert controller.click_text("anything") == "Visible"


def test_missing_element_raises_within_the_timeout():
    controller = controller_with(FakeDriver([]))
    with pytest.raises(ElementNotFoundError, match="nowhere"):
        controller.click_text("nowhere")


def test_whole_search_is_bounded_by_one_timeout():
    """The original code waited 5s per strategy, so a miss cost ~30s."""
    import time

    controller = controller_with(FakeDriver([]), element_timeout=0.5)
    started = time.monotonic()
    with pytest.raises(ElementNotFoundError):
        controller.click_text("nowhere")
    assert time.monotonic() - started < 3.0


def test_intercepted_click_falls_back_to_javascript():
    element = FakeElement(click_error=ElementClickInterceptedException("overlay"))
    driver = FakeDriver([element])
    controller = controller_with(driver)
    controller.click_text("sign in")
    assert any("arguments[0].click()" in script for script in driver.scripts)


def test_invalid_selector_does_not_abort_the_search():
    driver = FakeDriver([], find_error=InvalidSelectorException("bad"))
    controller = controller_with(driver)
    with pytest.raises(ElementNotFoundError):
        controller.click_text("sign in")


def test_empty_description_is_rejected():
    controller = controller_with(FakeDriver([]))
    with pytest.raises(ElementNotFoundError):
        controller.click_text("   ")


# ---------------------------------------------------------------------------
# Generated XPath must be valid XPath 1.0
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "phrase",
    [
        "sign in",
        "don't have an account",
        "O'Brien",
        'say "hello"',
        """it's a "quote\"""",
        "100% off",
        "a & b",
        "<script>",
    ],
)
def test_every_generated_locator_compiles(phrase):
    """Interpolating an apostrophe used to raise InvalidSelectorException."""
    etree = pytest.importorskip("lxml.etree")
    from selenium.webdriver.common.by import By

    for by, value in BrowserController._locators(phrase):
        if by != By.XPATH:
            continue
        etree.XPath(value)  # raises XPathSyntaxError if malformed


# ---------------------------------------------------------------------------
# Chrome option construction and start-up
# ---------------------------------------------------------------------------

def test_headless_adds_the_right_flags():
    from voice_automation.browser.controller import _build_options

    arguments = _build_options(Settings(headless=True)).arguments
    assert "--headless=new" in arguments
    assert any(a.startswith("--window-size") for a in arguments)


def test_sandbox_is_not_disabled_by_default():
    """--no-sandbox weakens Chrome's sandbox; it must be opt-in."""
    from voice_automation.browser.controller import _build_options

    assert "--no-sandbox" not in _build_options(Settings()).arguments
    assert "--no-sandbox" in _build_options(Settings(disable_sandbox=True)).arguments


def test_deprecated_automation_extension_option_is_gone():
    """useAutomationExtension was removed from Chrome and now raises."""
    from voice_automation.browser.controller import _build_options

    experimental = _build_options(Settings()).experimental_options
    assert "useAutomationExtension" not in experimental


def test_chrome_binary_override_is_applied():
    from voice_automation.browser.controller import _build_options

    options = _build_options(Settings(chrome_binary="/opt/chrome/chrome"))
    assert options.binary_location == "/opt/chrome/chrome"


def test_start_wraps_driver_failures(monkeypatch):
    import voice_automation.browser.controller as module

    def explode(service, options):
        raise WebDriverException("chromedriver unreadable")

    monkeypatch.setattr(module.webdriver, "Chrome", explode)
    controller = BrowserController(Settings(chromedriver_path="chromedriver-stub"))
    with pytest.raises(BrowserError, match="Could not start Chrome"):
        controller.start()


def test_start_is_idempotent(monkeypatch):
    import voice_automation.browser.controller as module

    created = []

    def make(service, options):
        driver = FakeDriver()
        created.append(driver)
        return driver

    monkeypatch.setattr(module.webdriver, "Chrome", make)
    controller = BrowserController(
        Settings(chromedriver_path="chromedriver-stub", headless=True)
    )
    controller.start()
    controller.start()
    assert len(created) == 1
    assert created[0].page_load_timeout == Settings().page_load_timeout


def test_context_manager_always_quits(monkeypatch):
    import voice_automation.browser.controller as module

    driver = FakeDriver()
    monkeypatch.setattr(module.webdriver, "Chrome", lambda service, options: driver)
    controller = BrowserController(
        Settings(chromedriver_path="chromedriver-stub", headless=True)
    )
    with pytest.raises(ValueError), controller:
        raise ValueError("boom")
    assert driver.quit_calls == 1
