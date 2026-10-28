"""Excel-driven execution and test selection.

Reads Execution_Config for run parameters (Project, Environment, Station, Station_Name)
and Test_Cases for test enablement and station mappings.
Credentials (URL, Username, Password) are mapped dynamically from .env using <PROJECT>_<ENV>_*.
"""
from __future__ import annotations
from pathlib import Path
import re
from typing import Any
import pytest
from utils.excel_reader import ExcelReader
from utils.settings import truthy

REQUIRED = {
    'Execution_Config': {'Project', 'Environment', 'Station', 'Enabled'},
    'Test_Cases': {'TestCase_ID', 'Project', 'TestCase_Name', 'Station', 'Enabled'},
}


def _norm(v: Any) -> str:
    return str(v or '').strip()


def _yes(v: Any) -> bool:
    return truthy(v, default=False)


def _parse_stations(station_str: Any) -> list[str]:
    """Parse comma-separated station codes (e.g. 'DXB, DWC' -> ['DXB', 'DWC'])."""
    raw = [s.strip().upper() for s in str(station_str or '').split(',') if s.strip()]
    return raw if raw else ['ALL']


def load_workbook_config(path: str):
    p = Path(path)
    if not p.exists():
        raise pytest.UsageError(f'Execution workbook not found: {p}')
    reader = ExcelReader(str(p))
    try:
        available_sheets = reader.get_sheet_names()
        sheets = {}
        for sheet, cols in REQUIRED.items():
            if sheet not in available_sheets:
                raise pytest.UsageError(f"Required sheet {sheet!r} not found in {path}.")
            data = reader.read_sheet(sheet)
            if not data:
                raise pytest.UsageError(f'Excel worksheet {sheet!r} is empty.')
            headers = set(data[0].keys())
            missing = cols - headers
            if missing:
                raise pytest.UsageError(f'Worksheet {sheet!r} is missing columns: {sorted(missing)}')
            sheets[sheet] = data

        # 1. Parse Execution_Config
        stations = {}
        active_exec = []
        for r in sheets['Execution_Config']:
            proj = _norm(r.get('Project')).lower()
            env = _norm(r.get('Environment')).lower()
            station = _norm(r.get('Station')).upper()
            station_name = _norm(r.get('Station_Name') or station)
            enabled = _yes(r.get('Enabled'))

            if not all((proj, env, station)):
                raise pytest.UsageError(f'Execution_Config row has blank Project, Environment, or Station: {r}')

            key = (proj, station)
            stations[key] = (station_name, enabled)
            if enabled:
                active_exec.append({**r, 'Project': proj, 'Environment': env, 'Station': station, 'Station_Name': station_name, 'Enabled': True})

        if not active_exec:
            raise pytest.UsageError('Execution_Config sheet has no enabled rows (Enabled=Yes).')

        # 2. Parse Test_Cases
        cases = []
        seen = set()
        for r in sheets['Test_Cases']:
            project = _norm(r.get('Project')).lower()
            name = _norm(r.get('TestCase_Name'))
            tcid = _norm(r.get('TestCase_ID'))
            station_raw = _norm(r.get('Station')).upper()

            if not all((project, name, tcid, station_raw)):
                raise pytest.UsageError(f'Test_Cases row has blank Project, TestCase_Name, TestCase_ID, or Station: {r}')

            station_list = _parse_stations(station_raw)
            for st in station_list:
                if st != 'ALL':
                    if not re.fullmatch(r'[A-Z0-9_-]{2,10}', st):
                        raise pytest.UsageError(f'Invalid Station code {st!r} in {station_raw!r}; use 2-10 alphanumeric characters.')
                    if (project, st) not in stations:
                        stations[(project, st)] = (st, True)

            key = (project, tcid)
            if key in seen:
                raise pytest.UsageError(f'Duplicate Test_Cases mapping for TestCase_ID {tcid!r} in project {project!r}.')
            seen.add(key)

            try:
                enabled = _yes(r.get('Enabled'))
            except ValueError as exc:
                raise pytest.UsageError(f'Invalid Enabled value in Test_Cases row {r}: {exc}') from exc

            cases.append({
                **r,
                'Project': project,
                'TestCase_Name': name,
                'TestCase_ID': tcid,
                'Station': station_raw,
                'Station_List': station_list,
                'Enabled': enabled,
            })

        # 3. Validation: Verify that each enabled station in Execution_Config explicitly exists in Test_Cases
        for exec_row in active_exec:
            e_proj = exec_row['Project']
            e_station = exec_row['Station']
            if e_station != 'ALL':
                exists = any(
                    c['Project'] == e_proj and e_station in c['Station_List']
                    for c in cases
                )
                if not exists:
                    raise pytest.UsageError(
                        f"Station {e_station!r} defined in Execution_Config for project {e_proj!r} does not exist in the Test_Cases sheet."
                    )

        return sheets, stations, cases
    finally:
        reader.close()


def pytest_addoption(parser):
    group = parser.getgroup('framework')
    existing_opts = set()
    for opt in getattr(parser._anonymous, 'options', []):
        existing_opts.update(opt.names())
    for grp in getattr(parser, '_groups', []):
        for opt in getattr(grp, 'options', []):
            existing_opts.update(opt.names())

    def _safe_add(*names, **kwargs):
        if not any(name in existing_opts for name in names):
            group.addoption(*names, **kwargs)

    _safe_add('--project', action='store', default='flydubai', help='Project name; defaults to Execution_Config in Excel.')
    _safe_add('--env', action='store', default='qa', help='Environment (qa, prod); defaults to Execution_Config in Excel.')
    _safe_add('--station', action='store', default='DXB', help='Station code; defaults to Execution_Config in Excel.')
    _safe_add('--browser', action='store', default='chromium', help='Browser to use for tests (chromium, firefox, webkit); defaults to Execution_Config in Excel.')
    _safe_add('--headless', action='store_true', default='True', help='Run browser in headless mode; defaults to Execution_Config in Excel.')
    _safe_add('--headed', action='store_false', dest='headless', default=None, help='Override Excel and run with a visible browser.')
    _safe_add('--no-email', action='store_true', default=False, help='Disable report email delivery for this run.')
    _safe_add('--execution-config', action='store', default='test_data/execution_config.xlsx', help='Path to the Excel file containing execution configuration.')


