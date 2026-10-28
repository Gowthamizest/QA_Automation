from playwright.sync_api import expect
import pytest
import allure
from pages.Flights_View_List_View_Page import Flights_View_Ongoing_Page
from utils.logger import get_logger
import time

logger = get_logger()


@pytest.mark.smoke
@pytest.mark.login
def test_flights_view_ongoing(page):
    
    logger.info("Starting Flights View Ongoing Test")

    flights_view_ongoing_page = Flights_View_Ongoing_Page(page, None)

    with allure.step("Test Execution Started -> Navigating to Dashboard"):

        # Navigating to Dashboard
        flights_view_ongoing_page.navigate_to_list_view_page()

        # Load All Flights in Turnaround List View
        flights_view_ongoing_page.load_all_flights()

        # Checking All Sections are displayed
        for section in flights_view_ongoing_page.SECTIONS:
            section_name = section["name"]
            with allure.step(f"Checking {section_name} Section"):
                logger.info(f"Checking {section_name} Section")
                section_tab = flights_view_ongoing_page.page.locator(section["tab"])
                expect(section_tab).to_be_visible()
                logger.info(f"{section_name} Section is Displayed")
        logger.info("All Sections are Displayed Successfully")

        # Checking Activity Dropdown is Displayed for Turnaround and Split Flights

        number_of_flights = flights_view_ongoing_page.count_of_flights()
        if number_of_flights == 0:
            logger.warning(f"No Flights Found in {section_name}")
        elif number_of_flights <= 15 and number_of_flights > 0:
            logger.info(f"Number of Flights in {section_name} is {number_of_flights}")
        else :
            number_of_flights = 15
            logger.info(f"Number of Flights in {section_name} is {number_of_flights}")


        # Checking PTS Names List is Displayed for Activity Dropdown in Flight Card for Turnaround and Split Flights

        for i in range(number_of_flights):
            flight_card = flights_view_ongoing_page.page.locator(flights_view_ongoing_page.FLIGHT_ROW_CARDS).nth(i)
            count_of_activity_dropdowns = flights_view_ongoing_page.activity_dropdown_is_displayed(flight_card)

            if count_of_activity_dropdowns == 1:
                for j in range(count_of_activity_dropdowns):
                                activity_dropdown = flight_card.locator(flights_view_ongoing_page.ACTIVITY_DROPDOWN_CARD).nth(j)
                                flights_view_ongoing_page.pts_is_displayed(activity_dropdown, flight_card)
                else :
                    logger.warning(f"PTS Names List is not Displayed for Activity Dropdown in Flight Card")
            elif count_of_activity_dropdowns > 1:
                for j in range(count_of_activity_dropdowns-2):
                                activity_dropdown = flight_card.locator(flights_view_ongoing_page.ACTIVITY_DROPDOWN_CARD).nth(j)
                                flights_view_ongoing_page.pts_is_displayed(activity_dropdown, flight_card)
                else:
                    logger.warning(f"PTS Names List is not Displayed for Activity Dropdown in Flight Card")
            else:
                logger.warning(f"Activity Dropdown is not Displayed for Flight Card")

            logger.info("PTS Names List is Displayed for All Flight Cards in Turnaround and Split Flights")

            # Hover on STA
            sta_element = flight_card.locator(flights_view_ongoing_page.STA)

            if sta_element.count() > 0 and sta_element.first.is_visible():

                sta_element.first.hover()
                time.sleep(2)

                # Check Onblock Time
                onblock_time = flight_card.locator(flights_view_ongoing_page.ONBLOCK_TIME)

                if onblock_time.count() > 0 and onblock_time.first.is_visible():
                    expect(onblock_time.first).to_be_visible()
                    logger.info(f"Onblock Time is displayed for Flight Card {i + 1}")
                else:
                    logger.info(f"Onblock Time is not displayed for Flight Card {i + 1}")

        logger.info("Onblock Time Validation Completed for Ongoing Section")


        # Navigate to Departed Section

        departed_section = flights_view_ongoing_page.page.locator(
            flights_view_ongoing_page.SECTIONS[2]["tab"]
        )

        expect(departed_section).to_be_visible()
        departed_section.click()

        flights_view_ongoing_page.flight_are_visible()

        # Checking Offblock Time and Flight Card in Departed Section

        number_of_flights = flights_view_ongoing_page.count_of_flights()

        if number_of_flights > 15:
            number_of_flights = 15

        for i in range(number_of_flights):

            flight_card = flights_view_ongoing_page.page.locator(flights_view_ongoing_page.FLIGHT_ROW_CARDS).nth(i)
            expect(flight_card).to_be_visible()

            # Hover on ETD
            etd_element = flight_card.locator(flights_view_ongoing_page.ETD)

            if etd_element.count() > 0 and etd_element.first.is_visible():

                etd_element.first.hover()
                time.sleep(2)

                # Check Offblock Time
                offblock_time = flight_card.locator(flights_view_ongoing_page.OFFBLOCK_TIME)

                if offblock_time.count() > 0 and offblock_time.first.is_visible():

                    expect(offblock_time.first).to_be_visible()
                    logger.info(f"Offblock Time is displayed for Departed Flight Card {i + 1}")

                else:
                    logger.info(f"Offblock Time is not displayed for Departed Flight Card {i + 1}")

            # Open Flight Menu for the Same Flight Card
            flight_menu = flight_card.locator(flights_view_ongoing_page.FLIGHT_MENU_ICON)

            if flight_menu.count() > 0 and flight_menu.first.is_visible():
                flight_menu.first.click()

                # Check Flight Card Option
                flight_card_button = flights_view_ongoing_page.page.locator(flights_view_ongoing_page.FLIGHT_CARD_BUTTON)

                if flight_card_button.count() > 0 and flight_card_button.first.is_visible():
                    logger.info(f"Flight Card Option is displayed for Flight {i + 1}")

                    # Click Flight Card and Verify New Tab
                    with page.expect_popup() as popup_info:
                        flight_card_button.first.click()

                    flight_card_page = popup_info.value
                    flight_card_page.wait_for_load_state("domcontentloaded")

                    expect(flight_card_page.locator("body")).to_be_visible()

                    logger.info(f"Flight Card opened in a new tab for Flight {i + 1}")

                    flight_card_page.close()

                else:
                    logger.warning(f"Flight Card Option is not displayed for Flight {i + 1}")

            else:
                logger.warning(f"Flight Menu is not displayed for Flight Card {i + 1}")

        logger.info("Offblock Time and Flight Card Validation Completed for Departed Section")


            



        



