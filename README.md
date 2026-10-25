https://we.tl/t-ChbCqMw7xKNVBezo

# Cargo List Loader

Loads the CarGo cargo-list Excel sheet into the fare tables of the `cashier` Django app, and includes an
automated test that simulates a user picking Campus, City and Vehicle from dropdowns and checks the fare.

## What is in this package

```
cargo_loader/
├── README.md                          <- this file (keep it OUTSIDE your Django project)
└── cashier/                           <- copy the contents of this folder into your cashier app
    ├── cargo_import.py                   reads and interprets the sheet
    ├── test.py                           automated test + JSON/Excel report
    └── management/
        ├── __init__.py
        └── commands/
            ├── __init__.py
            └── load_cargo_data.py        the command: python manage.py load_cargo_data
```

Only the `cashier/` folder goes into your project. This README stays outside, for example in a `docs/` folder or next to the project.

## Requirements

- Django project with the `cashier` app and the models `City`, `Campus`, `Vehicle`, `SubsidyType`, `Matrix`
  (each with a `name` field; `Matrix` has `city`, `campus`, `vehicle`, `peso_price`).
- `SubsidyType` created and migrated (`python manage.py makemigrations && python manage.py migrate`).
- A `Campus` row with id 1 (Main).
- `pip install openpyxl`

## Install

1. Copy everything inside `cargo_loader/cashier/` into your project's `cashier/` folder (next to `models.py`).
   If `management/` or `management/commands/` already exist, add the files and keep your existing `__init__.py`.
2. Put the Excel sheet at `cashier/cargo_list.xlsx` (or point `CARGO_XLSX` at it).

## Run the loader

Preview first. Nothing is saved:

```bash
python manage.py load_cargo_data "cashier\cargo_list.xlsx" --dry-run
```

Load for real (same command without `--dry-run`):

```bash
python manage.py load_cargo_data "cashier\cargo_list.xlsx"
```

Options: `--app <label>` if your app is not called `cashier`. Campus id 1 is set by `CAMPUS_ID` at the top of
`load_cargo_data.py`.

The command prints what it created, updated or left unchanged, every price conflict, and the rows that were
filed under "Unidentified". It is safe to run again: it matches by name, never by id, so it does not duplicate rows.

## How the sheet is converted

Only rows whose first column is `CARGO` are read.

| Sheet | Goes to | Rule |
|---|---|---|
| CAMPUS + DISTRICT | `City.name` | Built as `Campus (District)`, e.g. `Main (Pasay)`. Matches existing cities ignoring case, accents and spacing; creates missing ones. `SRC` becomes `Santa Rosa`. If DISTRICT is blank or literally "DISTRICT", the PICK UP LOCATION is used. |
| Vehicle type | `Vehicle.name` | A `/` creates separate entries with the same data (`VAN/L300` gives Van and L300). `SUVS` becomes `SUV`. Blank gives `Unidentified`. New vehicles get `peso_price` 0. |
| TOTAL COST PF RENT | `Matrix.peso_price` | If blank, REBATE AMOUNT / 0.5. If both are blank, 0.00. |
| Cost equals rebate | `SubsidyType` "Student" | The `Student` row is created if missing. It is not linked to Matrix. |
| (none) | `Matrix.campus` | Always Campus id 1 (Main). Campus rows are never created or changed. |

One Matrix row per city and vehicle.

### Price conflicts

When the sheet gives different prices for the same city and vehicle, the loader tries to separate them by
**pick up location**: the rows that name a pick up move to their own city, `Campus (District - Pick up)`,
for example `Tagaytay (Tagaytay - Brgy Asis, Mendez)`. Rows with no pick up stay on the base city. This is only
done when it really removes the conflict.

If splitting cannot separate them (same pick up, or no pick up at all), the most common price wins (a 0.00 never
beats a real price, a tie goes to the higher price) and the command prints it as an
`UNRESOLVED price conflict`. Fix those in the sheet and run again.

Every split row is listed in the command output.

## Run the automated test

```bash
python manage.py test cashier.test
```

Django builds a temporary empty database, creates Campus id 1, loads the sheet with the command above, and then,
for every city and vehicle combination in the sheet:

1. selects the Campus,
2. checks the City appears in the City dropdown,
3. checks the Vehicle appears in the Vehicle dropdown for that city,
4. checks the fare equals the expected price.

It also checks the whole table: campus on every row, no duplicates, row count, no Campus rows added,
`Student` exists when needed, and that running the loader twice changes nothing.

Your real database is never touched.

### Reports

Each run writes a timestamped JSON and Excel file to `cashier/test_reports/`
(change with `CARGO_REPORT_DIR`). Columns: No, Test, Campus, City, Vehicle, Excel rows, Expected, Actual,
Result (PASS/FAIL), Failed step, Remark. A failing row's remark gives the failed step and expected vs actual.

### Settings (environment variables)

| Variable | Default |
|---|---|
| `CARGO_XLSX` | `cashier/cargo_list.xlsx` |
| `CARGO_REPORT_DIR` | `cashier/test_reports` |

## Things to review after the first dry run

- Rows that used the pick-up location because DISTRICT was blank (South and Kawit campuses).
- Rows filed under `Unidentified` (no vehicle type, e.g. the North rows).
- Price conflicts where the most common price was used.
- New City rows you may want to rename or merge, e.g. `South (Salawag)`.

## Troubleshooting

| Message | Cause |
|---|---|
| `Campus with id 1 does not exist` | Create the Main campus, or change `CAMPUS_ID`. |
| `No installed app with label ...` / `LookupError` | Wrong app label; pass `--app`. |
| `Unknown command: 'load_cargo_data'` | The two `__init__.py` files in `management/` are missing. |
| `ModuleNotFoundError: openpyxl` | `pip install openpyxl` |
| Test: `Excel sheet not found` | Put the sheet at `cashier/cargo_list.xlsx` or set `CARGO_XLSX`. |

## Notes

- The dropdown steps in the test are simulated with database queries. If you want the test to call your real
  view or API instead, that can be added.
- Tested on Django 6.1 with SQLite in a throwaway project that mirrors your models; run the dry run and the test
  in your own project before the real load.
