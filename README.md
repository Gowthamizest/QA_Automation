# Playwright (Python) + Pytest Automation Framework

A page-object-based UI automation framework built with **Playwright -Python** and **pytest**. This document explains the folder structure, why each part exists, the naming conventions, and the best practices every contributor should follow.

## 1. Folder Structure at a Glance

project-root/  
│  
├── pages/ # Page Objects + Locators (one file per screen)  
│ ├── base_page.py # Browser init, browser actions, assertions  
│ ├── app_screen_page.py # &lt;App&gt;\_&lt;Screen&gt;\_page.py  
│ └── admin_access_management_page.py  
│  
├── tests/ # All test files live here  
│ ├── test_admin_access_management_user.py  
│ └── test_admin_access_management_user_xyz.py  
│  
├── test_data/ # Test data per app/screen  
│ ├── app_screen_test_data.py  
│ ├── \*.json  
│ ├── \*.txt  
│ ├── \*.csv  
│ └── \*.xlsx  
│  
├── utils/ # Reusable helpers (no page-specific logic)  
│ ├── common_methods.py  
│ ├── reports.py  
│ ├── email_utils.py  
│ ├── config.py  
│ └── excel_utils.py  
│  
├── reports/ # Generated output (HTML report, screenshots, logs)  
│ └── screenshots/  
│  
├── automation_control_sheet.xlsx # Controls which tests/suites are executed  
├── conftest.py # Fixtures, setup/teardown, configuration hooks  
├── pytest.ini # Retry, markers (tags), default options  
├── .env # URLs, credentials, email settings (NOT committed)  
├── .gitignore  
├── requirements.txt  
└── README.md

## 2. Folder / File Responsibilities

### 2.1 pages/ : Locators and Page Objects

**Purpose:** Holds one Page Object per application screen. Each class contains that screen's **locators** and the **methods** (user actions) that operate on them.

**Why it matters:** If the UI changes, only one file needs to be updated, not every test. Tests stay readable and free of selectors.

**Naming:** &lt;app&gt;\_&lt;screen&gt;\_page.py, e.g. app_screen_page.py, admin_accessmanagement_page.py.

**Inside each page file:**

1. **Header block** (author / created date / modified by / modified date)
2. **Locators** section, with clear comments describing which part of the screen each group belongs to
3. **Methods** section: actions and validations for that screen

"""  
Author : &lt;name&gt;  
Created On : &lt;dd-mm-yyyy&gt;  
Modified By : &lt;name&gt;  
Modified On : &lt;dd-mm-yyyy&gt;  
Description : Page object for Admin > Access Management screen  
"""  
from pages.base_page import BasePage  
<br/><br/>class AdminAccessManagementPage(BasePage):  
<br/>\# ------------------------------------------------------------------  
\# LOCATORS - User listing grid  
\# ------------------------------------------------------------------  
ADD_USER_BUTTON = "button\[data-testid='add-user'\]"  
SEARCH_INPUT = "input\[placeholder='Search user'\]"  
<br/>\# ------------------------------------------------------------------  
\# METHODS - User listing grid  
\# ------------------------------------------------------------------  
def click_add_user(self):  
self.click(self.ADD_USER_BUTTON)  
<br/>def search_user(self, name: str):  
self.fill(self.SEARCH_INPUT, name)

### 2.2 pages/base_page.py : The Foundation Class

**Purpose:** A single parent class that every page object inherits from. It wraps Playwright so that no test or page object calls raw Playwright APIs directly.

| Section                    | What it contains                                              |
| -------------------------- | ------------------------------------------------------------- |
| **Browser init**           | Browser / context / page initialisation and shared setup      |
| **Browser action methods** | open, click, hover, double_click, fill, select_dropdown, etc. |
| **Assertion methods**      | is_visible, is_enabled / clickable, is_text_present, etc.     |

**Why it matters:** Central place for waits, logging, retries and error handling. Improve it once and every page benefits.

### 2.3 tests/ : Test Folder

**Purpose:** Contains **all** test files. Nothing else (no helpers, no data) should live here.

**Naming:** test_&lt;appname&gt;\_&lt;screenname&gt;.py, e.g. test_admin_access_management_user.py. Variants for sub-features add a suffix: test_admin_access_management_user_xyz.py.

**Structure of every test file:**

1. **Header** (author, created, modified by, modified date)
2. **Scenario** description (what business flow the file covers)
3. **Test cases**, each decorated with markers (see section 4)

