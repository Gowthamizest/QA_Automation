"""Validated project/environment and Excel-backed runtime settings."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from utils.excel_reader import ExcelReader

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def truthy(value: Any, *, default: bool = False) -> bool:
    if value is None or str(value).strip() == '':
        return default
    val = str(value).strip().lower()
    if val in {'yes', 'y', 'true', '1', 'on', 'enabled'}:
        return True
    if val in {'no', 'n', 'false', '0', 'off', 'disabled'}:
        return False
    raise ValueError(f'Invalid boolean value: {value!r}')


def split_list(value: Any) -> list[str]:
    return [v.strip() for v in str(value or '').split(',') if v.strip()]


class RuntimeConfig:
    def __init__(self, project: str | None = None, env: str | None = None, workbook: str | None = None):
        self.workbook = Path(workbook or os.getenv('EXECUTION_CONFIG', ROOT / 'test_data' / 'execution_config.xlsx'))
        if not self.workbook.is_absolute():
            self.workbook = ROOT / self.workbook

        # If project or env not passed via CLI, resolve from Execution_Config in Excel
        if (not project or not env) and self.workbook.exists():
            reader = ExcelReader(str(self.workbook))
            try:
                if 'Execution_Config' in reader.get_sheet_names():
                    rows = reader.read_sheet('Execution_Config')
                    active = [r for r in rows if truthy(r.get('Enabled'), default=False)]
                    if active:
                        if not project:
                            project = str(active[0].get('Project', '')).strip().lower()
                        if not env:
                            env = str(active[0].get('Environment', '')).strip().lower()
            finally:
                reader.close()

        self.project = (project or 'flydubai').strip().lower()
        self.env = (env or 'qa').strip().lower()
        if not self.project or not self.env:
            raise ValueError('Project and environment are required.')

        prefix = f'{self.project.upper()}_{self.env.upper()}'
        self.url = os.getenv(f'{prefix}_URL')
        self.username = os.getenv(f'{prefix}_USERNAME')
        self.password = os.getenv(f'{prefix}_PASSWORD')
        self.timeout_ms = int(os.getenv(f'{prefix}_TIMEOUT_MS', os.getenv('PLAYWRIGHT_TIMEOUT_MS', '60000')))
        if self.timeout_ms < 1:
            raise ValueError('Timeout must be positive.')
        if not self.url:
            raise ValueError(
                f"Configuration credentials missing in .env for PROJECT={self.project.upper()} ENV={self.env.upper()}.\n"
                f"Please ensure {prefix}_URL, {prefix}_USERNAME, and {prefix}_PASSWORD are defined in your .env file."
            )

    def execution_settings(self, station: str | None, cli_browser: str | None, cli_headless: bool | None) -> dict[str, Any]:
        settings = {'browser': cli_browser or 'chromium', 'headless': cli_headless if cli_headless is not None else False}
        if self.workbook.exists():
            reader = ExcelReader(str(self.workbook))
            try:
                if 'Execution_Config' in reader.get_sheet_names():
                    rows = reader.read_sheet('Execution_Config')
                    matches = [
                        r for r in rows
                        if str(r.get('Project', '')).strip().lower() == self.project
                        and str(r.get('Environment', '')).strip().lower() == self.env
                        and str(r.get('Station', 'ALL') or 'ALL').strip().upper() in {'ALL', (station or 'ALL').upper()}
                        and truthy(r.get('Enabled'), default=True)
                    ]
                    if matches:
                        row = matches[0]
                        if not cli_browser and row.get('Browser'):
                            settings['browser'] = str(row['Browser']).strip().lower()
                        if cli_headless is None and row.get('Headless') is not None:
                            settings['headless'] = truthy(row['Headless'])
            finally:
                reader.close()
        if settings['browser'] not in {'chromium', 'firefox', 'webkit'}:
            raise ValueError(f'Unsupported browser: {settings["browser"]}')
        return settings
