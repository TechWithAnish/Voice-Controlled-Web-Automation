"""A small, safe action surface over Selenium.

Design notes
------------
*   Any Chromium-based browser (Chrome, Edge, Brave) or Firefox can be
    driven; see :mod:`voice_automation.browser.browsers`.  The browser is a
    configuration choice and defaults to whichever one is installed.
*   Drivers are resolved by Selenium Manager, which ships with Selenium and
    downloads a matching driver for the detected browser version.  An
    explicit driver can still be pinned with ``VA_DRIVER_PATH``.
*   The controller owns the driver's lifetime and is a context manager, so a
    crash can never leak a browser process.
*   Element lookup uses a single bounded :class:`WebDriverWait` that tries
    every locator strategy on each poll, rather than a separate timeout per
    strategy.
*   Every phrase interpolated into XPath goes through
    :func:`~voice_automation.browser.xpath.xpath_literal`.
*   ``--no-sandbox`` is opt-in rather than always on.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from enum import Enum
from types import TracebackType
from typing import TYPE_CHECKING, Any

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    InvalidSelectorException,
    NoSuchWindowException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from ..config import Settings
from ..exceptions import BrowserError, BrowserUnavailableError, ElementNotFoundError
from .browsers import BrowserInfo, BrowserKind, resolve_browser
from .xpath import lowercase_expr, xpath_literal

if TYPE_CHECKING:  # pragma: no cover
    from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)


class ScrollDirection(str, Enum):
    """Supported scroll targets."""

    UP = "up"
    DOWN = "down"
    TOP = "top"
    BOTTOM = "bottom"


#: Tags a click can plausibly target, used to keep ``contains()`` lookups from
#: matching ``<body>``.
_INTERACTIVE = (
    "a",
    "button",
    "input",
    "summary",
    "label",
    "option",
    "*[@role='button']",
    "*[@role='link']",
    "*[@role='tab']",
    "*[@role='menuitem']",
)

_WINDOW_WIDTH = 1920
_WINDOW_HEIGHT = 1080


def _build_options(settings: Settings, info: BrowserInfo) -> Any:
    """Build the options object for ``info``'s browser family."""
    if info.kind is BrowserKind.FIREFOX:
        return _firefox_options(settings, info)
    return _chromium_options(settings, info)


def _chromium_options(settings: Settings, info: BrowserInfo) -> Any:
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions

    options = EdgeOptions() if info.kind is BrowserKind.EDGE else ChromeOptions()

    if settings.headless:
        options.add_argument("--headless=new")
        options.add_argument(f"--window-size={_WINDOW_WIDTH},{_WINDOW_HEIGHT}")
    if settings.disable_sandbox:
        # Only appropriate inside a container; weakens the browser sandbox.
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

    # Chromium forks such as Brave are driven by chromedriver, which must be
    # told which binary to launch; naming it is harmless for Chrome and Edge.
    if info.path is not None:
        options.binary_location = str(info.path)

    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    # Suppress the noisy DevTools listener banner on Windows.
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return options


def _firefox_options(settings: Settings, info: BrowserInfo) -> Any:
    from selenium.webdriver.firefox.options import Options as FirefoxOptions

    options = FirefoxOptions()
    if settings.headless:
        options.add_argument("-headless")
        options.add_argument("--width")
        options.add_argument(str(_WINDOW_WIDTH))
        options.add_argument("--height")
        options.add_argument(str(_WINDOW_HEIGHT))
    if info.path is not None:
        options.binary_location = str(info.path)
    return options


def _build_service(settings: Settings, info: BrowserInfo) -> Any:
    """Return a Service for ``info``, or ``None`` to let Selenium Manager decide."""
    if not settings.driver_path:
        return None
    if info.kind is BrowserKind.FIREFOX:
        from selenium.webdriver.firefox.service import Service as FirefoxService

        return FirefoxService(executable_path=settings.driver_path)
    if info.kind is BrowserKind.EDGE:
        from selenium.webdriver.edge.service import Service as EdgeService

        return EdgeService(executable_path=settings.driver_path)
    from selenium.webdriver.chrome.service import Service as ChromeService

    return ChromeService(executable_path=settings.driver_path)


def _driver_class(kind: BrowserKind) -> Any:
    if kind is BrowserKind.FIREFOX:
        return webdriver.Firefox
    if kind is BrowserKind.EDGE:
        return webdriver.Edge
    return webdriver.Chrome


