import re
from pathlib import Path
from playwright.sync_api import Locator, Page, expect
from utils.logger import get_logger

logger = get_logger(__name__)


class BasePage:
    def __init__(self, page: Page, base_url=None):
        self.page = page
        self.base_url = base_url

    # =====================================================================
    # Helpers (used only inside this class)
    # =====================================================================

    # Accepts a selector string or a locator and always returns a locator
    def _get_locator(self, target):
        if isinstance(target, Locator):
            return target
        return self.page.locator(target)

    # Runs one element action and writes start / success / failure lines to the log
    def _perform_action_with_log(self, action, target, fn, *args, **kwargs):
        loc = self._get_locator(target)
        label = str(target)
        logger.info('ACTION start | %s | locator=%s', action, label)
        try:
            result = fn(loc, *args, **kwargs)
            logger.info('ACTION success | %s | locator=%s', action, label)
            return result
        except Exception:
            logger.exception('ACTION failed | %s | locator=%s | url=%s', action, label, self.page.url)
            raise

    # =====================================================================
    # Navigation
    # =====================================================================

    # Opens the application url (or the given url) and waits for the page to load
    def open_application(self, url=None):
        target = url or self.base_url
        if not target:
            raise ValueError('Application URL not found. Pass a URL to open_application() or configure project/environment URL.')
        logger.info('Navigating to application: %s', target)
        self.page.goto(target, wait_until='domcontentloaded')

    # Goes to the previous page in the browser history
    def go_back(self, **kwargs):
        return self.page.go_back(**kwargs)

    # Goes to the next page in the browser history
    def go_forward(self, **kwargs):
        return self.page.go_forward(**kwargs)

    # Refreshes the current page
    def reload_page(self, **kwargs):
        return self.page.reload(**kwargs)

    # =====================================================================
    # Finding elements (these only find, they do not click or read anything)
    # =====================================================================

    # Finds element(s) using a css / xpath selector
    def find_element(self, selector):
        return self.page.locator(selector)

    # Finds an element by its role, e.g. find_by_role('button', name='Submit')
    def find_by_role(self, role, **kwargs):
        return self.page.get_by_role(role, **kwargs)

    # Finds an element by the text visible on it
    def find_by_text(self, text, **kwargs):
        return self.page.get_by_text(text, **kwargs)

    # Finds an input by the label written next to it
    def find_by_label(self, text, **kwargs):
        return self.page.get_by_label(text, **kwargs)

    # Finds an input by its placeholder text
    def find_by_placeholder(self, text, **kwargs):
        return self.page.get_by_placeholder(text, **kwargs)

    # Finds an element by its title attribute
    def find_by_title(self, text, **kwargs):
        return self.page.get_by_title(text, **kwargs)

    # Picks one element from a list of matches (0 = first, -1 = last)
    def get_nth_element(self, target, index):
        return self._get_locator(target).nth(index)

    # =====================================================================
    # Element actions
    # =====================================================================

    # Clicks on the element
    def click(self, locator, **kwargs):
        return self._perform_action_with_log('click', locator, lambda l: l.click(**kwargs))

    # Double clicks on the element
    def double_click(self, locator, **kwargs):
        return self._perform_action_with_log('double_click', locator, lambda l: l.dblclick(**kwargs))

    # Right clicks on the element
    def right_click(self, locator, **kwargs):
        return self._perform_action_with_log('right_click', locator, lambda l: l.click(button='right', **kwargs))

    # Moves the mouse over the element (for dropdown menus, tooltips, etc.)
    def hover_over(self, locator, **kwargs):
        return self._perform_action_with_log('hover_over', locator, lambda l: l.hover(**kwargs))

    # Drags the source element and drops it on the target element
    def drag_and_drop(self, source, target, **kwargs):
        return self._perform_action_with_log('drag_and_drop', source, lambda l: l.drag_to(self._get_locator(target), **kwargs))

    # Clears the field first (if it has text) and then enters the new text
    def send_text(self, locator, text, **kwargs):
        self.clear_text(locator)
        return self._perform_action_with_log('send_text', locator, lambda l: l.fill(str(text), **kwargs))

    # Removes any text present in the field
    def clear_text(self, locator):
        return self._perform_action_with_log('clear_text', locator, lambda l: l.clear())

    # Presses a keyboard key on the element, e.g. press_key('#search', 'Enter')
    def press_key(self, locator, key, **kwargs):
        return self._perform_action_with_log('press_key', locator, lambda l: l.press(key, **kwargs))

    # Ticks a checkbox or selects a radio button
    def tick_checkbox(self, locator, **kwargs):
        return self._perform_action_with_log('tick_checkbox', locator, lambda l: l.check(**kwargs))

    # Unticks a checkbox
    def untick_checkbox(self, locator, **kwargs):
        return self._perform_action_with_log('untick_checkbox', locator, lambda l: l.uncheck(**kwargs))

    # Chooses option(s) in a dropdown; pass one value or a list of values for a multi select
    def select_dropdown_option(self, locator, option, **kwargs):
        return self._perform_action_with_log('select_dropdown_option', locator, lambda l: l.select_option(option, **kwargs))

    # Uploads one or more files using a file input
    def upload_file(self, locator, files, **kwargs):
        return self._perform_action_with_log('upload_file', locator, lambda l: l.set_input_files(files, **kwargs))

    # Scrolls the page until the element is visible
    def scroll_to_element(self, locator, **kwargs):
        return self._perform_action_with_log('scroll_to_element', locator, lambda l: l.scroll_into_view_if_needed(**kwargs))

    # =====================================================================
    # Reading values (returns data, does not assert anything)
    # =====================================================================

    # Returns the text as it is shown on the screen
    def get_text(self, locator):
        return self._perform_action_with_log('get_text', locator, lambda l: l.inner_text())

    # Returns how many elements match
    def count_elements(self, locator):
        return self._get_locator(locator).count()

    # Returns True if at least one element matches
    def element_exists(self, locator):
        return self._get_locator(locator).count() > 0

    # Returns True if the element is visible on the screen
    def is_visible(self, locator):
        return self._get_locator(locator).is_visible()

    # Returns True if the element is hidden or not on the page
    def is_hidden(self, locator):
        return self._get_locator(locator).is_hidden()

    # Returns True if the element can be used (not disabled)
    def is_enabled(self, locator):
        return self._get_locator(locator).is_enabled()

    # Returns True if the element is disabled
    def is_disabled(self, locator):
        return self._get_locator(locator).is_disabled()

    # Returns True if the checkbox / radio button is ticked
    def is_checked(self, locator):
        return self._get_locator(locator).is_checked()

    # Returns True if the user can type in the element
    def is_editable(self, locator):
        return self._get_locator(locator).is_editable()

    # =====================================================================
    # Waits
    # =====================================================================

    # Waits until the page has loaded (state: domcontentloaded, load or networkidle)
    def wait_for_page_load(self, state='domcontentloaded', timeout=None):
        return self.page.wait_for_load_state(state, timeout=timeout)

    # Waits until the browser url matches
    def wait_for_url(self, url, timeout=None):
        return self.page.wait_for_url(url, timeout=timeout)

    # Waits until the element is in the given state (visible, hidden, attached or detached)
    def wait_for_element(self, target, state='visible', timeout=None):
        return self._get_locator(target).wait_for(state=state, timeout=timeout)

    # Waits until the given javascript expression becomes true
    def wait_for_condition(self, expression, timeout=None):
        return self.page.wait_for_function(expression, timeout=timeout)

    # Fixed wait in milliseconds, use only when there is no better option
    def hard_wait(self, milliseconds):
        return self.page.wait_for_timeout(milliseconds)

    # =====================================================================
    # Tabs and popups
    # =====================================================================

    # Runs the action (like a click) that opens a new tab and returns that new tab
    def get_new_tab(self, action):
        with self.page.context.expect_page() as page_info:
            action()
        return page_info.value

    # Runs the action that opens a popup window and returns that popup
    def get_popup_window(self, action):
        with self.page.expect_popup() as popup_info:
            action()
        return popup_info.value

    # Returns all the tabs that are currently open
    def get_all_tabs(self):
        return self.page.context.pages

    # Moves to a tab by its position (0 = first tab, -1 = last tab)
    def switch_to_tab(self, index):
        self.page = self.page.context.pages[index]
        self.page.bring_to_front()
        return self.page

    # Moves to the tab whose title contains the given text
    def switch_to_tab_by_title(self, title):
        for tab in self.page.context.pages:
            if title in tab.title():
                self.page = tab
                self.page.bring_to_front()
                return self.page
        raise Exception(f'No tab found with title containing: {title}')

    # Moves to the tab whose url contains the given text
    def switch_to_tab_by_url(self, url):
        for tab in self.page.context.pages:
            if url in tab.url:
                self.page = tab
                self.page.bring_to_front()
                return self.page
        raise Exception(f'No tab found with url containing: {url}')

    # Closes the current tab and moves to the last open tab
    def close_current_tab(self):
        self.page.close()
        tabs = self.page.context.pages
        if tabs:
            self.page = tabs[-1]
            self.page.bring_to_front()

    # =====================================================================
    # Alerts
    # =====================================================================

    # Runs the action that shows an alert, clicks OK / Accept and returns the alert message
    def accept_alert(self, action, prompt_text=None):
        messages = []

        def handler(dialog):
            messages.append(dialog.message)
            if prompt_text:
                dialog.accept(prompt_text)
            else:
                dialog.accept()

        self.page.once('dialog', handler)
        action()
        return messages[0] if messages else None

    # Runs the action that shows an alert, clicks Cancel / Dismiss and returns the alert message
    def dismiss_alert(self, action):
        messages = []

        def handler(dialog):
            messages.append(dialog.message)
            dialog.dismiss()

        self.page.once('dialog', handler)
        action()
        return messages[0] if messages else None

    # =====================================================================
    # Page content
    # =====================================================================

    # Returns the title of the current page
    def get_page_title(self):
        return self.page.title()

    # Returns the url of the current page
    def get_page_url(self):
        return self.page.url

    # =====================================================================
    # Assertions - element state
    # =====================================================================

    # Checks the element is visible
    def assert_element_visible(self, locator, timeout=None):
        expect(self._get_locator(locator)).to_be_visible(timeout=timeout)

    # Checks the element is hidden or not on the page
    def assert_element_hidden(self, locator, timeout=None):
        expect(self._get_locator(locator)).to_be_hidden(timeout=timeout)

    # Checks the element is enabled
    def assert_element_enabled(self, locator, timeout=None):
        expect(self._get_locator(locator)).to_be_enabled(timeout=timeout)

    # Checks the element is disabled
    def assert_element_disabled(self, locator, timeout=None):
        expect(self._get_locator(locator)).to_be_disabled(timeout=timeout)

    # Checks the user can type in the element
    def assert_element_editable(self, locator, timeout=None):
        expect(self._get_locator(locator)).to_be_editable(timeout=timeout)

    # Checks the checkbox / radio button is ticked
    def assert_element_checked(self, locator, timeout=None):
        expect(self._get_locator(locator)).to_be_checked(timeout=timeout)

    # Checks the checkbox is not ticked
    def assert_element_unchecked(self, locator, timeout=None):
        expect(self._get_locator(locator)).not_to_be_checked(timeout=timeout)

    # Checks the cursor is in the element
    def assert_element_focused(self, locator, timeout=None):
        expect(self._get_locator(locator)).to_be_focused(timeout=timeout)

    # Checks the element has no text / content inside
    def assert_element_empty(self, locator, timeout=None):
        expect(self._get_locator(locator)).to_be_empty(timeout=timeout)

    # Checks the element is present in the page source
    def assert_element_present(self, locator, timeout=None):
        try:
            self._get_locator(locator).wait_for(state='attached', timeout=timeout)
        except Exception as exc:
            raise AssertionError(f'Expected element to be present; locator={locator!s}; url={self.page.url}; cause={exc}') from exc

    # Checks the element is not present in the page source
    def assert_element_absent(self, locator, timeout=None):
        try:
            self._get_locator(locator).wait_for(state='detached', timeout=timeout)
        except Exception as exc:
            raise AssertionError(f'Expected element to be absent; locator={locator!s}; url={self.page.url}; cause={exc}') from exc

    # =====================================================================
    # Assertions - element content
    # =====================================================================

    # Checks the element text is exactly the expected text
    def assert_text_equals(self, locator, expected, timeout=None):
        try:
            expect(self._get_locator(locator)).to_have_text(expected, timeout=timeout)
        except AssertionError as exc:
            raise AssertionError(f'Text assertion failed; locator={locator!s}; expected={expected!r}; url={self.page.url}') from exc

    # Checks the element text contains the expected text
    def assert_text_contains(self, locator, expected, timeout=None):
        try:
            expect(self._get_locator(locator)).to_contain_text(expected, timeout=timeout)
        except AssertionError as exc:
            raise AssertionError(f'Text containment failed; locator={locator!s}; expected substring={expected!r}; url={self.page.url}') from exc

    # Checks the value typed in an input field
    def assert_field_value(self, locator, expected, timeout=None):
        try:
            expect(self._get_locator(locator)).to_have_value(expected, timeout=timeout)
        except AssertionError as exc:
            raise AssertionError(f'Value assertion failed; locator={locator!s}; expected={expected!r}; url={self.page.url}') from exc

    # Checks the selected options of a multi select dropdown (expected is a list)
    def assert_selected_options(self, locator, expected, timeout=None):
        expect(self._get_locator(locator)).to_have_values(expected, timeout=timeout)

    # Checks an attribute has the expected value, e.g. href, placeholder
    def assert_attribute_value(self, locator, name, expected, timeout=None):
        try:
            expect(self._get_locator(locator)).to_have_attribute(name, expected, timeout=timeout)
        except AssertionError as exc:
            raise AssertionError(f'Attribute assertion failed; locator={locator!s}; attribute={name!r}; expected={expected!r}; url={self.page.url}') from exc

    # Checks the css class of the element
    def assert_css_class(self, locator, expected, timeout=None):
        expect(self._get_locator(locator)).to_have_class(expected, timeout=timeout)

    # Checks the id of the element
    def assert_element_id(self, locator, expected, timeout=None):
        expect(self._get_locator(locator)).to_have_id(expected, timeout=timeout)

    # Checks a css style of the element, e.g. assert_css_style(loc, 'color', 'rgb(0, 0, 0)')
    def assert_css_style(self, locator, name, expected, timeout=None):
        expect(self._get_locator(locator)).to_have_css(name, expected, timeout=timeout)

    # Checks how many elements match
    def assert_element_count(self, locator, expected, timeout=None):
        try:
            expect(self._get_locator(locator)).to_have_count(expected, timeout=timeout)
        except AssertionError as exc:
            raise AssertionError(f'Count assertion failed; locator={locator!s}; expected={expected!r}; actual={self.count_elements(locator)}; url={self.page.url}') from exc

    # =====================================================================
    # Assertions - page
    # =====================================================================

    # Checks the page url (use contains=True to match only part of the url)

    def assert_page_url(self, expected, contains=False, timeout=None):
        pattern = re.compile(re.escape(expected)) if contains else expected
        try:
            expect(self.page).to_have_url(pattern, timeout=timeout)
        except AssertionError as exc:
            mode = 'to contain ' if contains else ''
            raise AssertionError(f'URL assertion failed; expected {mode}{expected!r}; actual={self.page.url!r}') from exc

    # Checks the page title (use contains=True to match only part of the title)

    def assert_page_title(self, expected, contains=False, timeout=None):
        pattern = re.compile(re.escape(expected)) if contains else expected
        try:
            expect(self.page).to_have_title(pattern, timeout=timeout)
        except AssertionError as exc:
            raise AssertionError(f'Page title assertion failed; expected {"to contain " if contains else ""}{expected!r}; actual={self.page.title()!r}; url={self.page.url}') from exc

    # =====================================================================
    # Screenshot
    # =====================================================================

        # Takes a full page screenshot on failure with a red border around the failed element and attaches it to the html and allure reports
    def capture_failure_screenshot(self, locator=None, flight_name='Failure', error_message=''):
        """Legacy-compatible screenshot helper; failures never replace the original test exception."""
        try:
            if self.page.is_closed(): return None
            if locator is not None:
                try:
                    # mark the failed element with a red border so it is easy to spot in the screenshot
                    self._get_locator(locator).first.evaluate("el => { el.style.border = '3px solid red'; }", timeout=3000)
                except Exception:
                    logger.debug('Could not mark the failed element with a red border', exc_info=True)
            from utils import report_context
            data=self.page.screenshot(full_page=True, animations='disabled')
            report_context.attach_screenshot(data, f'{flight_name} Failure Screenshot', error_message, 'image/png')
            try:
                import allure
                allure.attach(data,name=f'{flight_name} Failure Screenshot',attachment_type=allure.attachment_type.PNG)
                if error_message: allure.attach(error_message,name=f'{flight_name} Error',attachment_type=allure.attachment_type.TEXT)
            except Exception: logger.debug('Allure screenshot attachment unavailable',exc_info=True)
            return data
        except Exception:
            logger.exception('Unable to capture failure screenshot | url=%s', getattr(self.page,'url','unknown'))
            return None