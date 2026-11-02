"""A small, safe action surface over Selenium.

Design notes
------------
*   The controller owns the driver's lifetime and is a context manager, so a
    crash can never leak a Chrome process.
*   Element lookup uses a single bounded :class:`WebDriverWait` that tries
    every locator strategy on each poll.  The original implementation waited
    five seconds per strategy in sequence, so a miss cost thirty seconds of
    silence; here the whole search is capped by one timeout.
*   Every phrase interpolated into XPath goes through
    :func:`~voice_automation.browser.xpath.xpath_literal`.
*   ``--no-sandbox`` is opt-in rather than always on.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from enum import Enum
from types import TracebackType
from typing import TYPE_CHECKING

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
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from ..config import Settings
from ..exceptions import BrowserError, BrowserUnavailableError, ElementNotFoundError
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


def _build_options(settings: Settings) -> ChromeOptions:
    """Translate :class:`Settings` into Chrome options."""
    options = ChromeOptions()
    if settings.headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    if settings.disable_sandbox:
        # Only appropriate inside a container; weakens Chrome's sandbox.
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    if settings.chrome_binary:
        options.binary_location = settings.chrome_binary

    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    # Suppress the noisy DevTools listener banner on Windows.
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return options


class BrowserController:
    """Owns a Chrome session and exposes only the actions the assistant needs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver: webdriver.Chrome | None = None

    # -- lifecycle ------------------------------------------------------
    def start(self) -> None:
        """Launch Chrome.  Raises :class:`BrowserError` on failure."""
        if self._driver is not None:
            return
        try:
            service = self._build_service()
            self._driver = webdriver.Chrome(
                service=service, options=_build_options(self._settings)
            )
            self._driver.set_page_load_timeout(self._settings.page_load_timeout)
            if self._settings.maximize_window and not self._settings.headless:
                try:
                    self._driver.maximize_window()
                except WebDriverException:  # pragma: no cover - window manager quirk
                    logger.debug("Could not maximise the window", exc_info=True)
            logger.info("Chrome started (headless=%s)", self._settings.headless)
        except WebDriverException as exc:
            raise BrowserError(f"Could not start Chrome: {exc.msg or exc}") from exc
        except Exception as exc:  # driver download, permissions, ...
            raise BrowserError(f"Could not start Chrome: {exc}") from exc

    def _build_service(self) -> Service:
        if self._settings.chromedriver_path:
            return Service(executable_path=self._settings.chromedriver_path)
        # Imported lazily so that an offline run with an explicit driver path
        # does not pay for the manager's network check.
        from webdriver_manager.chrome import ChromeDriverManager

        return Service(ChromeDriverManager().install())

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
        """Close Chrome.  Safe to call repeatedly and from a signal handler."""
        driver, self._driver = self._driver, None
        if driver is None:
            return
        try:
            driver.quit()
            logger.info("Chrome closed")
        except Exception:
            logger.warning("Error while closing Chrome", exc_info=True)

    # -- state ----------------------------------------------------------
    @property
    def driver(self) -> webdriver.Chrome:
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
            return self.driver.current_url
        except WebDriverException as exc:
            raise BrowserUnavailableError(f"Browser session lost: {exc.msg or exc}") from exc

    def title(self) -> str:
        try:
            return self.driver.title
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