class BrowserController:
    """Owns a browser session and exposes only the actions the assistant needs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver: Any | None = None
        self._info: BrowserInfo | None = None

    # -- lifecycle ------------------------------------------------------
    @property
    def info(self) -> BrowserInfo | None:
        """Which browser this controller launched, once started."""
        return self._info

    def start(self) -> None:
        """Launch the browser.  Raises :class:`BrowserError` on failure."""
        if self._driver is not None:
            return

        try:
            info = resolve_browser(
                self._settings.browser, self._settings.browser_binary
            )
        except LookupError as exc:
            raise BrowserError(str(exc)) from exc

        options = _build_options(self._settings, info)
        service = _build_service(self._settings, info)
        factory = _driver_class(info.kind)

        try:
            self._driver = (
                factory(service=service, options=options)
                if service is not None
                else factory(options=options)
            )
            self._driver.set_page_load_timeout(self._settings.page_load_timeout)
            if self._settings.maximize_window and not self._settings.headless:
                try:
                    self._driver.maximize_window()
                except WebDriverException:  # pragma: no cover - window manager quirk
                    logger.debug("Could not maximise the window", exc_info=True)
            self._info = info
            logger.info(
                "%s started (headless=%s)", info.label, self._settings.headless
            )
        except WebDriverException as exc:
            raise BrowserError(
                f"Could not start {info.label}: {exc.msg or exc}"
            ) from exc
        except Exception as exc:  # driver download, permissions, ...
            raise BrowserError(f"Could not start {info.label}: {exc}") from exc

    def __enter__(self) -> BrowserController:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.quit()

    def quit(self) -> None:
        """Close the browser.  Safe to call repeatedly and from a signal handler."""
        driver, self._driver = self._driver, None
        if driver is None:
            return
        try:
            driver.quit()
            logger.info("Browser closed")
        except Exception:
            logger.warning("Error while closing the browser", exc_info=True)

    # -- state ----------------------------------------------------------
    @property
    def driver(self) -> Any:
        if self._driver is None:
            raise BrowserUnavailableError("The browser is not running")
        return self._driver

    @property
    def is_alive(self) -> bool:
        """True when the session still responds."""
        if self._driver is None:
            return False
        try:
            _ = self._driver.current_url
            return True
        except WebDriverException:
            return False

    def current_url(self) -> str:
        try:
            return str(self.driver.current_url)
        except WebDriverException as exc:
            raise BrowserUnavailableError(f"Browser session lost: {exc.msg or exc}") from exc

    def title(self) -> str:
        try:
            return str(self.driver.title)
        except WebDriverException as exc:
            raise BrowserUnavailableError(f"Browser session lost: {exc.msg or exc}") from exc

    # -- navigation -----------------------------------------------------
    def go(self, url: str) -> None:
        """Navigate to an absolute URL.

        A page-load timeout is reported but not treated as fatal: the
        document is usually usable even when a third-party asset stalls.
        """
        try:
            self.driver.get(url)
        except TimeoutException:
            logger.warning(
                "Page load timed out after %ss: %s",
                self._settings.page_load_timeout,
                url,
            )
        except (NoSuchWindowException, BrowserUnavailableError) as exc:
            raise BrowserUnavailableError(f"Browser session lost: {exc}") from exc
        except WebDriverException as exc:
            raise BrowserError(f"Could not open {url}: {exc.msg or exc}") from exc

    def back(self) -> None:
        self._history("back")

    def forward(self) -> None:
        self._history("forward")

    def refresh(self) -> None:
        self._history("refresh")

    def _history(self, action: str) -> None:
        try:
            getattr(self.driver, action)()
        except TimeoutException:
            logger.warning("%s timed out", action)
        except WebDriverException as exc:
            raise BrowserError(f"Could not {action}: {exc.msg or exc}") from exc

    # -- scrolling ------------------------------------------------------
    def scroll(self, direction: ScrollDirection, pixels: int | None = None) -> None:
        """Scroll the viewport.

        ``pixels`` is clamped to a sane range so a misheard "scroll down nine
        million" cannot be passed through to the page.
        """
        step = pixels if pixels is not None else self._settings.scroll_step
        step = max(1, min(int(step), self._settings.max_scroll_step))
        scripts = {
            ScrollDirection.DOWN: f"window.scrollBy({{top: {step}, behavior: 'smooth'}});",
            ScrollDirection.UP: f"window.scrollBy({{top: -{step}, behavior: 'smooth'}});",
            ScrollDirection.TOP: "window.scrollTo({top: 0, behavior: 'smooth'});",
            ScrollDirection.BOTTOM: (
                "window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});"
            ),
        }
        try:
            self.driver.execute_script(scripts[direction])
        except WebDriverException as exc:
            raise BrowserError(f"Could not scroll {direction.value}: {exc.msg or exc}") from exc

    # -- clicking -------------------------------------------------------
    def click_text(self, description: str, timeout: float | None = None) -> str:
        """Click the first visible element matching ``description``.

        Returns the text of the element that was clicked.  Raises
        :class:`ElementNotFoundError` when nothing matches within the
        timeout, which bounds the whole search rather than each strategy.
        """
        phrase = " ".join(description.split())
        if not phrase:
            raise ElementNotFoundError("No element description was given")

        wait = WebDriverWait(
            self.driver,
            self._settings.element_timeout if timeout is None else timeout,
            poll_frequency=0.3,
        )
        locators = self._locators(phrase)
        try:
            element = wait.until(lambda _: self._first_visible(locators))
        except TimeoutException as exc:
            raise ElementNotFoundError(
                f"Could not find anything to click matching {phrase!r}"
            ) from exc
        except WebDriverException as exc:
            raise BrowserError(f"Could not search the page: {exc.msg or exc}") from exc

        label = (element.text or element.get_attribute("value") or phrase).strip()
        self._click(element, phrase)
        return label or phrase

    @staticmethod
    def _locators(phrase: str) -> Sequence[tuple[str, str]]:
        """Locator strategies ordered from most to least precise."""
        exact = xpath_literal(phrase)
        folded = xpath_literal(phrase.lower())
        interactive = " | ".join(f"//{tag}" for tag in _INTERACTIVE)
        contains_self = lowercase_expr("normalize-space(.)")
        return (
            (By.XPATH, f"//*[@aria-label={exact} or @title={exact}]"),
            (By.XPATH, f"//input[@value={exact} or @placeholder={exact}]"),
            (By.XPATH, f"//button[normalize-space(.)={exact}]"),
            (By.XPATH, f"//a[normalize-space(.)={exact}]"),
            (By.PARTIAL_LINK_TEXT, phrase),
            (
                By.XPATH,
                " | ".join(
                    f"//{tag}[contains({contains_self}, {folded})]" for tag in _INTERACTIVE
                ),
            ),
            (
                By.XPATH,
                f"({interactive})[contains({lowercase_expr('@aria-label')}, {folded})]",
            ),
            (
                By.XPATH,
                f"//*[contains({lowercase_expr('text()')}, {folded})]",
            ),
        )

    def _first_visible(self, locators: Sequence[tuple[str, str]]) -> WebElement | None:
        """Return the first displayed, enabled element any locator finds."""
        for by, value in locators:
            try:
                candidates: list[WebElement] = self.driver.find_elements(by, value)
            except InvalidSelectorException:
                # Should not happen now that literals are escaped, but a
                # malformed selector must never abort the whole search.
                logger.debug("Invalid selector skipped: %s %s", by, value, exc_info=True)
                continue
            except StaleElementReferenceException:  # pragma: no cover - timing
                continue
            for candidate in candidates:
                try:
                    if candidate.is_displayed() and candidate.is_enabled():
                        return candidate
                except StaleElementReferenceException:  # pragma: no cover - timing
                    continue
        return None

    def _click(self, element: WebElement, phrase: str) -> None:
        """Click ``element``, scrolling it into view and falling back to JS."""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
                element,
            )
        except WebDriverException:  # pragma: no cover - best effort
            logger.debug("Could not scroll element into view", exc_info=True)

        try:
            element.click()
            return
        except (
            ElementClickInterceptedException,
            ElementNotInteractableException,
            StaleElementReferenceException,
        ):
            logger.debug("Native click failed for %r; trying JS click", phrase)
        except WebDriverException as exc:
            raise BrowserError(f"Could not click {phrase!r}: {exc.msg or exc}") from exc

        try:
            self.driver.execute_script("arguments[0].click();", element)
        except WebDriverException as exc:
            raise ElementNotFoundError(
                f"Found {phrase!r} but it could not be clicked"
            ) from exc
