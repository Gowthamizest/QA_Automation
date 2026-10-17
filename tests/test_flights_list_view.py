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

            



        



