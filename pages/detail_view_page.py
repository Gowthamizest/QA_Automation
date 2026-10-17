import pytest
from pages.base_page import BasePage
from utils.logger import get_logger
from playwright.sync_api import expect
import allure
import time

logger = get_logger(__name__)

class DetailViewPage(BasePage):

    MENU = "//span[@class='nav-icon']/i[text()='menu']"
    LIST_VIEW = "//div[@role='button']/span[text()='Flights']"

    SECTIONS = [
        {"name": "Ongoing", "tab": "//div[contains(text(),'Ongoing')]"},
        {"name": "Departed", "tab": "//div[contains(text(),'Departed')]"}
    ]

    FLIGHTS_CARDS = "//mat-card[contains(@class,'listviewmatcard')]/div"
    DETAIL_VIEW_ARROW = "//div[contains(@class,'moreInfoStyles')]/mat-icon[text()='arrow_forward']"
    ARRIVAL_FLIGHT_NUMBER = "//div[@class='flight-names']/div[@class='flight-arrival']//div[@class='arr-dep']"
    DEPARTURE_FLIGHT_NUMBER = "//div[@class='flight-names']/div[@class='flight-departure']//div[@class='arr-dep']"
    ORIGIN_AIRPORT_CODE = "//div[@class='flight-names']/div[@class='flight-arrival']//div[@class='src-des']"
    DESTINATION_AIRPORT_CODE = "//div[@class='flight-names']/div[@class='flight-departure']//div[@class='src-des']"
    AIRCRAFT_AND_REGISTRATION_NUMBER = "//div[contains(@class,'h-50')]/span[@class='flight-details-value'][1]"
    TURNAROUND_STATUS = "//div[contains(@class,'gap-2')]/span[@class='flight-details-value']"
    GROUND_TIME = "//div[contains(@class,'gap-2')]/span[contains(@class,'ng-star-inserted')]"
    BAY_NUMBER = "//div[contains(@class,'thirdrow')]//span[@class='flight-details-value'][2]"
    GATE_NUMBER = "//div[contains(@class,'thirdrow')]//span[@class='flight-details-value'][3]"
    STA = "//div[contains(@class,'flight-details-title') and text()='STA']/..//div[@class='flight-details-value']"
    ETA = "//div[contains(@class,'flight-details-title') and text()='ETA']/..//div[@class='flight-details-value']"
    ONB = "//div[contains(@class,'flight-details-title') and text()='ONB']/..//div[@class='flight-details-value']"
    STD = "//div[contains(@class,'flight-details-title') and text()='STD']/..//div[@class='flight-details-value']"
    ETD = "//div[contains(@class,'flight-details-title') and text()='ETD']/..//div[@class='flight-details-value']"

    DETAIL_VIEW_BACK_ARROW = "//div[@class='back-arrow']"

    def navigate_to_list_view_page(self):

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

    def load_all_flights(self):
        logger.info("Loading All Flights")
        previous_count = 0
        same_count_retry = 0
        while True:

            ongoing_flights = self.page.locator("//mat-card[@id='cardviewid']/div")
            current_count = ongoing_flights.count()

            #logger.info(f"Currently Loaded Flights: {current_count}")

            # Stop when all flights are loaded
            if current_count == previous_count:
                same_count_retry += 1
            else:
                same_count_retry = 0

            # Stop only after multiple retries
            if same_count_retry >= 3:
                break

            previous_count = current_count

            # Scroll to Bottom
            flights_container = self.page.locator("#cardviewid").last
            flights_container.evaluate("(element) => element.scrollTop = element.scrollHeight")
            self.page.wait_for_timeout(3000)

        logger.info("All Flights Loaded")

    def arrival_and_departure_flight_number(self):

        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(3000)
        try :
            # Check Arrival Number of Flight is Displayed
            with allure.step("Checking Arrival Flight Number is Displayed"):
                arrival_flight_number = self.page.locator(self.ARRIVAL_FLIGHT_NUMBER)
                arrival_flight_number.wait_for(state="visible", timeout=10000)
                arrival_flight = arrival_flight_number.inner_text().strip()
                expect(arrival_flight_number).to_be_visible()
                logger.info(f"Arrival Flight Number is Visible & Arrival Flight Number is {arrival_flight}")

            # Check Departure Number of Flight is Displayed
            with allure.step("Checking Departure Flight Number is Displayed"):
                departure_flight_number = self.page.locator(self.DEPARTURE_FLIGHT_NUMBER)
                departure_flight = departure_flight_number.inner_text().strip()
                if departure_flight == "":
                    logger.warning("Departure Flight Number is Not Displayed")
                logger.info(f"Departure Flight Number is {departure_flight}")

            return arrival_flight, departure_flight

        except Exception as e:
            self.capture_failure_screenshot(
                locator = arrival_flight_number,
                flight_name = "Arrival_Departure_Validation",
                error_message = str(e)
            )
            raise

    def origin_and_destination(self):

        try :
            # Check Origin of the flight is Displayed
            with allure.step("Checking Origin of the Flight is Displayed"):
                origin_airport_code = self.page.locator(self.ORIGIN_AIRPORT_CODE)
                expect(origin_airport_code).not_to_have_text("")
                origin_airport = origin_airport_code.inner_text()
                logger.info(f"Arrival Airport Code is {origin_airport}")

            # Check Destination of the flight is Displayed
            with allure.step("Checking Destination of Flight is Displayed"):
                destination_airport_code = self.page.locator(self.DESTINATION_AIRPORT_CODE)
                destination_airport = destination_airport_code.inner_text().strip()
                if destination_airport == "":
                    logger.warning("Destination Airport Code is Not Displayed")
                logger.info(f"Destination Airport Code is {destination_airport}")

        except Exception as e:
            self.capture_failure_screenshot(
                locator = origin_airport_code,
                flight_name = "Arrival_Departure_Validation",
                error_message = str(e)
            )
            raise

    def is_lock_icon_visible(self, flight_locator):
        """
        Returns True if lock icon is visible inside a flight card
        """
        try:
            lock_icon = flight_locator.locator("//div[@role='button']/div[contains(@class,'lock-icon')]")
            return lock_icon.count() > 0 and lock_icon.first.is_visible()
        except Exception:
            return False

    def aircraft_type_and_reg_number(self):

        try :
            # Check Aircraft Type and Registration Number is Displayed
            with allure.step("Checking Aircraft Type and Registration Number is Displayed"):
                aircraft_and_registration_number = self.page.locator(self.AIRCRAFT_AND_REGISTRATION_NUMBER)
                aircrft_reg_no = aircraft_and_registration_number.inner_text()
                aircraft_and_registration = aircrft_reg_no.split()
                aircraft_number = aircraft_and_registration[0]
                if aircraft_number in ["null","-",""]:
                    raise Exception ("Aircraft Type is not Displayed")
                registration_number = aircraft_and_registration[1]
                logger.info(f"Displayed Aircraft Number is {aircraft_number}")
                logger.info(f"Displayed Registration Number is {registration_number}")

        except Exception as e:
            self.capture_failure_screenshot(
                locator= aircraft_and_registration_number,
                flight_name="Arrival_Departure_Validation",
                error_message=str(e)
            )
            raise


    def flight_arrival_timing(self):

        try :
            # Check STA of Flight is Displayed
            with allure.step("Checking STA is mentioned"):
                sta_time = self.page.locator(self.STA)
                expect(sta_time).not_to_have_text('-')
                sta_time_value = sta_time.inner_text()
                logger.info(f"Mentioned STA Time is {sta_time_value}")

            # Check ETA of Flight is Displayed
            with allure.step("Checking ETA is mentioned"):
                eta_time = self.page.locator(self.ETA)
                eta_time_value = eta_time.inner_text()
                if eta_time_value == "-":
                    logger.warning("ETA Time is not Displayed")
                logger.info(f"Mentioned ETA Time is {eta_time_value}")

        except Exception as e:
            self.capture_failure_screenshot(
                locator=sta_time,
                flight_name="Arrival_Departure_Validation",
                error_message=str(e)
            )
            raise

    def on_block_timing(self):

        try:
            # Check ONB of Flight is Displayed
            with allure.step("Checking ONB is mentioned"):
                onb_time = self.page.locator(self.ONB)
                expect(onb_time).not_to_have_text('-')
                onb_time_value = onb_time.inner_text()
                logger.info(f"Mentioned ONB Time is {onb_time_value}")

        except Exception as e:
            self.capture_failure_screenshot(
                locator = onb_time,
                flight_name = "Arrival_Departure_Validation",
                error_message = str(e)
            )
            raise

    def flight_departure_timing(self):

            # Check STD of Flight is Displayed
            with allure.step("Checking STD is mentioned"):
                std_time = self.page.locator(self.STD)
                std_time_value = std_time.inner_text()
                if std_time_value == "-":
                    logger.warning("STD Time is not Displayed")
                logger.info(f"Mentioned STD Time is {std_time_value}")

            # Check ETD of Flight is Displayed
            with allure.step("Checking ETD is mentioned"):
                etd_time = self.page.locator(self.ETD)
                etd_time_value = etd_time.inner_text()
                if etd_time_value == "-":
                    logger.warning("ETD Time is not Displayed")
                logger.info(f"Mentioned ETD Time is {etd_time_value}")


    def bay_and_gate_number(self):

            # Check Bay for Flight
            with allure.step("Checking the Bay is Displayed"):
                bay_number = self.page.locator(self.BAY_NUMBER)
                bay_number_text = bay_number.inner_text()
                if bay_number_text == "-":
                    logger.warning("Bay Number is not Displayed")
                logger.info(f"Displayed Bay Number is {bay_number_text}")

            # Check Gate for Flight
            with allure.step("Checking Gate Number is Displayed"):
                gate_number = self.page.locator(self.GATE_NUMBER)
                gate_number_text = gate_number.inner_text()
                if gate_number_text == "-":
                    logger.warning("Gate Number is not Displayed")
                logger.info(f"Displayed Gate Number is {gate_number_text}")


    def turnaround_status_and_ground_time(self):

        try :
            # Check Flight Turnaround Status and Ground Time
            with allure.step("Check Flight Turnaround Status and Ground Time"):
                turnaround_status = self.page.locator(self.TURNAROUND_STATUS)
                expect(turnaround_status).not_to_have_text('-')
                turnaround_status_text = turnaround_status.inner_text()
                logger.info(f"Displayed Turnaround Status is {turnaround_status_text}")

            with allure.step("Checking Ground Time is Displayed"):
                ground_time = self.page.locator(self.GROUND_TIME)
                expect(ground_time).not_to_have_text('-')
                ground_time_text = ground_time.inner_text()
                logger.info(f"Displayed Ground Time is {ground_time_text}")

        except Exception as e:
            self.capture_failure_screenshot(
                locator = turnaround_status,
                flight_name = "Arrival_Departure_Validation",
                error_message = str(e)
            )
            raise

    def flight_are_visible(self):
        # Checking Flights are Visible
        with allure.step("Checking Flights are Visible in Dashboard"):
            #time.sleep(10)
            flights = self.page.locator("//mat-card[contains(@class,'listviewmatcard')]")
            expect(flights.first).to_be_visible()
            logger.info("Flights are Visible")

    def count_of_flights(self):
        # Counting the Number of Flights
        ongoing_flights = self.page.locator(self.FLIGHTS_CARDS)
        expect(ongoing_flights.first).to_be_visible()
        number_of_flights = ongoing_flights.count()
        logger.info(f"Totally we have {number_of_flights} Flights")

        return number_of_flights
















