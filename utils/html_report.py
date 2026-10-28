"""Self-contained, Extent-style HTML report (single file, no external assets).

* Dashboard: totals, pass-rate donut, per-airport table
* Per test: status, airport, TC number, steps, WARNING/ERROR log lines,
  error traceback and screenshots (embedded as base64, click to enlarge)
* One .html file -> easy to attach to e-mail, opens offline in any browser

E-mail delivery is enabled by default when valid station recipients are configured; use --no-email to disable it.
"""
import html
import json
import re
import os
import platform
import time
from datetime import datetime
from pathlib import Path

import pytest

from utils import report_context as rc

_PHASE_STATUS = {"passed": "PASSED", "failed": "FAILED", "skipped": "SKIPPED"}


def norm_tc(value) -> str:
    if not value:
        return ""
    text = re.sub(r"^TC[\s_\-]*", "", str(value).strip().upper())
    return str(int(text)) if text.isdigit() else text


def write_html(path: str | Path, document: str) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    return destination


def write_json(path: str | Path, payload: dict) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return destination


def _tc_label(marker) -> str:
    if not marker or not marker.args:
        return ""
    number = norm_tc(marker.args[0])
    return f"TC{int(number):02d}" if number.isdigit() else f"TC-{number}"


# --------------------------------------------------------------------------- options
def pytest_addoption(parser):
    group = parser.getgroup("html-report")
    group.addoption("--report-dir", action="store", default="reports", help="Folder for the HTML report")
    group.addoption("--report-title", action="store", default="Sanity Automation Execution Report")


def pytest_configure(config):
    if hasattr(config, "workerinput"):  # xdist worker: the controller builds the report
        return
    config.pluginmanager.register(HtmlReportPlugin(config), "html-report-plugin")


# --------------------------------------------------------------------------- plugin

def cfg_station(item):
    values=[v for k,v in item.user_properties if k == "stations"]
    return values[-1] if values else item.config.getoption('--station', default='unknown')