def pytest_configure(config):
    path = config.getoption('--execution-config')
    if not Path(path).is_absolute():
        path = str(Path(config.rootpath) / path)
    sheets, stations, cases = load_workbook_config(path)

    # Resolve project, env, station: CLI flags override Execution_Config defaults
    active_exec = [r for r in sheets['Execution_Config'] if _yes(r.get('Enabled'))]
    default_exec = active_exec[0] if active_exec else {}

    cli_project = config.getoption('--project')
    project = (cli_project or default_exec.get('Project', 'flydubai')).strip().lower()

    cli_env = config.getoption('--env')
    env = (cli_env or default_exec.get('Environment', 'qa')).strip().lower()

    cli_station = config.getoption('--station')
    station_str = (cli_station or default_exec.get('Station', 'DXB')).strip()
    requested = [s.strip().upper() for s in station_str.split(',') if s.strip()]

    # Populate resolved values back to config options for downstream fixtures & plugins
    config.option.project = project
    config.option.env = env
    config.option.station = station_str

    if not requested:
        raise pytest.UsageError('--station must contain at least one station code.')

    known = {code for (proj, code), (name, enabled) in stations.items() if proj == project and enabled}
    if requested == ['ALL']:
        requested = sorted(known) if known else ['ALL']
    else:
        if known:
            unknown = [s for s in requested if s != 'ALL' and s not in known]
            if unknown:
                raise pytest.UsageError(f'Unknown station(s) for {project}: {unknown}; known enabled stations: {sorted(known)}')

    # Filter active cases
    active = [
        r for r in cases
        if r['Project'] == project and r['Enabled'] and (
            'ALL' in r['Station_List'] or any(st in requested for st in r['Station_List'])
        )
    ]
    if not active:
        raise pytest.UsageError(f'No enabled test mappings for project={project}, station={requested}.')

    config.framework_sheets = sheets
    config.framework_stations = stations
    config.framework_cases = active
    config.framework_project = project
    config.framework_env = env
    config.framework_stations_requested = requested
    config.framework_selected_names = {v.lower() for r in active for v in (r['TestCase_Name'], r['TestCase_ID'])}
    config.addinivalue_line('markers', 'tc(id): optional test case ID')
    config.addinivalue_line('markers', 'station(code): station-specific test')


def pytest_generate_tests(metafunc):
    """Repeat station-aware tests once per mapped station when they request the station fixture."""
    if 'station' not in metafunc.fixturenames:
        return
    config = metafunc.config
    name = metafunc.function.__name__.lower()
    tc_marker = metafunc.definition.get_closest_marker('tc')
    aliases = {name, metafunc.definition.nodeid.lower(), metafunc.definition.nodeid.split('[', 1)[0].lower()}
    if tc_marker and tc_marker.args:
        aliases.add(str(tc_marker.args[0]).lower())

    mappings = [r for r in config.framework_cases if r['TestCase_Name'].lower() in aliases or r['TestCase_ID'].lower() in aliases]
    station_values = set()
    for row in mappings:
        st_list = row.get('Station_List') or _parse_stations(row['Station'])
        if 'ALL' in st_list:
            station_values.update(config.framework_stations_requested)
        else:
            for st in st_list:
                if st in config.framework_stations_requested:
                    station_values.add(st)
    if station_values:
        values = sorted(station_values, key=config.framework_stations_requested.index)
        metafunc.parametrize('station', values, ids=values)


def pytest_collection_modifyitems(config, items):
    project = config.framework_project
    selected = config.framework_selected_names
    requested = set(config.framework_stations_requested)
    keep = []
    deselected = []
    mapping_by_name = {}
    for r in config.framework_cases:
        st_list = set(r.get('Station_List') or _parse_stations(r['Station']))
        for alias in (r['TestCase_Name'].lower(), r['TestCase_ID'].lower()):
            mapping_by_name.setdefault(alias, set()).update(st_list)

    for item in items:
        # Match by node ID, function name, or explicit TC marker. Avoid loose substring matching.
        names = {item.name.lower(), item.originalname.lower(), item.nodeid.lower(), item.nodeid.split('[', 1)[0].lower()}
        marker = item.get_closest_marker('tc')
        if marker and marker.args:
            names.add(str(marker.args[0]).lower())
        candidates = [n for n in selected if n in names]
        if not candidates:
            deselected.append(item)
            continue
        configured_stations = set().union(*(mapping_by_name.get(n, set()) for n in candidates))
        if not ('ALL' in configured_stations or configured_stations.intersection(requested)):
            deselected.append(item)
            continue
        item.user_properties.append(('project', project))
        applicable = (configured_stations & requested) if 'ALL' not in configured_stations else requested
        item.user_properties.append(('stations', ','.join(sorted(applicable or requested))))
        keep.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = keep
    config.framework_deselected_count = len(deselected)
    if not keep:
        raise pytest.UsageError('Excel configuration selected zero collected tests. Check TestCase_Name against pytest function names or node IDs.')
