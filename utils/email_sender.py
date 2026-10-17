import os
import smtplib
import xml.etree.ElementTree as ET

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from allure import testcase
from dotenv import load_dotenv
import traceback

from utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)


class EmailSender:

    def __init__(self):

        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT"))
        self.sender_email = os.getenv("EMAIL_SENDER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        receivers = os.getenv("EMAIL_RECEIVERS","")

        self.receiver_emails = [
            email.strip()
            for email in receivers.split(",")
            if email.strip()
        ]

        # Validate required environment variables

        if not self.smtp_server:
            raise ValueError(
                "SMTP_SERVER missing in .env"
            )

        if not self.sender_email:
            raise ValueError(
                "EMAIL_SENDER missing in .env"
            )

        if not self.sender_password:
            raise ValueError(
                "EMAIL_PASSWORD missing in .env"
            )

        if not self.receiver_emails:
            raise ValueError(
                "EMAIL_RECEIVERS missing in .env"
            )

        logger.info(f"SMTP_SERVER = {self.smtp_server}")
        logger.info(f"SMTP_PORT = {self.smtp_port}")
        logger.info(f"EMAIL_SENDER = {self.sender_email}")
        logger.info(f"EMAIL_RECEIVERS = {self.receiver_emails}")

    def parse_pytest_results(self, xml_file):

        if not os.path.exists(xml_file):
            raise FileNotFoundError(f"Result file not found: {xml_file}")

        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Store unique test results
        test_results = {}

        for testcase in root.iter("testcase"):

            test_name = testcase.attrib.get("name","Unknown Test")
            test_class = testcase.attrib.get("classname","Unknown File")

            test_key = f"{test_class}::{test_name}"

            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped_tag = testcase.find("skipped")

            # Determine current testcase status
            if failure is not None or error is not None:
                current_status = "FAILED"

            elif skipped_tag is not None:
                current_status = "SKIPPED"

            else:
                current_status = "PASSED"

            # Priority:
            # FAILED > SKIPPED > PASSED

            if test_key not in test_results:

                test_results[test_key] = current_status

            else:

                existing_status = test_results[test_key]

                if existing_status == "FAILED":
                    continue

                if current_status == "FAILED":
                    test_results[test_key] = "FAILED"

                elif (existing_status == "PASSED" and current_status == "SKIPPED"):
                    test_results[test_key] = "SKIPPED"

        # Calculate Summary
        total = len(test_results)

        passed = sum(
            1
            for status in test_results.values()
            if status == "PASSED"
        )

        failed = sum(
            1
            for status in test_results.values()
            if status == "FAILED"
        )

        skipped = sum(
            1
            for status in test_results.values()
            if status == "SKIPPED"
        )

        failed_tests = [
            test_name
            for test_name, status
            in test_results.items()
            if status == "FAILED"
        ]

        summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "failed_tests": failed_tests
        }

        print("\n========== Execution Summary ==========")
        print(f"Total Tests   : {summary['total']}")
        print(f"Passed Tests  : {summary['passed']}")
        print(f"Failed Tests  : {summary['failed']}")
        print(f"Skipped Tests : {summary['skipped']}")

        if summary["failed_tests"]:

            print("\nFailed Test Cases:")

            for test in summary["failed_tests"]:
                print(f" - {test}")

        print("=======================================\n")

        return summary

    def build_email_body(self, project, env, browser, summary):

        failed_section = ""

        if summary["failed_tests"]:

            failed_section = """
            <br>
            <h3>Failed Test Cases</h3>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr>
                    <th>Failed Test</th>
                </tr>
            """

            for failed_test in summary["failed_tests"]:

                failed_section += f"""
                <tr>
                    <td>{failed_test}</td>
                </tr>
                """

            failed_section += "</table>"

        html = f"""
        <html>

        <body>

            <h2>Automation Execution Summary</h2>

            <table border="1" cellpadding="6" cellspacing="0">

                <tr>
                    <td><b>Project</b></td>
                    <td>{project}</td>
                </tr>

                <tr>
                    <td><b>Environment</b></td>
                    <td>{env}</td>
                </tr>

                <tr>
                    <td><b>Browser</b></td>
                    <td>{browser}</td>
                </tr>

            </table>

            <br>

            <table border="1" cellpadding="6" cellspacing="0">

                <tr>
                    <th>Total Executed</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Skipped</th>
                </tr>

                <tr>
                    <td>{summary["total"]}</td>
                    <td>{summary["passed"]}</td>
                    <td>{summary["failed"]}</td>
                    <td>{summary["skipped"]}</td>
                </tr>

            </table>

            {failed_section}

            <br><br>

            <b>Framework:</b> Playwright + Pytest

            <br>

            <b>Report Generated Automatically</b>

        </body>

        </html>
        """

        return html

    def send_execution_report(self, project, env, browser, xml_file):
        try:
            summary = self.parse_pytest_results(xml_file)
            body = self.build_email_body(project, env, browser, summary)
            subject = (
                f"[{project.upper()}]"
                f" [{env.upper()}]"
                f" Automation Execution Report"
            )

            # Email Message Configuration
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = ", ".join(self.receiver_emails)
            message["Subject"] = subject
            message.attach(MIMEText(body, "html"))

            logger.info("Connecting to Outlook SMTP Server")

            logger.info("Creating SMTP connection")
            server = smtplib.SMTP(
                self.smtp_server,
                self.smtp_port
            )

            logger.info("Starting TLS")
            server.starttls()

            logger.info("Logging in")
            server.login(
                self.sender_email,
                self.sender_password
            )

            logger.info("Sending Email")
            server.sendmail(
                self.sender_email,
                self.receiver_emails,
                message.as_string()
            )

            logger.info("Closing SMTP connection")
            server.quit()

            logger.info("Execution report email sent successfully.")


        except Exception as error:

            logger.error(
                f"{type(error).__name__}: {error}"
            )

            logger.error(
                traceback.format_exc()
            )

            raise