class HtmlReportPlugin:
    def __init__(self, config):
        self.config = config
        self.records: dict = {}
        self.framework_warnings: list = []
        self.started = time.time()
        self.report_path = ""
        self.capture = rc.LogCapture(level=0)

    # ---- lifecycle
    def pytest_sessionstart(self, session):
        self.started = time.time()
        from utils.logger import configure_logging
        cfg = self.config
        project = getattr(cfg, "framework_project", None) or cfg.getoption("--project", default="unknown") or "unknown"
        env = getattr(cfg, "framework_env", None) or cfg.getoption("--env", default="unknown") or "unknown"
        station_req = getattr(cfg, "framework_stations_requested", None)
        station = (station_req[0] if station_req else None) or cfg.getoption("--station", default="unknown") or "unknown"
        configure_logging(project, env, station, str(cfg.rootpath / "logs"))
        import logging
        logging.getLogger().addHandler(self.capture)

    def pytest_unconfigure(self, config):
        import logging
        logging.getLogger().removeHandler(self.capture)

    def pytest_runtest_setup(self, item):
        import logging
        logging.getLogger(__name__).info('TEST START | %s', item.nodeid)

    def pytest_runtest_teardown(self, item, nextitem):
        import logging
        logging.getLogger(__name__).info('TEST TEARDOWN | %s', item.nodeid)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        params = getattr(getattr(item, "callspec", None), "params", {}) or {}
        marker = item.get_closest_marker("tc")
        doc = (getattr(item.function, "__doc__", "") or "").strip().splitlines()
        record = rc.TestRecord(
            nodeid=item.nodeid,
            name=item.name,
            description=re.sub(r"^TC[\s_\-]*\d+\s*[-:]\s*", "", doc[0].strip()) if doc else "",
            airport=str(params.get("station") or params.get("airport") or ",".join(dict.fromkeys(v for k,v in item.user_properties if k == "stations")) or "-"),
            tc=_tc_label(marker),
            markers=sorted({m.name for m in item.iter_markers() if m.name not in ("tc", "parametrize", "usefixtures")}),
            start=time.time(),
        )
        self.records[item.nodeid] = record
        station_values = [v for k,v in item.user_properties if k == "stations"]
        record.stations = [str(params["station"])] if params.get("station") else ([s for s in (station_values[-1].split(",") if station_values else []) if s] or [record.airport])
        rc.set_current(record)
        yield
        record.duration = time.time() - record.start
        if record.status == "RUNNING":
            record.status = "PASSED"
        rc.set_current(None)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        setattr(item, f"rep_{report.when}", report)  # used by fixtures to detect failures
        if report.failed:
            page = getattr(item, "_framework_page", None)
            if page is not None and not page.is_closed():
                from pages.base_page import BasePage
                from utils import report_context
                station_values=[v for k,v in item.user_properties if k == "stations"]
                station=station_values[-1] if station_values else cfg_station(item)
                path=BasePage.capture_failure(page, project=item.config.getoption('--project'), station=station,
                                             test_name=item.name, report_context=report_context,
                                             error_message=report.longreprtext)
                if path:
                    try:
                        import allure
                        allure.attach.file(path, name=f"{item.name} failure", attachment_type=allure.attachment_type.PNG)
                    except Exception:
                        pass

        record = self.records.get(item.nodeid)
        if record is None:
            return
        if report.when == "setup" and report.failed:
            record.status, record.error = "ERROR", report.longreprtext
        elif report.when == "call":
            record.status = _PHASE_STATUS.get(report.outcome, "PASSED")
            if report.failed:
                record.error = report.longreprtext
        elif report.when == "teardown" and report.failed and record.status == "PASSED":
            record.status, record.error = "ERROR", report.longreprtext
        if report.skipped:
            record.status = "SKIPPED"
            reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else str(report.longrepr)
            record.skip_reason = reason.replace("Skipped: ", "")

    def pytest_warning_recorded(self, warning_message, when, nodeid, location):
        self.framework_warnings.append(f"{warning_message.category.__name__}: {warning_message.message}")

    # ---- report
    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        records = list(self.records.values())
        if not records:
            return
        cfg = self.config
        meta = {
            "title": cfg.getoption("--report-title"),
            "project": cfg.getoption("--project", default="-"),
            "env": cfg.getoption("--env", default="-"),
            "browser": getattr(cfg, "_framework_execution_settings", {}).get("browser", cfg.getoption("--browser") or "chromium"),
            "airports": ", ".join(getattr(cfg, "framework_stations_requested", [])) or "-",
            "started": datetime.fromtimestamp(self.started).strftime("%d %b %Y %H:%M:%S"),
            "duration": time.time() - self.started,
            "ended": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            "deselected": getattr(cfg, "framework_deselected_count", 0),
            "host": platform.node(),
            "warnings": self.framework_warnings,
            "plan_warnings": getattr(cfg, "plan_warnings", []),
        }
        summary = summarize(records)
        summary["selected"] = len(records)
        summary["deselected"] = getattr(cfg, "framework_deselected_count", 0)

        out_dir = cfg.getoption("--report-dir")
        if not os.path.isabs(out_dir):
            out_dir = os.path.join(str(cfg.rootpath), out_dir, str(meta['project']), str(meta['env']))
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.fromtimestamp(self.started).strftime("%Y%m%d_%H%M%S")
        name = f"{str(meta['project']).upper()}_{str(meta['env']).upper()}_{stamp}.html"
        self.report_path = os.path.join(out_dir, name)
        document = build_html(meta, summary, records)
        for path in (self.report_path, os.path.join(out_dir, "latest_report.html")):
            write_html(path, document)
        write_json(os.path.join(out_dir, "summary.json"), {
            "meta": {k: v for k, v in meta.items() if k not in ("warnings", "plan_warnings")},
            "summary": summary})

        # Expand records into station-specific views without changing the original result.
        import copy
        station_reports = {}
        base = os.path.splitext(self.report_path)[0]
        requested = getattr(cfg, "framework_stations_requested", [])
        for station in requested or list(dict.fromkeys(r.airport for r in records)):
            subset=[]
            for record in records:
                mapped=getattr(record, "stations", [record.airport])
                if station in mapped or "ALL" in mapped or (len(mapped)==1 and mapped[0]==station):
                    clone=copy.copy(record); clone.airport=station; subset.append(clone)
            if not subset:
                continue
            station_meta = dict(meta, airports=station, title=f"{meta['title']} - {station}", duration=sum(r.duration for r in subset))
            station_file = os.path.join(out_dir, f"{station}_Report.html")
            station_reports[station] = station_file
            station_summary=summarize(subset)
            station_summary["selected"]=len(subset)
            station_summary["deselected"]=getattr(cfg, "framework_deselected_count", 0)
            station_doc = build_html(station_meta, station_summary, subset)
            write_html(station_file, station_doc)
            write_html(f"{base}_{station}.html", station_doc)

        if not cfg.getoption("--no-email"):
            from utils.email_sender import EmailSender
            try:
                sender = EmailSender()
                sender.send_session_report(
                    meta=meta,
                    records=records,
                    station_reports=station_reports,
                    consolidated_report=self.report_path,
                )
            except Exception as error:
                self.framework_warnings.append(f"E-mail delivery failed: {type(error).__name__}: {error}")
                print(f"\n[report] E-mail delivery problem: {type(error).__name__}: {error}")

    def pytest_terminal_summary(self, terminalreporter):
        if self.report_path:
            terminalreporter.write_sep("-", "HTML report")
            terminalreporter.write_line(self.report_path)


