"""
Copy all data from the Postgres database in cargo_reports/settings.py into a fresh SQLite file.

    python postgres_to_sqlite.py                      # writes db.sqlite3 next to this file
    python postgres_to_sqlite.py path\to\new.sqlite3  # writes that file
    python postgres_to_sqlite.py --replace            # archive an existing db.sqlite3 to db_archive\ first
    python postgres_to_sqlite.py --dump-only          # only write the JSON, don't create SQLite

Steps:
  1. Dumps Postgres to backups\postgres_data_<time>.json (Postgres is only read).
  2. Creates the SQLite file and builds every table (migrate --run-syncdb, for apps without migrations).
  3. Loads the JSON into SQLite and compares row counts.

Run the app on the new file with:  set DB_ENGINE=sqlite  then  python manage.py runserver
"""
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cargo_reports.settings')
os.environ.setdefault('PYTHONUTF8', '1')

# Tables Django rebuilds itself on migrate; copying them causes duplicate-key errors.
SKIP = ['contenttypes', 'auth.permission', 'admin.logentry', 'sessions']


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dump_only = '--dump-only' in sys.argv
    replace = '--replace' in sys.argv
    target_file = Path(args[0]).resolve() if args else BASE_DIR / 'db.sqlite3'

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if target_file.exists() and not dump_only:
        if not replace:
            sys.exit(f'[ERROR] {target_file} already exists. Use --replace to archive it first, '
                     'or pass another file name.')
        archive = BASE_DIR / 'db_archive'
        archive.mkdir(exist_ok=True)
        moved = archive / f'{target_file.stem}_{stamp}{target_file.suffix}'
        shutil.move(str(target_file), moved)
        print(f'Archived {target_file} -> {moved}')

    backups = BASE_DIR / 'backups'
    backups.mkdir(exist_ok=True)
    fixture = backups / f'postgres_data_{stamp}.json'

    # Postgres is the source ("default") even when DB_ENGINE=sqlite is set; the new file is "sqlite".
    import cargo_reports.settings as project_settings
    project_settings.DATABASES = {
        'default': project_settings.POSTGRES_DB,
        'sqlite': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(target_file)},
    }

    import django
    django.setup()
    from django.apps import apps
    from django.core.management import call_command
    from django.db import connections

    source = connections['default'].settings_dict
    print(f'Source: Postgres database "{source["NAME"]}" on {source.get("HOST") or "localhost"}')

    # 1) Dump Postgres. IDs are kept, so links between tables stay the same.
    print(f'\nDumping Postgres data to {fixture} ...')
    excludes = [x for s in SKIP for x in ('--exclude', s)]
    call_command('dumpdata', *excludes, database='default', natural_foreign=True,
                 indent=2, output=str(fixture))
    print('[OK] Dump written.')
    if dump_only:
        return

    # 2) Build the empty SQLite tables. Account has no migrations folder, so --run-syncdb creates it.
    print(f'\nCreating {target_file} ...')
    call_command('migrate', database='sqlite', run_syncdb=True, interactive=False, verbosity=1)

    # 3) Load and check.
    print('Loading data into SQLite ...')
    call_command('loaddata', str(fixture), database='sqlite')

    print('\nRow counts (Postgres -> SQLite):')
    bad = 0
    for model in apps.get_models():
        if model._meta.label_lower in SKIP or model._meta.app_label in SKIP:
            continue
        before = model._default_manager.using('default').count()
        after = model._default_manager.using('sqlite').count()
        flag = '' if before == after else '   <-- DIFFERENT'
        bad += bool(flag)
        print(f'  {model._meta.label:35} {before:>7} -> {after:<7}{flag}')
    print('\n[OK] SQLite file ready: ' + str(target_file) if not bad else '\n[WARNING] Some counts differ, see above.')
    print('Run the app on it with:  set DB_ENGINE=sqlite')


if __name__ == '__main__':
    main()