"""  
Author : &lt;name&gt;  
Created On : &lt;dd-mm-yyyy&gt;  
Modified By : &lt;name&gt;  
Modified On : &lt;dd-mm-yyyy&gt;  
"""  
import pytest  
from pages.admin_access_management_page import AdminAccessManagementPage  
<br/>\# Scenario: Admin creates, searches and deactivates a user  
<br/><br/>@pytest.mark.smoke  
@pytest.mark.regression  
def test_admin_can_search_user(page):  
access_page = AdminAccessManagementPage(page)  
access_page.search_user("john")  
assert access_page.is_visible(access_page.SEARCH_INPUT)

### 2.4 test_data/ : Test Data

**Purpose:** Keeps data separate from test logic so the same test can run with different data sets.

**Naming:** &lt;app&gt;\_&lt;screen&gt;\_test_data.py for Python data modules.

**Supported formats:** JSON, TXT, CSV, Excel.

| Format        | Best used for                                     |
| ------------- | ------------------------------------------------- |
| Python module | Small, static data and constants                  |
| JSON          | Structured / nested payloads                      |
| CSV / Excel   | Large data sets, data-driven (parametrised) tests |
| TXT           | Simple lists or free text inputs                  |

### 2.5 utils/ : Reusable Methods

**Purpose:** Generic helpers that are **independent of any particular screen**.

| File              | Responsibility                                                         |
| ----------------- | ---------------------------------------------------------------------- |
| common_methods.py | Shared helper functions (date handling, random data, string utilities) |
| reports.py        | Report generation and screenshot handling                              |
| email_utils.py    | Sending the execution report / summary by email                        |
| config.py         | Reads settings from .env and exposes them to the framework             |
| excel_utils.py    | Reading/writing Excel files (test data, control sheet)                 |

Rule of thumb: if it knows about a specific screen, it belongs in pages/. If it works anywhere, it belongs in utils/.

### 2.6 conftest.py : Fixtures, Setups and Configurations

**Purpose:** pytest's central hook file, auto-loaded before tests run.

Typical contents:

- Browser / context / page fixtures
- Login and logout setup/teardown
- Command-line options (e.g. --env, --browser, --headed)
- Hooks for screenshot-on-failure and report metadata

### 2.7 .env : Environment Configuration

**Purpose:** Holds environment-specific values that must **not** be hard-coded.

- List of application URLs (dev / QA / UAT)
- User ID / password for test accounts
- Email configuration (SMTP details, recipients)

BASE_URL=<https://qa.example.com>  
ADMIN_USER=admin_user  
ADMIN_PASSWORD=\*\*\*\*\*\*\*\*  
EMAIL_RECIPIENTS=<team@example.com>

**Never commit .env.** Add it to .gitignore and share a .env.example with placeholder values instead.

### 2.8 pytest.ini : Pytest Settings

**Purpose:** Project-level pytest configuration.

- **Retry** settings for flaky tests (e.g. via pytest-rerunfailures)
- **Markers (tags)** registration: smoke, regression, e2e
- Default CLI options, test paths and file-matching patterns

\[pytest\]  
testpaths = tests  
python_files = test_\*.py  
addopts = -v --reruns 1 --reruns-delay 2 --html=reports/report.html --self-contained-html  
markers =  
smoke: quick sanity checks on critical flows  
regression: full functional regression suite  
e2e: end-to-end business flow tests

### 2.9 reports/ : Execution Output

**Purpose:** Stores everything produced by a run: HTML report, screenshots of failures, logs.

- Reports can be published through **GitHub** (e.g. GitHub Actions artifacts / GitHub Pages)
- **Screenshots** are captured on failure and linked in the report
- Add reports/ to .gitignore for local runs

### 2.10 Automation Control Sheet

**Purpose:** An Excel sheet that controls _what_ gets executed: which tests or suites are enabled (Yes/No), their priority, and the target environment/browser, without touching code.

Suggested columns: Test ID | Test Name | Module | Marker | Run (Y/N) | Priority | Browser | Remarks

## 3. Naming Conventions

| Item                | Convention                                               | Example                                   |
| ------------------- | -------------------------------------------------------- | ----------------------------------------- |
| Page object file    | &lt;app&gt;\_&lt;screen&gt;\_page.py                     | admin_access_management_page.py           |
| Page object class   | PascalCase + Page                                        | AdminAccessManagementPage                 |
| Test file           | test_&lt;app&gt;\_&lt;screen&gt;\[\_&lt;feature&gt;\].py | test_admin_access_management_user.py      |
| Test function       | test_&lt;action&gt;\_&lt;expected_result&gt;             | test_admin_can_search_user_displayresults |
| Test data file      | &lt;app&gt;\_&lt;screen&gt;\_testdata.py                 | listview_ongoingsection_testdata.py       |
| Locator constants   | UPPER_SNAKE_CASE                                         | ADD_USER_BUTTON                           |
| Methods / functions | lower_snake_case, verb first                             | click_add_user()                          |
| Markers             | lowercase single word                                    | smoke, regression, e2e                    |

