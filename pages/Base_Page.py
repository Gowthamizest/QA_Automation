"""Reusable synchronous Playwright actions and Page Object Model foundation. Locators remain owned by page objects."""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Iterable

from playwright.sync_api import Locator, Page, expect
from utils.logger import get_logger

logger = get_logger(__name__)


class BasePage:
    def __init__(self, page: Page, base_url: str | None = None):
        self.page = page
        self.base_url = base_url

    def _locator(self, target: str | Locator) -> Locator:
        return target if isinstance(target, Locator) else self.page.locator(target)

    def _run(self, action: str, target: str | Locator, fn, *args, **kwargs):
        loc = self._locator(target)
        label = str(target)
        logger.info("ACTION start | %s | locator=%s", action, label)
        try:
            result = fn(loc, *args, **kwargs)
            logger.info("ACTION success | %s | locator=%s", action, label)
            return result
        except Exception:
            try:
                setattr(self.page, "_last_failed_locator", loc)
            except Exception:
                pass
            logger.exception("ACTION failed | %s | locator=%s | url=%s", action, label, self.page.url)
            raise

    # -------------------------------------------------------------------------
    # Navigation & Page Lifecycle
    # -------------------------------------------------------------------------

    def open_application(self, url: str | None = None):
        target = url or self.base_url
        if not target:
            raise ValueError(
                "Application URL not found. Pass a URL to open_application() or configure project/environment URL."
            )
        logger.info("Navigating to application: %s", target)
        self.page.goto(target, wait_until="domcontentloaded")

    def goto(self, url, **kwargs):
        return self.page.goto(url, **kwargs)

    def back(self, **kwargs):
        return self.page.go_back(**kwargs)

    def forward(self, **kwargs):
        return self.page.go_forward(**kwargs)

    def reload(self, **kwargs):
        return self.page.reload(**kwargs)

    def wait_for_load_state(self, state="domcontentloaded", timeout=None):
        return self.page.wait_for_load_state(state, timeout=timeout)

    def wait_for(self, target, state="visible", timeout=None):
        return self._locator(target).wait_for(state=state, timeout=timeout)

    # -------------------------------------------------------------------------
    # Basic User Actions
    # -------------------------------------------------------------------------

    def click(self, locator, **kwargs):
        return self._run("click", locator, lambda l: l.click(**kwargs))

    def double_click(self, locator, **kwargs):
        return self._run("double_click", locator, lambda l: l.dblclick(**kwargs))

    def right_click(self, locator, **kwargs):
        return self._run("right_click", locator, lambda l: l.click(button="right", **kwargs))

    def hover(self, locator, **kwargs):
        return self._run("hover", locator, lambda l: l.hover(**kwargs))

    def move_mouse_to_element(self, locator):
        return self._run("move_mouse", locator, lambda l: l.hover())

    def send_text(self, locator, text, **kwargs):
        return self._run("fill", locator, lambda l: l.fill(str(text), **kwargs))

    def fill(self, locator, text, **kwargs):
        return self.send_text(locator, text, **kwargs)

    def type_text(self, locator, text, **kwargs):
        return self._run("type", locator, lambda l: l.press_sequentially(str(text), **kwargs))

    def clear(self, locator):
        return self._run("clear", locator, lambda l: l.fill(""))

    def press(self, locator, key, **kwargs):
        return self._run("press", locator, lambda l: l.press(key, **kwargs))

    def focus(self, locator):
        return self._run("focus", locator, lambda l: l.focus())

    def select_text(self, locator, **kwargs):
        return self._run("select_text", locator, lambda l: l.select_text(**kwargs))

    def check(self, locator, **kwargs):
        return self._run("check", locator, lambda l: l.check(**kwargs))

    def uncheck(self, locator, **kwargs):
        return self._run("uncheck", locator, lambda l: l.uncheck(**kwargs))

    def select_radio(self, locator, **kwargs):
        return self._run("select_radio", locator, lambda l: l.check(**kwargs))

    def select_option(self, locator, option, **kwargs):
        return self._run("select_option", locator, lambda l: l.select_option(option, **kwargs))

    def select_multiple(self, locator, options, **kwargs):
        return self._run("select_multiple", locator, lambda l: l.select_option(options, **kwargs))

    def upload_file(self, locator, files, **kwargs):
        return self._run("upload_file", locator, lambda l: l.set_input_files(files, **kwargs))

    def scroll_into_view(self, locator, **kwargs):
        return self._run("scroll_into_view", locator, lambda l: l.scroll_into_view_if_needed(**kwargs))

    def scroll_page(self, x=0, y=500):
        self.page.mouse.wheel(x, y)

    # -------------------------------------------------------------------------
    # Getters & State Checks
    # -------------------------------------------------------------------------

    def get_text(self, locator):
        return self._run("get_text", locator, lambda l: l.inner_text())

    def get_input_value(self, locator):
        return self._run("get_input_value", locator, lambda l: l.input_value())

    def get_attribute(self, locator, name):
        return self._run("get_attribute", locator, lambda l: l.get_attribute(name))

    def exists(self, locator):
        return self._locator(locator).count() > 0

    def is_visible(self, locator):
        return self._locator(locator).is_visible()

    def is_hidden(self, locator):
        return self._locator(locator).is_hidden()

    def is_enabled(self, locator):
        return self._locator(locator).is_enabled()

    def is_disabled(self, locator):
        return self._locator(locator).is_disabled()

    def is_checked(self, locator):
        return self._locator(locator).is_checked()

    def is_editable(self, locator):
        return self._locator(locator).is_editable()

    def count(self, locator):
        return self._locator(locator).count()

    def get_all_text(self, locator):
        return self._locator(locator).all_text_contents()

    def get_all_attributes(self, locator, name):
        return [self._locator(locator).nth(i).get_attribute(name) for i in range(self.count(locator))]

    def get_title(self):
        return self.page.title()

    def get_page_title(self):
        return self.page.title()

    def get_url(self):
        return self.page.url

    # -------------------------------------------------------------------------
    # Assertions
    # -------------------------------------------------------------------------

    def assert_visible(self, locator, timeout=None):
        loc = self._locator(locator)
        try:
            expect(loc).to_be_visible(timeout=timeout)
        except Exception:
            try:
                setattr(self.page, "_last_failed_locator", loc)
            except Exception:
                pass
            raise

    def assert_not_visible(self, locator, timeout=None):
        expect(self._locator(locator)).not_to_be_visible(timeout=timeout)

    def assert_enabled(self, locator, timeout=None):
        loc = self._locator(locator)
        try:
            expect(loc).to_be_enabled(timeout=timeout)
        except Exception:
            try:
                setattr(self.page, "_last_failed_locator", loc)
            except Exception:
                pass
            raise

    def assert_disabled(self, locator, timeout=None):
        loc = self._locator(locator)
        try:
            expect(loc).to_be_disabled(timeout=timeout)
        except Exception:
            try:
                setattr(self.page, "_last_failed_locator", loc)
            except Exception:
                pass
            raise

    def assert_present(self, locator, timeout=None):
        loc = self._locator(locator)
        try:
            loc.wait_for(state="attached", timeout=timeout)
        except Exception as exc:
            try:
                setattr(self.page, "_last_failed_locator", loc)
            except Exception:
                pass
            raise AssertionError(
                f"Expected element to be present; locator={locator!s}; url={self.page.url}; cause={exc}"
            ) from exc

    def assert_absent(self, locator, timeout=None):
        try:
            self._locator(locator).wait_for(state="detached", timeout=timeout)
        except Exception as exc:
            raise AssertionError(
                f"Expected element to be absent; locator={locator!s}; url={self.page.url}; cause={exc}"
            ) from exc

    def assert_text(self, locator, expected, timeout=None):
        loc = self._locator(locator)
        try:
            expect(loc).to_have_text(expected, timeout=timeout)
        except Exception as exc:
            try:
                setattr(self.page, "_last_failed_locator", loc)
            except Exception:
                pass
            raise AssertionError(
                f"Text assertion failed; locator={locator!s}; expected={expected!r}; url={self.page.url}"
            ) from exc

    def assert_text_contains(self, locator, expected, timeout=None):
        loc = self._locator(locator)
        try:
            expect(loc).to_contain_text(expected, timeout=timeout)
        except Exception as exc:
            try:
                setattr(self.page, "_last_failed_locator", loc)
            except Exception:
                pass
            raise AssertionError(
                f"Text containment failed; locator={locator!s}; expected substring={expected!r}; url={self.page.url}"
            ) from exc

    def assert_url(self, expected, contains=False, timeout=None):
        pattern = re.compile(re.escape(expected)) if contains else expected
        try:
            expect(self.page).to_have_url(pattern, timeout=timeout)
        except AssertionError as exc:
            mode = "to contain " if contains else ""
            raise AssertionError(
                f"URL assertion failed; expected {mode}{expected!r}; actual={self.page.url!r}"
            ) from exc

    def assert_title(self, expected, contains=False, timeout=None):
        pattern = re.compile(re.escape(expected)) if contains else expected
        try:
            expect(self.page).to_have_title(pattern, timeout=timeout)
        except AssertionError as exc:
            mode = "to contain " if contains else ""
            raise AssertionError(
                f"Page title assertion failed; expected {mode}{expected!r}; actual={self.page.title()!r}; url={self.page.url}"
            ) from exc

    def handle_new_page(self, action):
        with self.page.context.expect_page() as page_info:
            action()
        return page_info.value

    def open_new_tab(self, action):
        return self.handle_new_page(action)

    # -------------------------------------------------------------------------
    # Red Border Box Highlighting & Screenshot Capture (Self-Contained in POM)
    # -------------------------------------------------------------------------

    @staticmethod
    def highlight_element(page: Page | None, locator: Any = None, error_message: str = "") -> None:
        """
        Highlight target element with a 2px solid red border box before capturing failure screenshot.

        1. Clears any previous red borders across the page DOM.
        2. Identifies the failing element via passed locator, page._last_failed_locator,
           or locator pattern in error_message.
        3. Applies '2px solid red' border to the element.
        """
        try:
            if page is None or page.is_closed():
                return

            # 1. Clear previous borders
            try:
                page.evaluate("() => document.querySelectorAll('*').forEach(el => { el.style.border = ''; })")
            except Exception:
                pass

            target = None
            # 2. Determine target locator
            if locator is not None:
                target = locator if hasattr(locator, "first") else page.locator(str(locator))
            elif getattr(page, "_last_failed_locator", None) is not None:
                target = page._last_failed_locator
            elif error_message:
                m = re.search(r'(?:locator|selector)\(["\']([^"\']+)["\']\)', str(error_message))
                if m:
                    target = page.locator(m.group(1))

            # 3. Apply 2px solid red border if target element exists
            if target is not None:
                try:
                    if target.count() > 0:
                        target.first.evaluate("el => { el.style.border = '2px solid red'; }")
                except Exception:
                    pass
        except Exception:
            logger.debug("Element highlight failed; continuing with screenshot", exc_info=True)

    @classmethod
    def capture_failure(
        cls,
        page: Page | None,
        *,
        project: str,
        station: str,
        test_name: str,
        report_context=None,
        output_dir="reports/screenshots",
        error_message="",
        locator=None,
    ) -> str | None:
        """
        Capture a PNG screenshot with red border element highlighting.
        Used by pytest hooks and framework reporters. Returns saved path or None.
        """
        try:
            if page is None or page.is_closed():
                return None
            safe = lambda s: "".join(c if c.isalnum() or c in "._-" else "_" for c in str(s))[:100]
            path = Path(output_dir) / safe(project) / safe(station) / f"{safe(test_name)}_{time.strftime('%Y%m%d_%H%M%S')}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            cls.highlight_element(page, locator=locator, error_message=error_message)
            data = page.screenshot(path=str(path), full_page=True, animations="disabled")
            if report_context is not None:
                report_context.attach_screenshot(data, path.name, error_message, "image/png")
            logger.error("Failure screenshot captured | path=%s | url=%s", path, getattr(page, "url", "unknown"))
            return str(path)
        except Exception:
            logger.exception("Failure screenshot capture failed; preserving original test failure.")
            return None

    def highlight_failed_element(self, locator=None, error_message=""):
        """Instance method: marks failed element with red border."""
        self.highlight_element(self.page, locator=locator, error_message=error_message)

    def capture_failure_screenshot(self, locator=None, flight_name="Failure", error_message=""):
        """Instance method for page objects: marks failed element with red border and saves screenshot."""
        try:
            if self.page.is_closed():
                return None
            self.highlight_failed_element(locator=locator, error_message=error_message)
            from utils import report_context

            data = self.page.screenshot(full_page=True, animations="disabled")
            report_context.attach_screenshot(data, f"{flight_name} Failure Screenshot", error_message, "image/png")
            try:
                import allure

                allure.attach(data, name=f"{flight_name} Failure Screenshot", attachment_type=allure.attachment_type.PNG)
                if error_message:
                    allure.attach(error_message, name=f"{flight_name} Error", attachment_type=allure.attachment_type.TEXT)
            except Exception:
                logger.debug("Allure screenshot attachment unavailable", exc_info=True)
            return data
        except Exception:
            logger.exception("Unable to capture failure screenshot | url=%s", getattr(self.page, "url", "unknown"))
            return None
