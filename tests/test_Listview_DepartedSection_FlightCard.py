
import pytest
import allure

from pages.Listview_DepartedSection_FlightCard import (
    Listview_DepartedSection_FlightCard
)
from utils.logger import get_logger

logger = get_logger(__name__)


@pytest.mark.smoke
@pytest.mark.login
def test_Listview_DepartedSection_FlightCard(page):

    logger.info("Starting List View Departed Flight Card Test")

    departed_page = Listview_DepartedSection_FlightCard(page)

    with allure.step("Navigate to Flights List View"):
        departed_page.navigate_to_list_view_page()

    with allure.step("Select Departed Flights"):
        departed_page.select_departed_flights()

    with allure.step("Validate Flight Cards for all departed flights"):
        departed_page.check_all_departed_flight_cards()

    logger.info(
        "List View Departed Flight Card Test completed successfully"
    )
