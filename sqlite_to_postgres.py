"""
Copy all data from db.sqlite3 into the Postgres database in cargo_reports/settings.py.

    python sqlite_to_postgres.py                  # uses db.sqlite3 next to this file
    python sqlite_to_postgres.py path\to\db.sqlite3
    python sqlite_to_postgres.py --dump-only      # only write the JSON, don't touch Postgres

Steps:
  1. Copies the SQLite file (the original is never changed).
  2. Adds to the copy any new nullable columns the current models expect
     (e.g. cashier.event_id), so the old data can be read.
  3. Dumps the copy to backups\sqlite_data_<time>.json. Models whose table
     does not exist in SQLite yet (e.g. Event, RemarksList, AuthRoute) are skipped.
  4. Runs migrate on Postgres, loads the JSON, and resets the ID sequences.

Postgres should be empty (freshly created). The script stops if it already has data.
"""
import os
import shutil
import sys
from datetime import datetime
from io import StringIO
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
    source = Path(args[0]).resolve() if args else BASE_DIR / 'db.sqlite3'
    if not source.exists():
        sys.exit(f'[ERROR] SQLite file not found: {source}')

    backups = BASE_DIR / 'backups'
    backups.mkdir(exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    work_copy = backups / f'sqlite_source_{stamp}.sqlite3'
    fixture = backups / f'sqlite_data_{stamp}.json'
    shutil.copy2(source, work_copy)
    print(f'Copied {source} -> {work_copy}')

    # Add a second database ("sqlite") next to the Postgres "default", before Django starts.
    import cargo_reports.settings as project_settings
    project_settings.DATABASES['sqlite'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(work_copy),
    }

    import django
    django.setup()
    from django.apps import apps
    from django.core.management import call_command
    from django.db import connections

    sqlite = connections['sqlite']
    skip = list(SKIP)

    # 1) Make the SQLite copy match the current models where that is safe.
    print('\nComparing models with the SQLite tables ...')
    tables = set(sqlite.introspection.table_names())
    problems = []
    with sqlite.cursor() as cur:
        for model in apps.get_models():
            meta = model._meta
            if meta.db_table not in tables:
                print(f'  skip {meta.label}: table "{meta.db_table}" not in SQLite (new model, no old data)')
                skip.append(meta.label)
                continue
            columns = {c.name for c in sqlite.introspection.get_table_description(cur, meta.db_table)}
            for field in meta.local_concrete_fields:
                if field.column in columns:
                    continue
                if field.null:
                    col_type = field.db_type(sqlite)
                    cur.execute(f'ALTER TABLE "{meta.db_table}" ADD COLUMN "{field.column}" {col_type} NULL')
                    print(f'  added empty column {meta.db_table}.{field.column} to the copy')
                else:
                    problems.append(f'{meta.label}.{field.name} ({meta.db_table}.{field.column})')
    if problems:
        sys.exit('[ERROR] These required (NOT NULL) columns are missing in SQLite; '
                 'add null=True or a default first:\n  ' + '\n  '.join(problems))

    # 2) Dump the copy. IDs are kept, so links between tables stay the same.
    print(f'\nDumping SQLite data to {fixture} ...')
    excludes = [x for s in skip for x in ('--exclude', s)]
    call_command('dumpdata', *excludes, database='sqlite', natural_foreign=True,
                 indent=2, output=str(fixture))
    print('[OK] Dump written.')
    if dump_only:
        return

    # 3) Load into Postgres.
    target = connections['default']
    print(f'\nTarget: {target.settings_dict["ENGINE"]} database "{target.settings_dict["NAME"]}" '
          f'on {target.settings_dict.get("HOST") or "localhost"}')
    print('Applying migrations on Postgres ...')
    call_command('migrate', database='default', interactive=False, verbosity=1)

    non_empty = [m._meta.label for m in apps.get_models()
                 if m._meta.label not in skip and m._default_manager.using('default').exists()]
    if non_empty:
        sys.exit('[ERROR] Postgres already has data in: ' + ', '.join(non_empty) +
                 '\n        Load into an empty database, or run: python manage.py loaddata ' + str(fixture))

    print('Loading data into Postgres ...')
    call_command('loaddata', str(fixture), database='default')

    # 4) loaddata keeps the old IDs, so move each ID counter past the highest ID.
    print('Resetting ID sequences ...')
    sql = StringIO()
    labels = sorted({m._meta.app_label for m in apps.get_models()})
    call_command('sqlsequencereset', *labels, database='default', stdout=sql, no_color=True)
    with target.cursor() as cur:
        cur.execute(sql.getvalue())

    # 5) Check: same number of rows on both sides.
    print('\nRow counts (SQLite -> Postgres):')
    bad = 0
    for model in apps.get_models():
        if model._meta.label in skip:
            continue
        before = model._default_manager.using('sqlite').count()
        after = model._default_manager.using('default').count()
        flag = '' if before == after else '   <-- DIFFERENT'
        bad += bool(flag)
        print(f'  {model._meta.label:35} {before:>7} -> {after:<7}{flag}')
    print('\n[OK] Import finished.' if not bad else '\n[WARNING] Some counts differ, see above.')
    print(f'You can delete the working copy: {work_copy}')


if __name__ == '__main__':
    main()
