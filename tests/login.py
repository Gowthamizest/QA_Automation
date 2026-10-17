import pytest
import allure
from pages.login_page import LoginPage
from utils.logger import get_logger

logger = get_logger(__name__)


@pytest.mark.smoke
@pytest.mark.login
def test_login(page):

    logger.info("Starting test_login")

    try:
        login_page = LoginPage(page, None)

        title = login_page.get_title()
        logger.info(f"Page title is: {title}")

        assert "AviLeap" in title

    except Exception as e:
        logger.error(f"Test failed due to: {str(e)}")
        raise  # VERY IMPORTANT → don’t remove this

    finally:
        logger.info("Test execution completed")