
import pytest
import allure

from pages.Listview_DepartedSection_AccesstoAIMedia import Listview_DepartedSection_AccesstoAIMedia
from utils.logger import get_logger

logger = get_logger(__name__)


@pytest.mark.smoke
@pytest.mark.login
def test_Listview_DepartedSection_AccesstoAIMedia(page):

    logger.info("Starting List View Departed Section Test")

    departed_page = Listview_DepartedSection_AccesstoAIMedia(page)

    with allure.step("Navigate to Flights List View"):
        departed_page.navigate_to_list_view_page()

    with allure.step("Select Departed Flights"):
        departed_page.select_departed_flights()

    with allure.step("Validate all departed flights and AI media"):
        departed_page.check_all_departed_flights()

    logger.info("List View Departed Section Test completed successfully")
