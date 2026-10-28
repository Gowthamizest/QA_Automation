
import allure
import pytest

from playwright.sync_api import Page, expect, TimeoutError
from pages.base_page import BasePage
from utils.logger import get_logger

logger = get_logger(__name__)


class Listview_DepartedSection_FlightCard(BasePage):

    # ==================== LOCATORS ====================

    MENU = "//span[@class='nav-icon']/i[normalize-space()='menu']"

    FLIGHTS = (
        "//div[@role='button' and contains(@class,'nav-row')]"
        "[.//span[normalize-space()='Flights']]"
    )

    DEPARTED_TAB = "text=Departed"

    FLIGHT_DETAILS = ".flight-details.ng-star-inserted"

    FLIGHT_MENU_ICON = "//mat-icon[normalize-space()='more_vert']"

    FLIGHT_CARD_MENU = "Flight Card"

    # Confirm this selector against the actual Flight Card page.
    FLIGHT_CARD_CONTAINER = ".rh-form"

    SPINNER_SELECTORS = [
        ".loading",
        ".spinner",
        ".mat-progress-spinner",
    ]

    # ==================== CONSTRUCTOR ====================

    def __init__(self, page: Page):
        super().__init__(page)
        self.page = page
        self.report_tab = None

    # ==================== SCREENSHOT ====================

    def attach_screenshot(
        self,
        name: str,
        full_page: bool = True
    ):
        try:
            screenshot = self.page.screenshot(
                full_page=full_page
            )

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

    def wait_for_loading_to_finish(
        self,
        timeout: int = 90000
    ):
        try:
            for selector in self.SPINNER_SELECTORS:
                spinners = self.page.locator(selector)

                for index in range(spinners.count()):
                    spinner = spinners.nth(index)

                    if spinner.is_visible():
                        expect(
                            spinner
                        ).not_to_be_visible(
                            timeout=timeout
                        )

            logger.info("Loading completed successfully")

        except TimeoutError:
            self.attach_screenshot("spinner_timeout")
            pytest.fail(
                f"Loading spinner did not disappear "
                f"within {timeout} ms"
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

    # ==================== OPEN AND VALIDATE ONE FLIGHT CARD ====================

    @allure.step("Open and validate Flight Card {flight_number}")
    def open_and_validate_flight_card(
        self,
        flight,
        flight_number
    ):
        popup = None

        try:
            logger.info(
                f"Opening Flight Card for flight {flight_number}"
            )

            flight.scroll_into_view_if_needed()

            menu_icon = flight.locator(
                self.FLIGHT_MENU_ICON
            )

            expect(
                menu_icon
            ).to_be_visible(timeout=15000)

            with self.page.context.expect_page(
                timeout=90000
            ) as new_page_info:

                menu_icon.click()

                flight_card_menu = self.page.get_by_role(
                    "menuitem",
                    name=self.FLIGHT_CARD_MENU,
                    exact=True
                )

                expect(
                    flight_card_menu
                ).to_be_visible(timeout=15000)

                flight_card_menu.click()

            popup = new_page_info.value
            self.report_tab = popup

            popup.wait_for_load_state(
                "domcontentloaded",
                timeout=90000
            )

            card_container = popup.locator(
                self.FLIGHT_CARD_CONTAINER
            )

            expect(
                card_container
            ).to_be_visible(timeout=90000)

            logger.info(
                f"Flight Card {flight_number} validated successfully"
            )

            self.attach_screenshot(
                f"flight_card_{flight_number}_validated"
            )

            return True

        except Exception as e:
            self.attach_screenshot(
                f"flight_card_{flight_number}_failed"
            )

            logger.error(
                f"Flight Card {flight_number} validation failed: {e}"
            )

            raise

        finally:
            if popup is not None and not popup.is_closed():
                popup.close()
                logger.info(
                    f"Closed Flight Card tab for flight {flight_number}"
                )

    # ==================== CHECK ALL DEPARTED FLIGHTS ====================

    @allure.step("Validate Flight Cards for all departed flights")
    def check_all_departed_flight_cards(self):
        try:
            flights = self.page.locator(self.FLIGHT_DETAILS)

            expect(
                flights.first
            ).to_be_visible(timeout=15000)

            total_flights = flights.count()

            if total_flights == 0:
                pytest.fail("No departed flights found")

            logger.info(
                f"Total departed flights found: {total_flights}"
            )

            validated_flights = 0

            for index in range(total_flights):
                flight_number = index + 1

                logger.info(
                    f"Processing flight {flight_number}/{total_flights}"
                )

                # Re-query the locator in case the DOM has updated.
                current_flights = self.page.locator(
                    self.FLIGHT_DETAILS
                )

                if index >= current_flights.count():
                    pytest.fail(
                        f"Flight list changed while processing "
                        f"flight {flight_number}"
                    )

                flight = current_flights.nth(index)

                expect(
                    flight
                ).to_be_visible(timeout=15000)

                self.open_and_validate_flight_card(
                    flight,
                    flight_number
                )

                validated_flights += 1

                logger.info(
                    f"Flight {flight_number} completed: "
                    f"{validated_flights}/{total_flights}"
                )

            assert validated_flights == total_flights, (
                f"Expected {total_flights} validated flights, "
                f"but validated {validated_flights}"
            )

            logger.info(
                f"All {validated_flights} departed Flight Cards "
                "validated successfully"
            )

        except Exception as e:
            self.attach_screenshot(
                "all_departed_flight_cards_failed"
            )
            logger.error(
                f"Failed to validate all departed Flight Cards: {e}"
            )
            raise

    # ==================== SWITCH BACK TO MAIN TAB ====================

    @allure.step("Switch back to main List View")
    def switch_back_to_main_tab(self):
        try:
            if self.page.is_closed():
                pytest.fail("Main List View tab is closed")

            self.page.bring_to_front()

            logger.info(
                "Returned to the main List View tab"
            )

        except Exception as e:
            self.attach_screenshot(
                "failed_switch_back_to_main_tab"
            )
            logger.error(
                f"Failed to return to main List View: {e}"
            )
            raise

    # ==================== COMPLETE WORKFLOW ====================

    @allure.step("Validate Flight Cards for all departed flights")
    def validate_departed_flight_report(self):
        self.navigate_to_list_view_page()
        self.select_departed_flights()
        self.check_all_departed_flight_cards()
        self.switch_back_to_main_tab()
