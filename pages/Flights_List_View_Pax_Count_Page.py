import time
import re
import pytest
import allure
from playwright.sync_api import expect
from pages.Base_Page import BasePage
from utils.logger import get_logger

logger = get_logger(__name__)

class PAX_Count_Page(BasePage):

    MENU = "//span[@class='nav-icon']/i[text()='menu']"
    LIST_VIEW = "//div[@role='button']/span[text()='Flights']"

    SECTIONS = [
        {"name": "Ongoing", "tab": "//div[contains(text(),'Ongoing')]"},
        {"name": "Incoming", "tab": "//div[contains(text(),'Incoming')]"},
        {"name": "Departed", "tab": "//div[contains(text(),'Departed')]"}
    ]

    ARRIVAL_AND_DEPARTURE_NUMBER = "//p[@mattooltip='Flight Arrival Departure Numbers']"
    ARRIVAL_AND_DEPARTURE_PAX = "//div[contains(@class,'pax_count-col')]/div[@class='dropdown']/div[@class='dropbtn']"
    PAX_COUNT_POPUP = "//div[contains(@class,'pax_count-col')]/div[@class='dropdown']/div[@class='dropdown-content']"
    NO_FLIGHTS_AVAILABLE = "//div[contains(text(),'No Flights Available')]"
    FLIGHTS_CARDS = "//mat-card[contains(@class,'listviewmatcard')]/div"

    def navigate_to_dashboard(self):
        
        logger.info("Navigating to List View")
        
        # Checking Menu
        self.page.wait_for_timeout(3000)
        menu = self.page.locator(self.MENU)
        expect(menu).to_be_visible()
        
        # Hover on menu
        menu.hover()
        self.page.wait_for_timeout(1000)
        
        # Trying to Navigate to List View
        list_view = self.page.locator(self.LIST_VIEW)
        
        # If Hover fails for List View
        if not list_view.is_visible():
            logger.warning("List View not displayed after Hover, Trying to Click")
            menu.click()
            self.page.wait_for_timeout(1000)
            
        expect(list_view).to_be_visible()
        
        #Clicking List View
        list_view.click()
        logger.info("Clicked List View")

    def flights_are_visible(self, section_name):

        with allure.step("Checking Flights are Visible in Dashboard"):
            #time.sleep(10)
            flights = self.page.locator("//mat-card[contains(@class,'listviewmatcard')]")
            expect(flights.first).to_be_visible()
            logger.info("Flights are Visible")
                    
            # Checking No Flights Message
            no_flights_msg = self.page.locator(self.NO_FLIGHTS_AVAILABLE)
            if no_flights_msg.is_visible():
                logger.error(f"No Flights Available in {section_name} Section")
                raise Exception(f"No Flights Available in {section_name} Section")
            logger.info("Flights are Visible")

    def arrival_and_departure_number(self, flights):

        try :
            with allure.step(f"Check Arrival and Departure Number"):
                arr_and_dep = flights.locator(self.ARRIVAL_AND_DEPARTURE_NUMBER)
                expect(arr_and_dep).to_be_visible()
                flight_number = arr_and_dep.inner_text().split('-')
                arrival_number = flight_number[0].strip()
                departure_number = flight_number[1].strip()
                logger.info(f"Arrival Number = {arrival_number} & Departure Number = {departure_number}")

            return arrival_number, departure_number
        
        except Exception as e :
            self.capture_failure_screenshot(
                locator = arr_and_dep,
                flight_name = "Arrival_Departure_Number",
                error_message = str(e)
            )
            raise

    def arrival_and_departure_pax(self, flights):

        try :
            with allure.step(f"Check Arrival and Departure PAX Count"):
                total_pax = flights.locator(self.ARRIVAL_AND_DEPARTURE_PAX)
                expect(total_pax).to_be_visible()
                pax_count = total_pax.inner_text().split("|")
                arrival_pax_count = pax_count[0].strip()
                departure_pax_count = pax_count[1].strip()
                logger.info(f"Arrival PAX Count = {arrival_pax_count} & Departure PAX Count = {departure_pax_count}")

            return arrival_pax_count, departure_pax_count, total_pax
        
        except Exception as e :
            self.capture_failure_screenshot(
                locator = total_pax,
                flight_name = "Arrival_Departure_PAX",
                error_message = str(e)
            )
            raise

    def validate_pax_count_from_segregation(self, flights, popup_text, arrival_pax_count, departure_pax_count):
        #logger.info(f"PAX Count Popup Text:\n{popup_text}")

        # Verify sections
        assert "Arrival" in popup_text, "Arrival section not found in popup"
        assert "Departure" in popup_text, "Departure section not found in popup"

        # Extract Arrival values
        arrival_match = re.search(
            r"Arrival\s*J:\s*(\d+)\s*Y:\s*(\d+)\s*Infant:\s*(\d+)",
            popup_text,
            re.DOTALL
        )

        # Extract Departure values
        departure_match = re.search(
            r"Departure\s*J:\s*(\d+)\s*Y:\s*(\d+)\s*Infant:\s*(\d+)",
            popup_text,
            re.DOTALL
        )

        if not arrival_match:
            pytest.fail("Arrival segregation values not found")

        if not departure_match:
            pytest.fail("Departure segregation values not found")

        arrival_j = int(arrival_match.group(1))
        arrival_y = int(arrival_match.group(2))
        arrival_infant = int(arrival_match.group(3))

        departure_j = int(departure_match.group(1))
        departure_y = int(departure_match.group(2))
        departure_infant = int(departure_match.group(3))

        logger.info(f"Arrival -> J:{arrival_j}, Y:{arrival_y}, Infant:{arrival_infant}")
        logger.info(f"Departure -> J:{departure_j}, Y:{departure_y}, Infant:{departure_infant}")

        # Calculate totals
        arrival_total = arrival_j + arrival_y
        departure_total = departure_j + departure_y

        logger.info(f"Calculated Arrival Total = {arrival_total}")
        logger.info(f"Calculated Departure Total = {departure_total}")

        # Compare against values already extracted from card
        assert int(arrival_total) == int(arrival_pax_count), (
            f"Arrival mismatch: Card={arrival_pax_count}, "
            f"Popup={arrival_total}"
        )

        assert int(departure_total) == int(departure_pax_count), (
            f"Departure mismatch: Card={departure_pax_count}, "
            f"Popup={departure_total}"
        )

        logger.info("Arrival and Departure PAX segregation validated successfully")

    def check_segregartion_of_pax(self,flights, arrival_pax_count, departure_pax_count):

        # Hovering on Pax Count to check segregation of Arrival and Departure PAX
        pax_count = flights.locator(self.ARRIVAL_AND_DEPARTURE_PAX)
        expect(pax_count).to_be_visible()
        pax_count.hover()
        #logger.info("Hovered on PAX Count")
        #self.page.wait_for_timeout(2000)

        pax_count_popup = flights.locator(self.PAX_COUNT_POPUP)
        expect(pax_count_popup).to_be_visible()
        #logger.info("PAX Count Popup is Visible")
        popup_text = pax_count_popup.inner_text().strip()
        #print(popup_text)
        #logger.info(f"PAX Count Popup Text: {popup_text}")

        self.validate_pax_count_from_segregation(flights, popup_text, arrival_pax_count, departure_pax_count)

        self.page.locator("body").hover()
        #self.page.wait_for_timeout(500)

    
    def count_of_flights(self):

        # Counting the Number of Flights
        ongoing_flights = self.page.locator(self.FLIGHTS_CARDS)
        expect(ongoing_flights.first).to_be_visible()
        number_of_flights = ongoing_flights.count()
        logger.info(f"Totally we have {number_of_flights} Flights")

        return number_of_flights



