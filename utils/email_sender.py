"""Generate and send station-wise Playwright/Pytest execution summary emails.

Configuration is read strictly from environment variables (.env).
Email body structure displays consolidated smoke test summary by airport.
"""

from __future__ import annotations

import html
import os
import re
import smtplib
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

EMAIL_PATTERN = r"[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+"


class EmailSender:
    """Create a station-wise summary email and attach HTML reports."""

    MAX_REPORT_SIZE = 8 * 1024 * 1024  # 8 MB per report

    def __init__(self):
        # Configuration is loaded strictly from environment variables (.env)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.office365.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("EMAIL_SENDER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")

        self.receiver_emails = self._split_addresses(
            os.getenv("EMAIL_RECEIVERS") or os.getenv("EMAIL_TO") or ""
        )
        self.cc_emails = self._split_addresses(
            os.getenv("EMAIL_CC") or ""
        )

        self.attach_report = os.getenv(
            "EMAIL_ATTACH_REPORT", "true"
        ).strip().lower() in ("1", "true", "yes", "y")

        logger.info("SMTP_SERVER = %s", self.smtp_server)
        logger.info("SMTP_PORT = %s", self.smtp_port)
        logger.info("EMAIL_SENDER = %s", self.sender_email)
        logger.info("EMAIL_RECEIVERS = %s", self.receiver_emails)
        if self.cc_emails:
            logger.info("EMAIL_CC = %s", self.cc_emails)

    # --------------------------------------------------------------
    # Configuration & Helpers
    # --------------------------------------------------------------

    def _split_addresses(self, text: Optional[str]) -> List[str]:
        return [
            address.strip()
            for address in re.split(r"[;,]", text or "")
            if address.strip()
        ]

    def _check_settings(self) -> None:
        if not self.smtp_server:
            raise ValueError("SMTP_SERVER missing in .env")
        if not self.sender_email:
            raise ValueError("EMAIL_SENDER missing in .env")
        if not self.sender_password:
            raise ValueError("EMAIL_PASSWORD missing in .env")
        if not self.receiver_emails:
            raise ValueError("EMAIL_RECEIVERS missing in .env")

        invalid = [
            address
            for address in self.receiver_emails + self.cc_emails
            if not re.fullmatch(EMAIL_PATTERN, address)
        ]
        if invalid:
            raise ValueError(f"Invalid email address(es) in .env: {invalid}")

    def recipients_for(self, project: Optional[str] = None, station: Optional[str] = None) -> Dict[str, List[str]]:
        """Return recipients strictly from .env configuration."""
        return {
            "to": self.receiver_emails.copy(),
            "cc": self.cc_emails.copy(),
            "invalid": [],
        }

    @staticmethod
    def _station_title(station_name: Any) -> str:
        """Format station heading as '<Code> Airport'."""
        station = str(station_name or "").strip()
        if not station or station.upper() in ("ALL", "UNKNOWN", "-", "NONE", "ALL STATIONS"):
            return "Airport"
        if station.upper().endswith("AIRPORT"):
            return station
        return f"{station} Airport"

    @staticmethod
    def _format_duration(seconds: Any) -> str:
        """Format seconds into '0h 9m 18s+293ms'."""
        try:
            sec_float = float(seconds or 0.0)
        except (ValueError, TypeError):
            sec_float = 0.0
        sec_float = max(0.0, sec_float)
        hours = int(sec_float // 3600)
        remainder = sec_float % 3600
        minutes = int(remainder // 60)
        rem_secs = remainder % 60
        secs = int(rem_secs)
        ms = int(round((rem_secs - secs) * 1000))
        if ms >= 1000:
            secs += 1
            ms -= 1000
        return f"{hours}h {minutes}m {secs}s+{ms}ms"

    @staticmethod
    def _clean_test_name(name: Any) -> str:
        """Strip parameterized suffix like '[DXB]' while keeping test name intact."""
        clean = re.sub(r"\[.*?\]$", "", str(name or "")).strip()
        return clean or str(name or "")

    # --------------------------------------------------------------
    # XML Parsing
    # --------------------------------------------------------------

    def _station_from_testcase(self, testcase: ET.Element, default_station: Optional[str] = None) -> str:
        """Identify a station from JUnit XML metadata or test name."""
        properties = testcase.find("properties")
        if properties is not None:
            for prop in properties.findall("property"):
                key = prop.get("name", "").strip().lower()
                value = prop.get("value", "").strip()
                if key in ("station", "stations", "airport", "location") and value:
                    first_st = [s.strip().upper() for s in value.split(",") if s.strip()]
                    if first_st:
                        return first_st[0]

        combined = f"{testcase.get('classname', '')} {testcase.get('name', '')}"
        patterns = (
            r"\b(?:station|airport)\s*[:=_-]\s*([A-Za-z0-9_-]+)",
            r"\b([A-Z0-9_-]{2,10})\s+Airport\b",
            r"\[([A-Z0-9_-]+)\]",
        )
        for pattern in patterns:
            match = re.search(pattern, combined, flags=re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return str(default_station or "DEFAULT").upper()

    @staticmethod
    def _status_from_testcase(testcase: ET.Element) -> str:
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            return "FAILED"
        if testcase.find("skipped") is not None:
            return "SKIPPED"
        return "PASSED"

    @staticmethod
    def _warning_count(testcase: ET.Element) -> int:
        warning_count = 0
        for tag in ("system-out", "system-err"):
            element = testcase.find(tag)
            if element is not None and element.text:
                warning_count += sum(
                    1
                    for line in element.text.splitlines()
                    if re.search(r"\bWARNING\b|\bWARN\b", line, re.I)
                )
        return warning_count

    @staticmethod
    def _duration(testcase: ET.Element) -> float:
        try:
            return max(0.0, float(testcase.get("time", "0")))
        except (TypeError, ValueError):
            return 0.0

    def _count_results(self, testcases: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(testcases)
        passed = 0
        failed = 0
        skipped = 0
        passed_tests: List[str] = []
        failed_tests: List[str] = []
        skipped_tests: List[str] = []
        warning_tests: List[str] = []
        total_duration = 0.0
        total_warnings = 0

        for item in testcases:
            status = item["status"]
            name = item["display_name"]
            total_duration += item.get("duration", 0.0)
            item_warnings = item.get("warnings", 0)
            total_warnings += item_warnings

            if status == "FAILED":
                failed += 1
                failed_tests.append(name)
            elif status == "SKIPPED":
                skipped += 1
                skipped_tests.append(name)
            else:
                passed += 1
                passed_tests.append(name)

            if item_warnings > 0:
                warning_tests.append(name)

        pass_pct = (passed / total * 100.0) if total else 0.0
        fail_pct = (failed / total * 100.0) if total else 0.0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "warnings": total_warnings,
            "duration": total_duration,
            "formatted_duration": self._format_duration(total_duration),
            "pass_percent": f"{pass_pct:.2f} %",
            "fail_percent": f"{fail_pct:.2f} %",
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "warning_tests": warning_tests,
        }

    def parse_pytest_results(self, xml_file: Any, station: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Parse pytest JUnit XML and group unique test results by station."""
        xml_path = Path(xml_file)
        if not xml_path.is_file():
            raise FileNotFoundError(f"Result file not found: {xml_file}")

        root = ET.parse(xml_path).getroot()
        grouped: Dict[tuple, Dict[str, Any]] = {}

        for testcase in root.iter("testcase"):
            station_name = self._station_from_testcase(testcase, station)
            name = testcase.get("name", "Unknown Test")
            classname = testcase.get("classname", "Unknown File")
            key = (station_name, classname, name)

            item = {
                "name": name,
                "display_name": self._clean_test_name(name),
                "classname": classname,
                "status": self._status_from_testcase(testcase),
                "duration": self._duration(testcase),
                "warnings": self._warning_count(testcase),
            }

            existing = grouped.get(key)
            if existing is None:
                grouped[key] = item
            else:
                priority = {"PASSED": 0, "SKIPPED": 1, "FAILED": 2}
                if priority[item["status"]] > priority[existing["status"]]:
                    existing["status"] = item["status"]
                existing["duration"] += item["duration"]
                existing["warnings"] += item["warnings"]

        stations: Dict[str, List[Dict[str, Any]]] = {}
        for (station_name, _, _), item in grouped.items():
            stations.setdefault(station_name, []).append(item)

        summaries = {
            station_name: self._count_results(items)
            for station_name, items in sorted(stations.items())
        }

        logger.info(
            "Parsed %s unique tests across %s station(s)",
            len(grouped),
            len(summaries),
        )
        return summaries

    # --------------------------------------------------------------
    # TestRecord (Pytest Session) In-Memory Summarization
    # --------------------------------------------------------------

    def summarize_records(
        self,
        records: List[Any],
        requested_stations: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Group in-memory pytest TestRecord objects by station and summarize.

        Ensures full consistency with the expected email body structure.
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {}

        for r in records:
            airport = str(getattr(r, "airport", "-")).strip()
            mapped = getattr(r, "stations", [airport])

            # Determine stations this test record belongs to
            stations_for_record = []
            if requested_stations:
                for st in requested_stations:
                    if st in mapped or "ALL" in mapped or airport == st:
                        stations_for_record.append(st)
            else:
                stations_for_record = [airport] if airport and airport != "-" else mapped

            if not stations_for_record:
                stations_for_record = [airport or "DEFAULT"]

            name = getattr(r, "name", "") or getattr(r, "nodeid", "Unknown Test")
            display_name = self._clean_test_name(name)
            status_raw = str(getattr(r, "status", "PASSED")).upper()
            if status_raw in ("FAILED", "ERROR"):
                status = "FAILED"
            elif status_raw == "SKIPPED":
                status = "SKIPPED"
            else:
                status = "PASSED"

            duration = float(getattr(r, "duration", 0.0) or 0.0)
            warnings = int(getattr(r, "warnings", 0) or 0)

            item = {
                "name": name,
                "display_name": display_name,
                "status": status,
                "duration": duration,
                "warnings": warnings,
            }

            for st in set(stations_for_record):
                st_code = st.strip().upper()
                grouped.setdefault(st_code, []).append(item)

        if requested_stations:
            for st in requested_stations:
                st_code = st.strip().upper()
                grouped.setdefault(st_code, [])

        return {
            st: self._count_results(items)
            for st, items in sorted(grouped.items())
        }

    # --------------------------------------------------------------
    # Email Body Builders (Plain Text & HTML)
    # --------------------------------------------------------------

    def _resolve_summaries(self, *args, **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        Support both signatures:
          build_email_body(summaries)
          build_email_body(project, env, browser, summaries)
        """
        if "summaries" in kwargs:
            return kwargs["summaries"]
        if len(args) == 1 and isinstance(args[0], dict):
            return args[0]
        if len(args) >= 4 and isinstance(args[3], dict):
            return args[3]
        raise ValueError("Invalid arguments passed to email body builder; summaries dict expected.")

    def build_plain_text(self, *args, **kwargs) -> str:
        """Plain-text email body exactly matching the requested format."""
        summaries = self._resolve_summaries(*args, **kwargs)

        lines = [
            "Automation Smoke Test Summary",
            "",
        ]

        station_items = list(summaries.items())
        for idx, (station, summary) in enumerate(station_items):
            station_title = self._station_title(station)
            lines.append(station_title)
            lines.append("")
            lines.append("")
            lines.append(f"Total Test Cases\t{summary['total']}")
            lines.append(f"Passed\t{summary['passed']}")
            lines.append(f"Failed\t{summary['failed']}")
            lines.append(f"Skipped\t{summary['skipped']}")
            lines.append(f"Warnings\t{summary['warnings']}")
            lines.append(f"Execution Time\t{summary['formatted_duration']}")
            lines.append(f"Pass Percentage\t{summary['pass_percent']}")
            lines.append(f"Fail Percentage\t{summary['fail_percent']}")
            lines.append("")

            lines.append("Passed Test Cases")
            if summary.get("passed_tests"):
                lines.extend(summary["passed_tests"])
            else:
                lines.append("None")
                lines.append("")

            lines.append("Failed Test Cases")
            if summary.get("failed_tests"):
                lines.extend(summary["failed_tests"])
            else:
                lines.append("None")
                lines.append("")

            lines.append("Skipped Test Cases")
            if summary.get("skipped_tests"):
                lines.extend(summary["skipped_tests"])
            else:
                lines.append("None")

            lines.append("")
            lines.append("Warning Test Cases")
            if summary.get("warning_tests"):
                lines.extend(summary["warning_tests"])
            else:
                lines.append("None")

            if idx < len(station_items) - 1:
                lines.append("")
                lines.append("")

        return "\n".join(lines)

    def build_email_body(self, *args, **kwargs) -> str:
        """HTML email body reflecting the requested format cleanly."""
        summaries = self._resolve_summaries(*args, **kwargs)

        sections_html = []
        for idx, (station, summary) in enumerate(summaries.items()):
            station_title = html.escape(self._station_title(station))

            def render_test_list(tests: List[str]) -> str:
                if not tests:
                    return '<div style="font-size:13px;color:#222222;margin-bottom:12px;">None</div>'
                items = "".join(f'<div style="margin:2px 0;">{html.escape(t)}</div>' for t in tests)
                return f'<div style="font-size:13px;color:#222222;margin-bottom:12px;">{items}</div>'

            section = f"""
            <div style="margin-top:{'0' if idx == 0 else '35px'};margin-bottom:20px;">
              <div style="font-size:16px;font-weight:bold;color:#111111;margin-bottom:14px;">{station_title}</div>
              <table cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-family:inherit;font-size:13px;margin-bottom:18px;min-width:320px;">
                <tbody>
                  <tr>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;color:#111111;width:160px;">Total Test Cases</td>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;text-align:left;color:#111111;">{summary['total']}</td>
                  </tr>
                  <tr>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;color:#111111;">Passed</td>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;text-align:left;color:#111111;">{summary['passed']}</td>
                  </tr>
                  <tr>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;color:#111111;">Failed</td>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;text-align:left;color:#111111;">{summary['failed']}</td>
                  </tr>
                  <tr>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;color:#111111;">Skipped</td>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;text-align:left;color:#111111;">{summary['skipped']}</td>
                  </tr>
                  <tr>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;color:#111111;">Warnings</td>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;text-align:left;color:#111111;">{summary['warnings']}</td>
                  </tr>
                  <tr>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;color:#111111;">Execution Time</td>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;text-align:left;color:#111111;">{summary['formatted_duration']}</td>
                  </tr>
                  <tr>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;color:#111111;">Pass Percentage</td>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;text-align:left;color:#111111;">{summary['pass_percent']}</td>
                  </tr>
                  <tr>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;color:#111111;">Fail Percentage</td>
                    <td style="border:1px solid #d0d7de;padding:6px 14px;text-align:left;color:#111111;">{summary['fail_percent']}</td>
                  </tr>
                </tbody>
              </table>

              <div style="font-weight:bold;font-size:13px;margin-top:14px;margin-bottom:4px;color:#111111;">Passed Test Cases</div>
              {render_test_list(summary.get('passed_tests', []))}

              <div style="font-weight:bold;font-size:13px;margin-top:14px;margin-bottom:4px;color:#111111;">Failed Test Cases</div>
              {render_test_list(summary.get('failed_tests', []))}

              <div style="font-weight:bold;font-size:13px;margin-top:14px;margin-bottom:4px;color:#111111;">Skipped Test Cases</div>
              {render_test_list(summary.get('skipped_tests', []))}

              <div style="font-weight:bold;font-size:13px;margin-top:14px;margin-bottom:4px;color:#111111;">Warning Test Cases</div>
              {render_test_list(summary.get('warning_tests', []))}
            </div>
            """
            sections_html.append(section)

        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
</head>
<body style="margin:0;padding:20px;font-family:Arial,'Segoe UI',sans-serif;color:#111111;background-color:#ffffff;line-height:1.4;">
  <div style="max-width:800px;margin:0 auto;">
    <div style="font-size:18px;font-weight:bold;color:#111111;margin-bottom:20px;">Automation Smoke Test Summary</div>
    {''.join(sections_html)}
  </div>
</body>
</html>"""

    # --------------------------------------------------------------
    # Report Attachments
    # --------------------------------------------------------------

    def _normalise_report_paths(
        self,
        report_path: Optional[Any] = None,
        report_paths: Optional[Any] = None,
    ) -> List[tuple]:
        if report_paths is not None:
            if isinstance(report_paths, dict):
                return list(report_paths.items())
            if isinstance(report_paths, (list, tuple, set)):
                return [(Path(p).stem.upper(), p) for p in report_paths]
            return [("REPORT", report_paths)]
        if report_path:
            return [("REPORT", report_path)]
        return []

    def _attach_reports(
        self,
        message: Any,
        report_path: Optional[Any] = None,
        report_paths: Optional[Any] = None,
    ) -> None:
        if not self.attach_report:
            logger.info("HTML report attachments disabled by .env (EMAIL_ATTACH_REPORT=false)")
            return

        from email import encoders
        from email.mime.base import MIMEBase

        all_paths = self._normalise_report_paths(report_path, report_paths)
        seen_paths = set()

        for station_label, path_val in all_paths:
            if not path_val:
                continue
            path = Path(path_val)
            if not path.is_file():
                logger.warning("Report file not found; skipping attachment: %s", path)
                continue

            resolved_path = str(path.resolve())
            if resolved_path in seen_paths:
                continue
            seen_paths.add(resolved_path)

            size = path.stat().st_size
            if size > self.MAX_REPORT_SIZE:
                logger.warning(
                    "HTML report exceeds %s MB; skipping attachment: %s",
                    self.MAX_REPORT_SIZE // (1024 * 1024),
                    path,
                )
                continue

            # Use application/octet-stream so email clients (Outlook/Gmail) attach it as a downloadable/openable file
            # instead of attempting to display raw HTML source code in a text previewer.
            attachment = MIMEBase("application", "octet-stream")
            with path.open("rb") as rf:
                attachment.set_payload(rf.read())
            encoders.encode_base64(attachment)
            attachment.add_header("Content-Disposition", "attachment", filename=path.name)
            message.attach(attachment)
            logger.info(
                "Attached HTML report for %s: %s (%.2f MB)",
                station_label,
                path.name,
                size / (1024 * 1024),
            )

    # --------------------------------------------------------------
    # SMTP Delivery
    # --------------------------------------------------------------

    def _send_smtp_message(self, message: Any) -> bool:
        server = None
        try:
            logger.info("Creating SMTP connection to %s:%s", self.smtp_server, self.smtp_port)
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=45)
            logger.info("Starting TLS")
            server.starttls()
            logger.info("Logging in as %s", self.sender_email)
            server.login(self.sender_email, self.sender_password)

            recipients = self.receiver_emails + self.cc_emails
            logger.info("Delivering email to %s", recipients)
            server.sendmail(self.sender_email, recipients, message.as_string())
            logger.info("Email delivered successfully!")
            return True
        except Exception as error:
            logger.error("%s: %s", type(error).__name__, error)
            logger.error(traceback.format_exc())
            raise
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    logger.warning("SMTP connection was already closed or could not quit cleanly")

    # --------------------------------------------------------------
    # Public Send Methods
    # --------------------------------------------------------------

    def send_session_report(
        self,
        meta: Dict[str, Any],
        records: List[Any],
        station_reports: Optional[Dict[str, str]] = None,
        consolidated_report: Optional[str] = None,
    ) -> bool:
        """
        Send a consolidated smoke test report for the pytest session.

        Reads configuration strictly from .env and compiles results for all
        executed airports/stations into a single email body.
        """
        self._check_settings()

        requested_stations = [
            s.strip().upper()
            for s in str(meta.get("airports", "")).split(",")
            if s.strip() and s.strip() != "-"
        ]
        summaries = self.summarize_records(records, requested_stations=requested_stations)
        if not summaries:
            logger.warning("No test summaries generated from records; email not sent.")
            return False

        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        body_html = self.build_email_body(summaries)
        body_text = self.build_plain_text(summaries)

        total_failed = sum(s["failed"] for s in summaries.values())
        total_executed = sum(s["total"] for s in summaries.values())
        if total_executed == 0:
            verdict = "NO TESTS EXECUTED"
        elif total_failed:
            verdict = "FAILED"
        else:
            verdict = "PASSED"

        project = meta.get("project", "AUTOMATION")
        env = meta.get("env", "QA")
        stations_label = ", ".join(summaries.keys()) if len(summaries) <= 3 else "MULTI-STATION"

        subject = f"Automation Smoke Test Summary - [{str(project).upper()}] [{str(env).upper()}] [{stations_label}] - {verdict}"

        message = MIMEMultipart("mixed")
        message["From"] = self.sender_email
        message["To"] = ", ".join(self.receiver_emails)
        if self.cc_emails:
            message["Cc"] = ", ".join(self.cc_emails)
        message["Subject"] = subject

        alternatives = MIMEMultipart("alternative")
        alternatives.attach(MIMEText(body_text, "plain", "utf-8"))
        alternatives.attach(MIMEText(body_html, "html", "utf-8"))
        message.attach(alternatives)

        # Attach all reports (both consolidated and station-specific)
        all_report_paths: Dict[str, str] = {}
        if station_reports:
            all_report_paths.update(station_reports)
        if consolidated_report:
            all_report_paths["CONSOLIDATED"] = consolidated_report

        self._attach_reports(message, report_paths=all_report_paths)

        return self._send_smtp_message(message)

    def send_execution_report(
        self,
        project: Any,
        env: Any,
        browser: Any,
        xml_file: Any,
        report_path: Optional[Any] = None,
        station: Optional[Any] = None,
        report_paths: Optional[Any] = None,
    ) -> bool:
        """
        Send a consolidated email from JUnit XML results.

        Reads configuration strictly from .env and formats the email body
        according to the required summary layout.
        """
        self._check_settings()

        summaries = self.parse_pytest_results(xml_file, station=station)
        if not summaries:
            logger.warning("No test cases found in %s; email not sent.", xml_file)
            return False

        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        body_html = self.build_email_body(summaries)
        body_text = self.build_plain_text(summaries)

        total_failed = sum(s["failed"] for s in summaries.values())
        total_executed = sum(s["total"] for s in summaries.values())
        if total_executed == 0:
            verdict = "NO TESTS EXECUTED"
        elif total_failed:
            verdict = "FAILED"
        else:
            verdict = "PASSED"

        stations_label = ", ".join(summaries.keys()) if len(summaries) <= 3 else "MULTI-STATION"
        subject = f"Automation Smoke Test Summary - [{str(project).upper()}] [{str(env).upper()}] [{stations_label}] - {verdict}"

        message = MIMEMultipart("mixed")
        message["From"] = self.sender_email
        message["To"] = ", ".join(self.receiver_emails)
        if self.cc_emails:
            message["Cc"] = ", ".join(self.cc_emails)
        message["Subject"] = subject

        alternatives = MIMEMultipart("alternative")
        alternatives.attach(MIMEText(body_text, "plain", "utf-8"))
        alternatives.attach(MIMEText(body_html, "html", "utf-8"))
        message.attach(alternatives)

        self._attach_reports(message, report_path=report_path, report_paths=report_paths)

        return self._send_smtp_message(message)

    def send_station_report(
        self,
        meta: Dict[str, Any],
        station: str,
        station_summary: Optional[Dict[str, Any]] = None,
        subset: Optional[List[Any]] = None,
        path: Optional[str] = None,
        recipients: Optional[Dict[str, List[str]]] = None,
    ) -> bool:
        """Single-station email method for backwards compatibility."""
        if subset:
            summaries = self.summarize_records(subset, requested_stations=[station])
        else:
            total = station_summary.get("total", 0) if station_summary else 0
            passed = station_summary.get("passed", 0) if station_summary else 0
            failed = station_summary.get("failed", 0) if station_summary else 0
            skipped = station_summary.get("skipped", 0) if station_summary else 0
            warnings = station_summary.get("warnings", 0) if station_summary else 0
            duration = meta.get("duration", 0.0)
            pass_pct = (passed / total * 100.0) if total else 0.0
            fail_pct = (failed / total * 100.0) if total else 0.0

            summaries = {
                station.strip().upper(): {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                    "warnings": warnings,
                    "duration": duration,
                    "formatted_duration": self._format_duration(duration),
                    "pass_percent": f"{pass_pct:.2f} %",
                    "fail_percent": f"{fail_pct:.2f} %",
                    "passed_tests": [],
                    "failed_tests": [],
                    "skipped_tests": [],
                    "warning_tests": [],
                }
            }

        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        body_html = self.build_email_body(summaries)
        body_text = self.build_plain_text(summaries)

        project = meta.get("project", "AUTOMATION")
        env = meta.get("env", "QA")
        total_failed = sum(s["failed"] for s in summaries.values())
        verdict = "FAILED" if total_failed else "PASSED"

        subject = f"Automation Smoke Test Summary - [{str(project).upper()}] [{str(env).upper()}] [{station.upper()}] - {verdict}"

        message = MIMEMultipart("mixed")
        message["From"] = self.sender_email
        message["To"] = ", ".join(self.receiver_emails)
        if self.cc_emails:
            message["Cc"] = ", ".join(self.cc_emails)
        message["Subject"] = subject

        alternatives = MIMEMultipart("alternative")
        alternatives.attach(MIMEText(body_text, "plain", "utf-8"))
        alternatives.attach(MIMEText(body_html, "html", "utf-8"))
        message.attach(alternatives)

        if path:
            self._attach_reports(message, report_path=path)

        return self._send_smtp_message(message)
