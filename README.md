# COP CarGo App

A Django web app for managing **CarGo** trips: leaders log the vehicles and passengers they bring to a campus service or event, pastors approve them, and finance/accounting release the transport subsidy based on a fare matrix.

## Roles

Every user is an `Account.UserType` (email login, no username) with one of these types:

| Code   | Role       | What they do |
|--------|------------|--------------|
| `LE`   | Leader     | Registers, then submits trip entries (vehicle, plate no., passengers, campus, service schedule, event) |
| `PTR`  | Pastor     | Approves or rejects trip entries and new leader accounts for their campus |
| `FI`   | Finance    | Cashier view: verifies vouchers, sets the released amount, adds remarks |
| `ACNT` | Accountant | Accounting dashboard: reviews entries, exports to Excel, adds remarks |

After login, users are sent to the landing page for their type. Those routes are stored in the `AuthRoute` table (default data in `backup/auth_routes.json`).

## Main features

- **Trip entry form** (`/trip/`). Picking a campus loads that campus's service schedules and its active events. The top event is selected by default.
- **Events**, which can be tied to one campus or left blank to show for all campuses. They can have a date range or none (always active). "Special Event" entries are listed first.
- **Fare matrix** (`Matrix`): price per city + vehicle + campus. You can import it from the CarGo cargo-list Excel sheet.
- **Approvals** for pastors: trip entries (`/approvals_list/`) and leader accounts (`/leaders/approvals_list/`).
- **Vouchers**: a 7-character code for each trip, checked by the cashier.
- **Remarks**: a log of remarks per trip, for each role (`RemarksList`).
- **Reports and Excel export** for each week (`/reports/`, `/accounting/`).
- Photo uploads for each trip, with duplicate detection by image hash.

## Project layout

```
cargo_reports/        Django project (settings, root urls, wsgi)
Account/              Custom user model (UserType), AuthRoute, login / registration
cashier/              Main app: models, views, forms, APIs
  cargo_import.py     Pure-Python parser for the cargo-list Excel sheet
  utils.py            events_for_campus(): which events a campus should see
  remarks_views.py    Remarks submission
  management/commands/load_cargo_data.py
  test.py             Cargo-list loader test (writes JSON/Excel reports)
templates/            Templates by role: Accountant/, Pastor/, Authentication/, Registration/
static/               CSS, JS, images, Bootstrap
backup/               Seed data (e.g. auth_routes.json)
```

The frontend uses Django templates, Bootstrap and Stimulus controllers (`data-action="change->trip-form#..."`). The newer Accountant page (`templates/Accountant/index-2.html`) uses Vue and Quasar.

## Requirements

- Python 3.11+
- PostgreSQL. The current settings use database `cop_cargo_app_2026` on `localhost:5432`, overridable with `DB_HOST` / `DB_PORT`. SQLite is still in `settings.py`, commented out.
- Packages in `requirements.txt` (Django 5.2, openpyxl, Pillow, ...). You'll also need a PostgreSQL driver such as `psycopg[binary]`.

## Getting started (Windows)

```bash
python -m venv venv
```

```bash
venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
python manage.py makemigrations Account cashier
```

```bash
python manage.py migrate
```

```bash
python manage.py loaddata backup/auth_routes.json
```

```bash
python manage.py createsuperuser
```

```bash
python manage.py runserver
```

Then open http://127.0.0.1:8000/login/. The admin site is at `/admin/`.

> `migrations/` is git-ignored, so run `makemigrations` on a fresh clone.

### Helper scripts

These batch files sit next to `manage.py`. They share their settings in `_config.bat` and activate the venv on their own.

| Script | What it does |
|--------|--------------|
| `run_server.bat [addr:port]` | Warns about unapplied migrations, then runs the dev server (default `127.0.0.1:8000`) |
| `dump_data.bat [app]` | Dumps data to `backups\data_<timestamp>.json` and `backups\latest.json` |
| `load_data.bat [file.json]` | Loads a fixture (default `backups\latest.json`) |
| `flush_except_users.bat` | Backs up the data, flushes the database, then reloads the users |

## Importing the fare matrix

This loads City, Vehicle, SubsidyType and Matrix rows from the cargo-list sheet. Only `CARGO` rows are read, and every row goes under Campus id 1 ("Main"):

```bash
python manage.py load_cargo_data cashier/cargo_list.xlsx --dry-run
```

Drop `--dry-run` to write the changes. You can run it more than once: matching is by name, and running it again changes nothing.

Mapping rules (see `cashier/cargo_import.py`):
- `CAMPUS (DISTRICT)` becomes the city name, e.g. `Main (Pasay)`. If the district is blank, the pick-up location is used.
- `VAN/L300` becomes two vehicles with the same price.
- If the cost is blank or 0, the price is `REBATE AMOUNT / 0.5`. If the rebate equals the cost, the row is a "Student" subsidy.

## Tests

```bash
python manage.py test cashier.test
```

The test loads the sheet into a throwaway test database and goes through Campus, City, Vehicle and fare for every combination. Reports are written to `cashier/test_reports/`. `CARGO_XLSX` and `CARGO_REPORT_DIR` override the paths.

## Deployment notes

Production runs on Apache + mod_wsgi (Bitnami) at `cop-cargo.com`. Before deploying, in `cargo_reports/settings.py`:

- set `DEBUG = False`
- uncomment `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`
- uncomment `STATIC_ROOT` and the production `STATICFILES_DIRS`, then run `python manage.py collectstatic`
- move `SECRET_KEY` and the database credentials into environment variables
