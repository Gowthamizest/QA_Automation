
import re
import pytest
import allure

from playwright.sync_api import Page, expect, TimeoutError
from pages.base_page import BasePage
from utils.logger import get_logger

logger = get_logger(__name__)

class Listview_DepartedSection_AccesstoAIMedia(BasePage):

    # ==================== LOCATORS ====================

    MENU = "//span[@class='nav-icon']/i[normalize-space()='menu']"

    FLIGHTS = (
        "//div[@role='button' and contains(@class,'nav-row')]"
        "[.//span[normalize-space()='Flights']]"
    )

    DEPARTED_TAB = "text=Departed"
    FLIGHT_DETAILS = ".flight-details.ng-star-inserted"

    TURNAROUND_HEADER = ".turnaround-header"
    SPLIT_HEADER = "mat-expansion-panel-header.split-expansion-header"

    FLIGHT_EXPANSION_HEADERS = (
        ".turnaround-header, "
        "mat-expansion-panel-header.split-expansion-header"
    )

    PROGRESS_NUMERATOR = 'p[style="float: left;"]'

    DETAIL_ROWS = (
        ".row-white-background.ng-star-inserted, "
        ".row-colored-background.ng-star-inserted"
    )

    MAT_ACCORDION = "mat-accordion"
    MAT_PANEL = "mat-expansion-panel"
    PANEL_HEADER = "mat-expansion-panel-header"

    ACTIVITY_NAMES = [
        "Arrival Activities",
        "Departure Activities",
        "Additional Activities",
    ]

    # Keep this only if it matches the actual image elements in your app.
    IMAGE_ELEMENTS = ".image-class.ng-star-inserted"

    POPUP_PLAYER = "#player"
    CLOSE_BUTTON = 'text="×"'

    # ==================== CONSTRUCTOR ====================

    def __init__(self, page: Page):
        super().__init__(page)
        self.page = page

    # ==================== SCREENSHOT ====================

    def attach_screenshot(self, name: str, full_page: bool = True):
        try:
            screenshot = self.page.screenshot(full_page=full_page)

            allure.attach(
                screenshot,
                name=name,
                attachment_type=allure.attachment_type.PNG
            )

            logger.info(f"Screenshot attached: {name}")

        except Exception as e:
            logger.warning(
                f"Failed to attach screenshot {name}: {e}"
            )

    # ==================== LOADING ====================

    def wait_for_loading_to_finish(self, timeout: int = 15000):
        try:
            for selector in [
                ".loading",
                ".spinner",
                ".mat-progress-spinner",
            ]:
                spinners = self.page.locator(selector)

                for index in range(spinners.count()):
                    spinner = spinners.nth(index)

                    if spinner.is_visible():
                        expect(spinner).not_to_be_visible(
                            timeout=timeout
                        )

            logger.info("Loading completed successfully")

        except TimeoutError:
            self.attach_screenshot("spinner_timeout")
            pytest.fail(
                "Loading spinner did not disappear within timeout"
            )

    # ==================== NAVIGATION ====================

    @allure.step("Navigate to Flights List View")
    def navigate_to_list_view_page(self):
        try:
            logger.info("Navigating to Flights List View")

            menu = self.page.locator(self.MENU)
            expect(menu).to_be_visible(timeout=15000)
            menu.hover()

            flights = self.page.locator(self.FLIGHTS)

            if not flights.is_visible():
                menu.click()

            expect(flights).to_be_visible(timeout=15000)
            flights.click()

            self.page.wait_for_load_state(
                "networkidle",
                timeout=90000
            )

            self.page.wait_for_selector(
                '[mattooltip="Flight Arrival Departure Numbers"]',
                timeout=90000
            )

            expect(
                self.page.locator(self.DEPARTED_TAB)
            ).to_be_visible(timeout=90000)

            logger.info("List View loaded successfully")

        except Exception as e:
            self.attach_screenshot("list_view_load_failed")
            logger.error(f"Failed to open List View: {e}")
            raise

    # ==================== DEPARTED TAB ====================

    @allure.step("Select Departed Flights")
    def select_departed_flights(self):
        try:
            departed = self.page.locator(self.DEPARTED_TAB)

            expect(departed).to_be_visible(timeout=15000)
            departed.click()

            expect(
                self.page.locator(self.FLIGHT_DETAILS).first
            ).to_be_visible(timeout=15000)

            logger.info("Departed Flights selected successfully")

        except Exception as e:
            self.attach_screenshot("departed_tab_failed")
            logger.error(f"Failed to select Departed tab: {e}")
            raise

    # ==================== FLIGHT TYPE ====================

    def detect_flight_type(self):
        turnaround = self.page.locator(self.TURNAROUND_HEADER)
        split = self.page.locator(self.SPLIT_HEADER)

        if turnaround.count() and turnaround.first.is_visible():
            return "turnaround"

        if split.count() and split.first.is_visible():
            return "split"

        return None

    def wait_for_flight_header(self, timeout: int = 90000):
        headers = self.page.locator(
            self.FLIGHT_EXPANSION_HEADERS
        )

        expect(headers.first).to_be_visible(timeout=timeout)

        flight_type = self.detect_flight_type()

        if flight_type is None:
            raise AssertionError(
                "Could not identify Turnaround or Split flight"
            )

        logger.info(f"Flight type detected: {flight_type}")
        return flight_type

    # ==================== PROGRESS VALIDATION ====================

    @allure.step("Validate progress numerator")
    def check_progress_numerator_not_zero(self):
        elements = self.page.locator(self.PROGRESS_NUMERATOR)

        expect(elements.first).to_be_visible(timeout=15000)

        values = []

        for i in range(elements.count()):
            element = elements.nth(i)

            if not element.is_visible():
                continue

            value_text = element.inner_text().strip()
            logger.info(f"Progress {i + 1}: {value_text}")

            match = re.search(r"^\s*(\d+)\s*/\s*\d+", value_text)

            if match:
                values.append(int(match.group(1)))

        if not values:
            pytest.fail("No valid progress numerator found")

        if not any(value > 0 for value in values):
            pytest.fail(
                f"All progress numerators are zero: {values}"
            )

        logger.info(f"Progress validation passed: {values}")

    # ==================== ALL DEPARTED FLIGHTS ====================

    @allure.step("Check all departed flights")
    def check_all_departed_flights(self):
        try:
            flights = self.page.locator(self.FLIGHT_DETAILS)

            expect(flights.first).to_be_visible(timeout=15000)
            total = flights.count()

            if total == 0:
                pytest.fail("No departed flights found")

            logger.info(f"Total departed flights: {total}")

            for i in range(total):
                logger.info(f"Checking flight {i + 1}/{total}")

                flights = self.page.locator(self.FLIGHT_DETAILS)
                flight = flights.nth(i)

                expect(flight).to_be_visible(timeout=15000)
                flight.scroll_into_view_if_needed()
                flight.click(timeout=15000)

                flight_type = self.wait_for_flight_header(
                    timeout=90000
                )

                logger.info(
                    f"Flight {i + 1} type: {flight_type}"
                )

                self.wait_for_loading_to_finish()
                self.check_progress_numerator_not_zero()

                if flight_type == "split":
                    self.check_split_flight_activity_media(
                        flight_number=i + 1
                    )
                else:
                    self.check_turnaround_detail_media(
                        flight_number=i + 1
                    )

                logger.info(f"Flight {i + 1} validation completed")

            logger.info("All departed flights processed")

        except Exception as e:
            self.attach_screenshot("all_departed_flights_failed")
            logger.error(f"Departed flight validation failed: {e}")
            raise

    # ==================== TURNAROUND MEDIA ====================

    @allure.step("Check Turnaround flight details and AI media")
    def check_turnaround_detail_media(self, flight_number=1):
        rows = self.page.locator(self.DETAIL_ROWS)

        if rows.count() == 0:
            pytest.fail(
                f"Flight {flight_number}: no detail rows found"
            )

        for i in range(rows.count()):
            off_block = rows.nth(i).get_by_text(
                "Off Block",
                exact=True
            )

            if off_block.count() and off_block.first.is_visible():
                logger.info(
                    f"Flight {flight_number}: Off Block found"
                )

        images = self.page.locator(self.IMAGE_ELEMENTS)
        self.process_ai_media(
            images,
            flight_number,
            "Turnaround"
        )

    # ==================== SPLIT FLIGHT ACTIVITY PANELS ====================

    @allure.step("Expand Split flight activity dropdowns and check AI media")
    def check_split_flight_activity_media(self, flight_number=1):
        accordion = self.page.locator(self.MAT_ACCORDION)

        expect(accordion.first).to_be_visible(timeout=15000)

        found_panels = 0
        processed_panels = 0

        for activity_name in self.ACTIVITY_NAMES:
            # Match the panel by its visible heading.
            panels = accordion.locator(self.MAT_PANEL).filter(
                has=accordion.locator(self.PANEL_HEADER).filter(
                    has_text=activity_name
                )
            )

            if panels.count() == 0:
                all_panels = accordion.locator(self.MAT_PANEL)
                matching = []

                for j in range(all_panels.count()):
                    candidate = all_panels.nth(j)
                    header = candidate.locator(self.PANEL_HEADER)

                    if (
                        header.count()
                        and activity_name in header.first.inner_text()
                    ):
                        matching.append(j)

                if not matching:
                    logger.warning(
                        f"Flight {flight_number}: "
                        f"{activity_name} panel not found"
                    )
                    continue

                panel_indexes = matching
            else:
                panel_indexes = list(range(panels.count()))

            for panel_index in panel_indexes:
                if panels.count() > 0:
                    panel = panels.nth(panel_index)
                else:
                    panel = accordion.locator(
                        self.MAT_PANEL
                    ).nth(panel_index)

                header = panel.locator(self.PANEL_HEADER)

                if header.count() == 0:
                    continue

                found_panels += 1

                expanded = header.first.get_attribute(
                    "aria-expanded"
                )

                if expanded != "true":
                    header.first.scroll_into_view_if_needed()
                    header.first.click()

                    expect(
                        header.first
                    ).to_have_attribute(
                        "aria-expanded",
                        "true",
                        timeout=15000
                    )

                logger.info(
                    f"Flight {flight_number}: "
                    f"{activity_name} expanded"
                )

                expect(
                    panel.locator(".mat-expansion-panel-body")
                ).to_be_visible(timeout=10000)

                images = panel.locator(self.IMAGE_ELEMENTS)

                self.page.wait_for_timeout(500)

                image_count = images.count()

                logger.info(
                    f"Flight {flight_number}: {activity_name} "
                    f"contains {image_count} matching AI media elements"
                )

                if image_count > 0:
                    processed = self.process_ai_media(
                        images,
                        flight_number,
                        activity_name
                    )

                    if processed > 0:
                        processed_panels += 1

        if found_panels == 0:
            self.attach_screenshot(
                f"flight_{flight_number}_activity_panels_missing"
            )
            pytest.fail(
                f"Flight {flight_number}: none of the expected "
                "activity panels were found in mat-accordion"
            )

        if processed_panels == 0:
            self.attach_screenshot(
                f"flight_{flight_number}_split_media_missing"
            )
            pytest.fail(
                f"Flight {flight_number}: activity panels were found, "
                "but no AI media popup was processed. Verify the "
                "image selector and actual panel HTML."
            )

        logger.info(
            f"Flight {flight_number}: Split activity media validated"
        )

    # ==================== COMMON AI MEDIA PROCESSING ====================

    def process_ai_media(
        self,
        images,
        flight_number,
        activity_name
    ):
        processed = 0

        image_count = images.count()

        logger.info(
            f"Flight {flight_number} / {activity_name}: "
            f"{image_count} media elements found"
        )

        for i in range(image_count):
            image = images.nth(i)

            try:
                if not image.is_visible():
                    logger.info(
                        f"Media {i + 1} is hidden; skipping"
                    )
                    continue

                image.scroll_into_view_if_needed()
                image.click(timeout=15000)

                self.page.wait_for_selector(
                    self.POPUP_PLAYER,
                    state="visible",
                    timeout=30000
                )

                self.attach_screenshot(
                    f"flight_{flight_number}_"
                    f"{activity_name.replace(' ', '_')}_"
                    f"ai_media_{i + 1}"
                )

                self.close_popup()
                processed += 1

                logger.info(
                    f"Flight {flight_number} / {activity_name}: "
                    f"media {i + 1} checked successfully"
                )

            except Exception as e:
                self.attach_screenshot(
                    f"flight_{flight_number}_media_failed_{i + 1}"
                )
                logger.error(
                    f"AI media {i + 1} failed: {e}"
                )
                raise

        return processed

    # ==================== CLOSE AI MEDIA POPUP ====================

    @allure.step("Close AI captured media popup")
    def close_popup(self):
        player = self.page.locator(self.POPUP_PLAYER)
        expect(player).to_be_visible(timeout=20000)

        close_button = self.page.locator(self.CLOSE_BUTTON)
        expect(close_button.first).to_be_visible(timeout=10000)
        close_button.first.click()

        self.page.wait_for_selector(
            self.POPUP_PLAYER,
            state="detached",
            timeout=15000
        )

        logger.info("AI media popup closed successfully")
