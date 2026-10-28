"""Reusable contextual logging with console and per-run file output."""
from __future__ import annotations
import logging, os, re
from pathlib import Path

_CONFIGURED=False

def configure_logging(project='unknown', env='unknown', station='unknown', log_dir='logs', level=None):
    global _CONFIGURED
    root=logging.getLogger()
    chosen=(level or os.getenv('LOG_LEVEL','INFO')).upper()
    root.setLevel(getattr(logging,chosen,logging.INFO))
    if _CONFIGURED and root.handlers: return
    formatter=logging.Formatter('%(asctime)s | %(levelname)s | project=%(project)s | env=%(env)s | station=%(station)s | %(name)s | %(message)s', '%Y-%m-%d %H:%M:%S')
    class ContextFilter(logging.Filter):
        def filter(self, record):
            record.project=getattr(record,'project',project); record.env=getattr(record,'env',env)
            current_station=station
            try:
                from utils.report_context import get_current
                current=get_current()
                if current is not None: current_station=getattr(current,'airport',station)
            except Exception: pass
            record.station=getattr(record,'station',current_station); return True
    log_path=Path(log_dir)/project/env/station
    log_path.mkdir(parents=True,exist_ok=True)
    for handler in (logging.StreamHandler(), logging.FileHandler(log_path/'execution.log',encoding='utf-8')):
        handler.setFormatter(formatter); handler.addFilter(ContextFilter()); root.addHandler(handler)
    _CONFIGURED=True

def get_logger(name=__name__):
    return logging.getLogger(name)

def safe_name(value):
    return re.sub(r'[^A-Za-z0-9_.-]+','_',str(value)).strip('_') or 'unknown'