**Important:** pytest discovers files matching test_\*.py by default (lowercase). Using lowercase with underscores is recommended since it works on both Windows and Linux CI without surprises.

## 4. Markers (Tags)

Every test case must carry at least one marker so suites can be selected at run time.

| Marker     | Meaning                            | When to run                                         |
| ---------- | ---------------------------------- | --------------------------------------------------- |
| smoke      | Critical-path sanity checks        | **Daily**, and on every build deployment            |
| regression | Complete functional coverage       | **Twice weekly**, and whenever a new build deployed |
| e2e        | Full business flows across modules | **On demand**, before each release                  |

pytest -m smoke  
pytest -m "regression and not e2e"  
pytest tests/test_admin_access_management_user.py -m smoke

## 5. File Header and Comment Standard

Every file in pages/ and tests/ starts with a header:

"""  
Author : &lt;name&gt;  
Created On : &lt;dd-mm-yyyy&gt;  
Modified By : &lt;name&gt;  
Modified On : &lt;dd-mm-yyyy&gt;  
Description : &lt;one-line purpose&gt;  
"""

Then:

- **Add proper and clear comments for each section** (locator groups, method groups, scenario blocks).
- Update **Modified By / Modified On** whenever you change the file.

## 6. Best Practices

### Design

1. **Page Object Model:** tests never contain locators; pages never contain assertions about business outcomes.
2. **Inherit from BasePage:** never call raw Playwright APIs from tests.
3. **One responsibility per file:** pages for UI, utils for helpers, tests for scenarios.
4. **Keep tests independent:** each test sets up and cleans up its own data; no test should rely on another test's outcome.

### Locators

5. Prefer stable, user-facing locators: get_by_role, get_by_label, get_by_test_id, then CSS. Avoid long XPath and index-based selectors.
6. Group locators by screen section and comment each group.
7. Never duplicate a locator. Define once in the page object and reuse.

### Waiting and Stability

8. Rely on Playwright's **auto-waiting**; avoid time.sleep().
9. Use web-first assertions (expect(locator).to_be_visible()) instead of manual checks.
10. Use retries only for genuine flakiness, and investigate the root cause rather than hiding it.

### Data and Configuration

11. No hard-coded URLs, credentials or test data in code. Use .env and test_data/.
12. Never commit secrets. Use CI secrets for pipelines.
13. Prefer pytest.mark.parametrize for data-driven tests.

### Tests

14. Give every test a clear, behaviour-describing name and at least one marker.
15. One logical verification focus per test; keep tests short and readable.
16. Add meaningful assertion messages so failures are self-explanatory.
17. Capture a **screenshot (and optionally a trace/video) on failure**.

### Code Quality

18. Follow PEP 8; use a formatter/linter (black, ruff / flake8).
19. Review all framework changes via pull requests.
20. Keep requirements.txt pinned and updated.

### Execution and Reporting

21. Run suites as per the defined frequency in automation plan
22. Run in parallel where tests are independent (pytest-xdist).
23. Publish reports from CI and email a summary using utils/email_utils.py.
24. Maintain the **Automation Control Sheet** so execution scope is visible and controlled.

## 7. Getting Started

\# 1. Create and activate a virtual environment  
python -m venv venv  
source venv/bin/activate # Windows: venv\\Scripts\\activate  
<br/>\# 2. Install dependencies  
pip install -r requirements.txt  
playwright install  
<br/>\# 3. Configure environment  
cp .env.example .env # then fill in real values  
<br/>\# 4. Run tests  
pytest -m smoke  
pytest -m regression --headed  
pytest -n 4 # parallel run (pytest-xdist)

Suggested requirements.txt:

playwright  
pytest  
pytest-playwright  
pytest-html  
pytest-rerunfailures  
pytest-xdist  
python-dotenv  
openpyxl

## 8. Adding a New Screen: Checklist

- ☐ Create pages/&lt;app&gt;\_&lt;screen&gt;\_page.py with header, commented locators and methods
- ☐ Add test data in test_data/&lt;app&gt;\_&lt;screen&gt;\_test_data.py (or JSON/CSV/Excel)
- ☐ Create tests/test_&lt;app&gt;\_&lt;screen&gt;.py with header, scenario comment and marked test cases
- ☐ Add any new shared helpers to utils/ (only if screen-independent)
- ☐ Register new markers in pytest.ini if required
- ☐ Add the new tests to the Automation Control Sheet
- ☐ Raise a pull request for review

