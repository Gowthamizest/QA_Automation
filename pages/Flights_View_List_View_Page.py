import pytest
from pages.Base_Page import BasePage
from utils.logger import get_logger
from playwright.sync_api import expect
import allure
import time

logger = get_logger(__name__)


class Flights_View_Ongoing_Page(BasePage):
        
    MENU = "//span[@class='nav-icon']/i[text()='menu']"
    LIST_VIEW = "//div[@role='button']/span[text()='Flights']"

    SECTIONS = [
        {"name": "Ongoing", "tab": "//div[contains(text(),'Ongoing')]"},
        {"name": "Incoming", "tab": "//div[contains(text(),'Incoming')]"},
        {"name": "Departed", "tab": "//div[contains(text(),'Departed')]"},
        {"name": "Non Operational", "tab": "//div[contains(text(),'Non Operational')]"}
    ]

    # Common Locators for Flights View List View Page

    
    SEARCH_INPUT = "//div[contains(@class,'search_form')]//input[@name='query']" # NA For NOP Section
    SEARCH_BUTTON = "//div[@class='ng-star-inserted']//i[@ptooltip='Search']"
    FLIGHT_ROW_CARDS = "//mat-card[contains(@class,'listviewmatcard')]/div"
    NO_FLIGHTS_AVAILABLE = "//div[contains(text(),'No Flights Available')]"
    ARRIVAL_AND_DEPARTURE_FLIGHT_NUMBER = "//p[@mattooltip='Flight Arrival Departure Numbers']"
    AIRCRAFT_TYPE = "//div[@class='aircraft_type']"
    AIRCRAFT_STATUS = "//div[contains(@class,'fefoclass')]//div[@class = 'fefodiv']" # NA For NOP Section
    BAY_NUMBER = "//div[contains(@class,'bay-col')]"
    GATE_NUMBER = "//div[contains(@class,'gate-col')]"
    ETA = "//div[contains(@class,'arrival-time-col')]//div[@class='dropdown-content']/p[contains(text(),'ETA')]"
    STA = "//div[contains(@class,'arrival-time-col')]//div[@class='dropdown-content']/p[contains(text(),'STA')]"
    STD = "//div[contains(@class,'departure-time-col')]//div[@class='dropdown-content']/p[contains(text(),'STD')]"
    ETD = "//div[contains(@class,'departure-time-col')]//div[@class='dropdown-content']/p[contains(text(),'ETD')]"
    ALERT_COL_BUTTON = "//div[contains(@class,'alerts-col')]//button"
    ALERT_DETAILS_POPUP = "//div[@class='grid_alerts_menu']//div[@class='notification-div']"
    ALERT_CARDS_IN_POPUP = "//div[@class='grid_alerts_menu']//div[@class='notification-div']//div[contains(@class,'alert-card')]"
    ALERT_TITLE_HEADER = "//div[@class='grid_alerts_menu']//div[@class='notification-div']//div[contains(@class,'alert-card')]//div[@class='alert-title-name']"
    ALERT_TYPE = "//div[@class='grid_alerts_menu']//div[@class='notification-div']//div[contains(@class,'alert-card')]//div[@class='alert-type']"
    ALERT_SUBTITLE = "//div[@class='grid_alerts_menu']//div[@class='notification-div']//div[contains(@class,'alert-card')]//pre[@class='alert-subtitle']"
    ALERT_POPUP_CLOSE_BUTTON = "//div[@class='notification-div']//mat-icon[text()='close']"
    FLAG_ICON_BUTTON = "//div[contains(@class,'flag-col')]//button"
    FLAG_POPUP = "//div[contains(@class,'flag-config')]"
    FLAG_REASON = "//mat-select[@placeholder = 'Flag Reason']"
    FLAG_SUBMIT_BUTTON = "//div[contains(@class,'flag-config')]//button[contains(@class,'savebutton')]" 
    PAX_COUNT = "//div[contains(@class,'pax_count-col')]/div[@class='dropdown']/div[@class='dropbtn']"
    PAX_COUNT_POPUP = "//div[contains(@class,'pax_count-col')]/div[@class='dropdown']/div[@class='dropdown-content']"
    IPORT_ICON = "//div[@mattooltip='IPORT']"
    IPORT_EVENTS_POPUP = "//div[contains(@class,'p-dialog-content')]"
    IPORT_EVENTS_CARDS = "//div[contains(@class,'p-dialog-content')]//div[contains(@class,'p-accordion-header')]"
    IPORT_EVENTS_POPUP_CLOSE_BUTTON = "//div[contains(@class,'p-dialog-header')]//button[contains(@class,'p-dialog-header-close')]"
    EDIT_FLIGHT_MENU_ICON = "//mat-icon[@mattooltip='Edit Flight']"
    EDIT_FLIGHT_MENU_POPUP = "//div[contains(@class,'mat-menu-content')]"
    ADD_ALERT_TASK_BUTTON = "//div[contains(@class,'mat-menu-content')]//span[text()='Add Alert/Task']" # NA For NOP Section
    ADD_ALERT_ALERT_NAME = "//div[@class='inputmainDiv']//input[@id='taskName']" # NA For NOP Section
    ADD_ALERT_ALERT_CATEGORY = "//div[@class='inputmainDiv']//p-dropdown[@id='alertCategory']" # NA For NOP Section
    ADD_ALERT_ALERT_CATEGORY_OPTIONS_ALERT = "//div[contains(@class,'p-dropdown-items-wrapper')]//span[text()='Alert']" # NA For NOP Section
    ADD_ALERT_ALERT_CATEGORY_OPTIONS_TASK = "//div[contains(@class,'p-dropdown-items-wrapper')]//span[text()='Task']" # NA For NOP Section
    ADD_ALERT_ALERT_CATEGORY_OPTIONS_INCIDENT = "//div[contains(@class,'p-dropdown-items-wrapper')]//span[text()='Incident Reporting']" # NA For NOP Section
    ADD_ALERT_SELECT_ALERT_TYPE_ARRIVAL = "//div[@class='alertTypeOptionsDiv']//h1[text() = 'Arrival']" # NA For NOP Section
    ADD_ALERT_SELECT_ALERT_TYPE_DEPARTURE = "//div[@class='alertTypeOptionsDiv']//h1[text() = 'Departure']" # NA For NOP Section
    ADD_ALERT_SAVE_BUTTON = "//div[contains(@class,'savebuttondiv')]//h1[text() = 'Save']" # NA For NOP Section
    FLIGHT_MILESTONES_BUTTON = "//div[contains(@class,'mat-menu-content')]//span[text()='Flight Milestones']"
    
    # Only for Ongoing and Incoming Section

    EDIT_FLIGHT_BUTTON = "//div[contains(@class,'mat-menu-content')]//span[text()='Edit Flight']"
    #EDIT_FLIGHT_ARRIVAL_NUMBER = "//div[contains(@class,'aff-field')]//input[@name='ArrivalFlightNo']"
    #EDIT_FLIGHT_DEPARTURE_NUMBER = "//div[contains(@class,'aff-field')]//input[@name='DepartureFlightNo']"
    #EDIT_FLIGHT_AIRCRAFT_TYPE = "//div[contains(@class,'aff-field')]//p-dropdown[@name='AircraftType']"
    #EDIT_FLIGHT_AIRCRAFT_TYPE_OPTIONS_SEARCH = "//div[contains(@class,'p-dropdown-filter-container')]//input[contains(@class,'p-dropdown-filter')]"
    #EDIT_FLIGHT_AIRCRAFT_TYPE_OPTIONS_SEARCH_BUTTON = "//div[contains(@class,'p-dropdown-filter-container')]//span[contains(@class,'p-dropdown-filter-icon')]"
    #EDIT_FLIGHT_AIRCRAFT_TYPE_OPTIONS = "//div[contains(@class,'p-dropdown-items-wrapper')]//span[text()='B37M']" # It is static while providing the data need to add through variable
    ACTIVITY_DROPDOWN_CARD = "//div[@class='ng-star-inserted']/mat-accordion[@class='mat-accordion']//mat-expansion-panel-header[@role='button']"
    ACTIVITY_NAMES_IN_PTS_LIST = "//div[@class='activities']//span[@class='ng-star-inserted']"
    # Only for Ongoing and Departed Section

    LOCK_FLIGHT_BUTTON = "//div[contains(@class,'mat-menu-content')]//span[text()='Lock Flight']"
    LOCK_FLIGHT_POPUP = "//form[contains(@class,'lock-dialog')]"
    LOCK_FLIGHT_REASON = "//input[@formcontrolname='lock_reason']"
    LOCK_FLIGHT_POPUP_LOCK_AND_UNLOCK_BUTTON = "//div[contains(@class,'lock-row')]/button[@type='submit']"
    LOCK_FLIGHT_POPUP_CANCEL_BUTTON = "//div[contains(@class,'lock-row')]/button/span[text()='Cancel']"
    UNLOCK_FLIGHT_BUTTON = "//div[contains(@class,'mat-menu-content')]//span[text()='Unlock Flight']"
    DETAIL_VIEW_ARROW = "//div[contains(@class,'moreInfoStyles')]/mat-icon[text()='arrow_forward']"

    # Only for Ongoing Section

    COUNTDOWN_TIMER = "//div[contains(@class,'countdown-col-incoming')]"
    COUNTDOWN_TIMER_NUMBER = "//div[contains(@class,'countdown-col-incoming')]//div[contains(@class,'progress-ring__number')]"
    ONBLOCK_TIME = "//div[@class='arrival-time-col']//div[@class='dropdown-content']//p[contains(text(),'ONBL')]/span"
    OFFBLOCK_TIME = "//div[contains(@class,'departure-time-col')]//div[@class='dropdown-content']//p[contains(text(),'OFBL')]/span"
    

    # Only for Incoming Section

    CANCEL_FLIGHT_BUTTON = "//div[contains(@class,'mat-menu-content')]//span[text()='Cancel Flight']"

    # Only for Departed Section

    FLIGHT_CARD_BUTTON = "//div[contains(@class,'mat-menu-content')]//span[text()='Flight Card']"
    FLIGHT_MENU_ICON = "//mat-icon[@aria-haspopup='menu' and contains(text(),'more_vert')]"
    FLIGHT_CARD_BUTTON = "//button[contains(@class,'edit_Flight_button')]/span[text()='Flight Card']"

    def navigate_to_list_view_page(self):

        logger.info("Navigating to List View")

        # Checking Menu
        #self.page.wait_for_timeout(3000)
        menu = self.page.locator(self.MENU)
        self.wait_for_element(menu, state="visible", timeout=30000)
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
        logger.info("List View Page is Loaded Successfully")


    def flight_are_visible(self):   
        # Checking Flights are Visible
        with allure.step("Checking Flights are Visible in Dashboard"):
            #time.sleep(10)
            flights = self.page.locator("//mat-card[contains(@class,'listviewmatcard')]")
            expect(flights.first).to_be_visible()
            logger.info("Flights are Visible")

    def count_of_flights(self):
        # Counting the Number of Flights
        ongoing_flights = self.page.locator(self.FLIGHT_ROW_CARDS)
        expect(ongoing_flights.first).to_be_visible()
        number_of_flights = ongoing_flights.count()
        logger.info(f"Totally we have {number_of_flights} Flights")

        return number_of_flights


    def activity_dropdown_is_displayed(self, Flight_Card):
        with allure.step(f"Checking Activity Dropdown is Displayed"):
            logger.info(f"Flight Card is Displayed")
            expect(Flight_Card).to_be_visible()
            logger.info(f"Clicking Flight Card")
            Flight_Card.click()
            logger.info(f"Clicked Flight Card")
            time.sleep(10)
            activity_dropdown = Flight_Card.locator(self.ACTIVITY_DROPDOWN_CARD)
            count_of_activity_dropdown = activity_dropdown.count()
            logger.info(f"Activity Dropdown Count = {count_of_activity_dropdown}")
            logger.info(f"Validating Activity Dropdown for Flight Card")
            expect(activity_dropdown.first).to_be_visible()
            logger.info(f"Activity Dropdown Displayed for Flight Card")

        return count_of_activity_dropdown

    def pts_is_displayed(self, Activity_Dropdown, Flight_Card):
        with allure.step(f"Checking PTS is Displayed"):
            logger.info(f"Activity Dropdown is Displayed")
            expect(Activity_Dropdown).to_be_visible()
            logger.info(f"Clicking Activity Dropdown")
            Activity_Dropdown.click()
            logger.info(f"Clicked Activity Dropdown")
            time.sleep(5)
            pts_names_list = Flight_Card.locator(self.ACTIVITY_NAMES_IN_PTS_LIST)
            logger.info(f"Validating PTS Names List for Activity Dropdown")
            expect(pts_names_list.first).to_be_visible()
            logger.info(f"PTS Names List Displayed for Activity Dropdown")


    def fetch_onblock_time(self, Flight_Card):
        with allure.step(f"Fetching Onblock Time"):
            logger.info(f"Flight Card is Displayed")
            expect(Flight_Card).to_be_visible()
            logger.info(f"Clicking Flight Card")
            Flight_Card.click()
            logger.info(f"Clicked Flight Card")
            time.sleep(10)
            onblock_time = Flight_Card.locator().text_content()
            logger.info(f"Onblock Time for Flight Card = {onblock_time}")

        return onblock_time


