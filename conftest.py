import os
import pytest
from playwright.sync_api import sync_playwright
from pages.base_page import BasePage
from pages.login_page import LoginPage
from utils.config import Config
from utils.email_sender import EmailSender


def pytest_addoption(parser):

    parser.addoption("--project", action="store", default="salzburg", help="Project Name")
    parser.addoption("--env", action="store", default="qa", help="Environment Name")
    parser.addoption("--browser", action="store", default="chromium", help="Browser Name")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):

    outcome = yield
    rep = outcome.get_result()

    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture(scope="function")
def page(request):

    project = request.config.getoption("--project")
    env = request.config.getoption("--env")
    browser_name = request.config.getoption("--browser")

    config = Config.get_config(project, env)

    with sync_playwright() as p:

        if browser_name.lower() == "chromium":
            browser = p.chromium.launch(headless=False,args=["--start-maximized"])

        elif browser_name.lower() == "firefox":
            browser = p.firefox.launch(headless=False)

        elif browser_name.lower() == "webkit":
            browser = p.webkit.launch(headless=False)

        else:
            raise ValueError(f"Unsupported browser: {browser_name}")

        context = browser.new_context(
            no_viewport=True
        )

        page = context.new_page()

        base = BasePage(page,config["url"])

        base.open_application()

        if "login" in request.keywords:

            login_page = LoginPage(page,config["url"])

            login_page.login_user(config["username"],config["password"])

        yield page

        if (hasattr(request.node, "rep_call")and request.node.rep_call.failed):
            base.capture_failure_screenshot("Failure Screenshot")

        context.close()
        browser.close()


def pytest_sessionstart(session):

    os.makedirs("reports", exist_ok=True)
    results_xml = os.path.join("reports", "results.xml")

    if os.path.exists(results_xml):
        os.remove(results_xml)


def pytest_sessionfinish(session, exitstatus):

    project = session.config.getoption("--project")
    env = session.config.getoption("--env")
    browser = session.config.getoption("--browser")

    try:

        email = EmailSender()
        email.send_execution_report(project=project, env=env, browser=browser, xml_file=os.path.join("reports", "results.xml"))

    except Exception as e:

        print(f"Failed to send execution email: {e}")
