#!/usr/bin/env python3
import importlib.util
from pathlib import Path

module_path = Path('tools/database/create_overview_view.py').resolve()
spec = importlib.util.spec_from_file_location('create_overview_view', str(module_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod.DB_CONFIG = dict(
    host='ticketdb-ticket63.f.aivencloud.com',
    port=13599,
    user='avnadmin',
    password='AVNS_QqNVFqacdQinAgGmXY9',
    database='defaultdb',
    charset='utf8mb4',
    collation='utf8mb4_unicode_ci',
    autocommit=False,
    ssl_verify_cert=False,
    ssl_verify_identity=False,
)

if hasattr(mod, 'main'):
    mod.main()
else:
    print('no main')