# --------------------------------------------------------------------------- summary
def summarize(records) -> dict:
    result = {"total": len(records), "passed": 0, "failed": 0, "skipped": 0, "warnings": 0,
              "errors_logged": 0, "airports": {}}
    for r in records:
        result[r.group] += 1
        result["warnings"] += r.warnings
        result["errors_logged"] += r.errors
        a = result["airports"].setdefault(r.airport, {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
        a["total"] += 1
        a[r.group] += 1
    result["pass_rate"] = round(100 * result["passed"] / result["total"], 1) if result["total"] else 0
    return result


# --------------------------------------------------------------------------- ExtentReports 2.41.1
def _e(value) -> str:
    return html.escape(str(value), quote=True)


def _format_duration(seconds: float) -> str:
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


def _clean_test_name(name: str) -> str:
    clean = re.sub(r"\[.*?\]$", "", str(name or "")).strip()
    return clean or str(name or "")


def _clean_error_message(error: str) -> str:
    """Extract clean error detail without dumping Python code, tracebacks, or objects."""
    if not error:
        return ""
    text = str(error).strip()
    if not text:
        return ""
    # Strip Python object reprs
    text = re.sub(r"<[a-zA-Z_][\w.]*\s+object\s+at\s+0x[0-9a-fA-F]+>", "", text)
    text = re.sub(r"<Page\s+url=[^>]+>", "", text)
    text = re.sub(r"<Locator\s+frame=[^>]+>", "", text)

    m_delay = re.search(r"Delay Time in ms:\s*\d+", text)
    if m_delay:
        return m_delay.group(0)

    for pattern in (
        r"AssertionError:\s*([^\r\n]+)",
        r"(Locator expected\s+[^\r\n]+)",
        r"TimeoutError:\s*([^\r\n]+)",
        r"Exception:\s*([^\r\n]+)",
        r"Error:\s*([^\r\n]+)",
    ):
        m = re.search(pattern, text)
        if m:
            clean = m.group(1).replace("AssertionError:", "").strip()
            return clean[:150]

    lines = [
        l.strip()
        for l in text.splitlines()
        if l.strip() and not l.strip().startswith(("Traceback", "File ", "at ", "E   ", "+", "-"))
    ]
    if lines:
        return lines[-1][:150]
    return "Test execution failure"


def _clean_log_text(msg: str) -> str:
    """Clean log message of raw Python objects, Base64 strings, and internal noise."""
    if not msg:
        return ""
    s = str(msg).strip()
    s = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{50,}", "[IMAGE_DATA]", s)
    s = re.sub(r"<[a-zA-Z_][\w.]*\s+object\s+at\s+0x[0-9a-fA-F]+>", "", s)
    s = re.sub(r"<Page\s+url=[^>]+>", "", s)
    s = re.sub(r"<Locator\s+frame=[^>]+>", "", s)
    return s.strip()


def build_html(meta: dict, summary: dict, records) -> str:
    """Generate ExtentReports 2.41.1 format report."""
    import uuid

    template_file = Path(__file__).resolve().parent / "extent_template.html"
    if not template_file.is_file():
        raise FileNotFoundError(f"ExtentReports template not found: {template_file}")

    template = template_file.read_text(encoding="utf-8")

    started_val = meta.get("started")
    if isinstance(started_val, (int, float)):
        started_dt = datetime.fromtimestamp(started_val)
    else:
        try:
            started_dt = datetime.strptime(str(started_val), "%d %b %Y %H:%M:%S")
        except Exception:
            started_dt = datetime.now()

    started_str = started_dt.strftime("%Y-%m-%d %H:%M:%S")
    ended_dt = datetime.now()
    ended_str = ended_dt.strftime("%Y-%m-%d %H:%M:%S")
    total_duration_str = _format_duration(meta.get("duration", 0.0))

    user_name = os.getenv("USERNAME") or os.getenv("USER") or "avileap"
    os_name = platform.system()
    python_version = platform.python_version()
    host_name = platform.node()
    project = str(meta.get("project", "FLYDUBAI")).upper()
    env = str(meta.get("env", "QA")).upper()
    airport_default = str(meta.get("airports", "DEL")).upper()

    test_items = []
    category_rows = []

    pass_count = summary.get("passed", 0)
    fail_count = summary.get("failed", 0)
    other_count = summary.get("skipped", 0)

    now_ts = datetime.now().timestamp()
    for r in records:
        test_id = str(uuid.uuid4())
        name = _clean_test_name(getattr(r, "name", "Unknown Test"))
        st_raw = str(getattr(r, "status", "PASSED")).upper()
        if st_raw in ("FAILED", "ERROR"):
            status = "fail"
        elif st_raw == "SKIPPED":
            status = "skip"
        else:
            status = "pass"

        rec_start = getattr(r, "start", 0.0)
        if not rec_start or rec_start < 86400:
            rec_start = now_ts
        rec_dur = max(float(getattr(r, "duration", 0.0) or 0.0), 0.0)
        rec_start_dt = datetime.fromtimestamp(rec_start)
        rec_end_dt = datetime.fromtimestamp(rec_start + rec_dur)

        r_start_str = rec_start_dt.strftime("%Y-%m-%d %H:%M:%S")
        r_end_str = rec_end_dt.strftime("%Y-%m-%d %H:%M:%S")
        r_dur_str = _format_duration(rec_dur)
        r_start_clock = rec_start_dt.strftime("%H:%M:%S")
        r_end_clock = rec_end_dt.strftime("%H:%M:%S")

        rec_airport = getattr(r, "airport", airport_default)
        if not rec_airport or rec_airport == "-":
            rec_airport = airport_default

        step_rows = []
        # Step 1: Airport and Environment header block
        step_rows.append(f"""<tr>
	<td class='status info' title='info' alt='info'><i class='mdi-action-info-outline'></i></td>
	<td class='timestamp'>{r_start_clock}</td>
	<td class='step-details'><h5 align="center" style="color:#008ae6;margin:4px 0;font-weight:600;">Airport: {_e(rec_airport)} &nbsp;|&nbsp; Environment: {_e(env)}</h5></td>
</tr>""")

        used_screenshot_names = set()
        has_failed_step = False

        # Sequential test steps if recorded via allure.step / rc.step
        steps_list = getattr(r, "steps", None)
        if steps_list:
            for step_obj in steps_list:
                s_time = datetime.fromtimestamp(getattr(step_obj, "start", rec_start)).strftime("%H:%M:%S")
                s_name = _e(getattr(step_obj, "name", ""))
                s_status = getattr(step_obj, "status", "passed")
                if s_status == "failed":
                    has_failed_step = True
                    err_msg = _clean_error_message(getattr(step_obj, "error", "") or getattr(r, "error", ""))
                    step_shots = getattr(step_obj, "screenshots", []) or r.screenshots
                    shots_markup = ""
                    for s in step_shots:
                        used_screenshot_names.add(s.name)
                        shots_markup += f"<div style='margin-top:8px;'><a href='data:{s.mime};base64,{s.data_b64}' data-featherlight='image'><img class='report-img' src='data:{s.mime};base64,{s.data_b64}' alt='Failure Screenshot' /></a></div>"
                    if not shots_markup:
                        shots_markup = "<div style='color:#888;font-size:12px;margin-top:4px;'>[Screenshot not available]</div>"

                    fail_desc = f"{s_name} - {_e(err_msg)}" if err_msg else s_name
                    step_rows.append(f"""<tr>
	<td class='status fail' title='fail' alt='fail'><i class='mdi-navigation-cancel'></i></td>
	<td class='timestamp'>{s_time}</td>
	<td class='step-details'><span class='fail label'>Fail</span> <span style='color:red;margin-left: 10px;font-weight:600;'>{fail_desc}</span>{shots_markup}</td>
</tr>""")
                else:
                    step_rows.append(f"""<tr>
	<td class='status info' title='info' alt='info'><i class='mdi-action-info-outline'></i></td>
	<td class='timestamp'>{s_time}</td>
	<td class='step-details'>{s_name}</td>
</tr>""")

        # If no steps were recorded via allure.step, display meaningful logs from test execution
        else:
            for l in getattr(r, "logs", []):
                msg = _clean_log_text(l.message)
                if not msg:
                    continue
                if any(p in msg for p in ("TEST START |", "TEST TEARDOWN |", "ACTION start |", "ACTION success |")):
                    continue
                l_time = datetime.fromtimestamp(l.ts).strftime("%H:%M:%S")
                l_status = "warning" if l.level == "WARNING" else ("fail" if l.level in ("ERROR", "CRITICAL") else "info")
                l_icon = "mdi-alert-warning" if l.level == "WARNING" else ("mdi-navigation-cancel" if l_status == "fail" else "mdi-action-info-outline")
                step_rows.append(f"""<tr>
	<td class='status {l_status}' title='{l_status}' alt='{l_status}'><i class='{l_icon}'></i></td>
	<td class='timestamp'>{l_time}</td>
	<td class='step-details'>{_e(msg)}</td>
</tr>""")

        # If test status is fail but no failed step was rendered above, render failure details with screenshot
        if status == "fail" and not has_failed_step:
            err_msg = _clean_error_message(getattr(r, "error", ""))
            shots_markup = "".join(
                f"<div style='margin-top:8px;'><a href='data:{s.mime};base64,{s.data_b64}' data-featherlight='image'><img class='report-img' src='data:{s.mime};base64,{s.data_b64}' alt='Failure Screenshot' /></a></div>"
                for s in getattr(r, "screenshots", [])
            )
            if not shots_markup:
                shots_markup = "<div style='color:#888;font-size:12px;margin-top:4px;'>[Screenshot not available]</div>"
            step_rows.append(f"""<tr>
	<td class='status fail' title='fail' alt='fail'><i class='mdi-navigation-cancel'></i></td>
	<td class='timestamp'>{r_end_clock}</td>
	<td class='step-details'><span class='fail label'>Fail</span> <span style='color:red;margin-left: 10px;font-weight:600;'>{_e(err_msg or 'Execution Failure')}</span>{shots_markup}</td>
</tr>""")

        # Final status badge
        if status == "pass":
            step_rows.append(f"""<tr>
	<td class='status pass' title='pass' alt='pass'><i class='mdi-action-check-circle'></i></td>
	<td class='timestamp'>{r_end_clock}</td>
	<td class='step-details'><span class='pass label'>Pass</span></td>
</tr>""")
        elif status == "skip":
            skip_msg = _e(str(getattr(r, "skip_reason", "") or "Skipping this test"))
            step_rows.append(f"""<tr>
	<td class='status skip' title='skip' alt='skip'><i class='mdi-content-redo'></i></td>
	<td class='timestamp'>{r_end_clock}</td>
	<td class='step-details'><span class='skip label'>Skip</span> <span style='color:orange;margin-left: 10px'>{skip_msg}</span></td>
</tr>""")

        test_item_html = f"""<li class='collection-item test displayed active {status} ' extentid='{test_id}'>
	<div class='test-head'>
		<span class='test-name'>{_e(name)} </span>
		<span class='test-status label right outline capitalize {status}'>{status}</span>
		<span class='category-assigned hide  sanity'></span>
	</div>
	<div class='test-body'>
		<div class='test-info'>
			<span title='Test started time' alt='Test started time' class='test-started-time label green lighten-1 text-white'>{r_start_str}</span>
			<span title='Test ended time' alt='Test ended time' class='test-ended-time label red lighten-1 text-white'>{r_end_str}</span>
			<span title='Time taken to finish' alt='Time taken to finish' class='test-time-taken label blue-grey lighten-3 text-white'>{r_dur_str}</span>
		</div>
		<div class='test-desc'></div>
		<div class='test-attributes'>
				<div class='categories'>
						<span class='category text-white'>sanity</span>
				</div>
		</div>
		<div class='test-steps'>
			<table class='bordered table-results'>
				<thead>
					<tr>
						<th>Status</th>
						<th>Timestamp</th>
						<th>Details</th>
					</tr>
				</thead>
				<tbody>
						{''.join(step_rows)}
				</tbody>
			</table>
			<ul class='collapsible node-list' data-collapsible='accordion'>
			</ul>
		</div>
	</div>
</li>"""
        test_items.append(test_item_html)

        category_rows.append(f"""<tr class='{status}'>
	<td>{r_start_str}</td>
	<td><span class='category-link linked' extentid='{test_id}'>{_e(name)}</span></td>
	<td><div class='status label capitalize {status}'>{status}</div></td>
</tr>""")

    category_html = f"""<li class='category-item displayed'>
	<div class='cat-head'>
		<span class='category-name'>sanity</span>
	</div>
	<div class='category-status-counts'>
			<span class='fail label dot'>Fail: {fail_count}</span>
			<span class='pass label dot'>Pass: {pass_count}</span>
	</div>
	<div class='cat-body'>
		<div class='category-status-counts'>
			<div class='button-group'>
				<a href='#!' class='pass label filter'>Pass <span class='icon'>{pass_count}</span></a>
				<a href='#!' class='fail label filter'>Fail <span class='icon'>{fail_count}</span></a>
				<a href='#!' class='other label filter'>Others <span class='icon'>{other_count}</span></a>
			</div>
		</div>
		<div class='cat-tests'>
			<table class='bordered'>
				<thead>
					<tr>
						<th>RunDate</th>
						<th>Test Name</th>
						<th>Status</th>
					</tr>
				</thead>
				<tbody>
						{''.join(category_rows)}
				</tbody>
			</table>
		</div>
	</div> 
</li>"""

    doc = (template
           .replace("{{STARTED_TIME}}", started_str)
           .replace("{{ENDED_TIME}}", ended_str)
           .replace("{{TOTAL_DURATION}}", total_duration_str)
           .replace("{{USER_NAME}}", _e(user_name))
           .replace("{{OS_NAME}}", _e(os_name))
           .replace("{{PYTHON_VERSION}}", _e(python_version))
           .replace("{{HOST_NAME}}", _e(host_name))
           .replace("{{PROJECT}}", _e(project))
           .replace("{{ENV}}", _e(env))
           .replace("{{TEST_COLLECTION}}", "\n".join(test_items))
           .replace("{{CATEGORY_ITEMS}}", category_html)
    )
    return doc