from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...cargo_import import PLACEHOLDER, STUDENT, build_index, collect, norm

CAMPUS_ID = 1  # Campus "Main"


class Command(BaseCommand):
    help = (
        "Load City, Vehicle, SubsidyType and Matrix rows from the CarGo cargo-list Excel sheet "
        "(CARGO rows only). Matches by name, never by pk. Matrix.campus is set to the existing Campus id 1; Campus rows are never created or changed."
    )

    def add_arguments(self, parser):
        parser.add_argument("xlsx", help="Path to the cargo list .xlsx")
        parser.add_argument("--app", default="cashier", help="App label that owns the models (default: cashier)")
        parser.add_argument("--dry-run", action="store_true", help="Report what would change; write nothing")

    def handle(self, *args, xlsx, app, dry_run, **opts):
        try:
            City, Campus, Vehicle, SubsidyType, Matrix = (
                apps.get_model(app, m) for m in ("City", "Campus", "Vehicle", "SubsidyType", "Matrix")
            )
        except LookupError as exc:
            raise CommandError(f"{exc} (use --app to set the app label)")

        # Every Matrix row is attached to this existing campus; Campus rows are never created or changed.
        campus = Campus.objects.filter(pk=CAMPUS_ID).first()
        if campus is None:
            raise CommandError(f"Campus with id {CAMPUS_ID} does not exist")

        entries, skipped, conflicts, placeholders, student_rows, splits = collect(xlsx)
        stats = {"cities_created": 0, "vehicles_created": 0, "subsidy_types_created": 0,
                 "matrix_created": 0, "matrix_updated": 0, "matrix_unchanged": 0}

        cities = build_index(City.objects.all())
        vehicles = build_index(Vehicle.objects.all())

        def get_or_create(index, model, name, stat, **extra):
            obj = index.get(norm(name))
            if obj is None:
                obj = index[norm(name)] = model.objects.create(name=name, **extra)
                stats[stat] += 1
            return obj

        with transaction.atomic():
            # "Student" lives in its own table; Matrix does not reference it.
            if student_rows:
                get_or_create(build_index(SubsidyType.objects.all()), SubsidyType, STUDENT, "subsidy_types_created")

            for (city_name, vehicle_name), price in sorted(entries.items()):
                city = get_or_create(cities, City, city_name, "cities_created")
                vehicle = get_or_create(vehicles, Vehicle, vehicle_name, "vehicles_created", peso_price=0)
                row = Matrix.objects.filter(city=city, vehicle=vehicle, campus=campus).order_by("pk").first()
                if row is None:
                    stats["matrix_created"] += 1
                    Matrix.objects.create(city=city, campus=campus, vehicle=vehicle, peso_price=price)
                elif row.peso_price != price:
                    stats["matrix_updated"] += 1
                    row.peso_price = price
                    row.save()
                else:
                    stats["matrix_unchanged"] += 1

            if dry_run:
                transaction.set_rollback(True)

        out = self.stdout.write
        out(f"{'DRY RUN - nothing saved. ' if dry_run else 'SAVED. '}{stats}")
        out(f"{len(entries)} city / vehicle combinations read from the CARGO rows; "
            f"{len(student_rows)} rows have rebate == cost ({STUDENT})")
        if splits:
            out(f"{len(splits)} rows had a different price for the same city + vehicle and were moved to a pick-up-specific city:")
            for excel_row, base, new, vehicle in splits:
                out(f"  Excel row {excel_row}: {base} -> {new} / {vehicle}")
        for (city, vehicle), counts, chosen in conflicts:
            out(f"UNRESOLVED price conflict {city} / {vehicle}: "
                + ", ".join(f"{p:.2f} x{n}" for p, n in counts.items()) + f" -> used {chosen:.2f}")
        if placeholders:
            out(f"Vehicle type blank, filed under '{PLACEHOLDER}': Excel rows {', '.join(map(str, placeholders))}")
        out(f"Skipped {len(skipped)} CARGO rows:")
        for row, why in skipped:
            out(f"  Excel row {row}: {why}")
