"""
Pure-Python helpers for turning the CarGo cargo-list sheet into Matrix rows.
No Django imports here, so the logic can be tested on its own.

Mapping (only rows whose first column is CARGO are read):
    CAMPUS (DISTRICT)  -> City.name          e.g. "Main (Pasay)"; created when missing
    Vehicle type       -> Vehicle.name       (normalised: "VAN/L300" -> "Van")
    TOTAL COST PF RENT -> Matrix.peso_price
        - blank / 0  : REBATE AMOUNT / 0.5
        - rebate == cost : SubsidyType "Student"
"""
import re
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal

import openpyxl

COL_TYPE = "BUS/CARGO/CAR POOL NO."
COL_CAMPUS = "CAMPUS"
COL_DISTRICT = "DISTRICT"
COL_PICKUP = "PICK UP LOCATION"
COL_VEHICLE = "Bus Company or Private Vehicle Type"
COL_COST = "TOTAL COST PF RENT"  # sic, as spelled in the sheet
COL_REBATE = "REBATE AMOUNT"

ONLY_TYPE = "CARGO"
PLACEHOLDER = "Unidentified"
STUDENT = "Student"
REBATE_DIVISOR = Decimal("0.5")

# CAMPUS column -> prefix used in City names (matches your existing "Santa Rosa (...)" cities)
CAMPUS_PREFIX = {"SRC": "Santa Rosa", "MAKATI": "Main"}

# The sheet came from a PDF, so some words are cut in two ("MANDALUYO NG").
WORD_REPAIRS = [
    "Mandaluyong", "Valenzuela", "Intramuros", "Tagaytay", "Pampanga", "Bulacan", "Marikina",
    "Dasmariñas", "Malagasang", "Pandacan",
]

# Spelling fixes for single vehicle types. Anything not listed keeps its own (tidied) name.
VEHICLE_NAMES = {
    "JEEP": "Jeep", "VAN": "Van", "L300": "L300", "SUV": "SUV", "SUVS": "SUV",
    "SEDAN": "Sedan", "PRIVATE": "Private",
}


def vehicle_names(value):
    """'VAN/L300' -> ['Van', 'L300']: every slash-separated part is its own vehicle."""
    names = []
    for part in clean(value).split("/"):
        part = part.strip()
        if part:
            name = VEHICLE_NAMES.get(squash(part)) or pretty(part)
            if name not in names:
                names.append(name)
    return names


def clean(value):
    return re.sub(r"\s+", " ", str(value)).strip() if value is not None else ""


def squash(value):
    """Upper-case with all spaces and dots removed."""
    return re.sub(r"[\s.]+", "", clean(value)).upper()


def norm(name):
    """Comparison key: ignores case, accents, spaces and punctuation."""
    text = unicodedata.normalize("NFKD", clean(name))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


_REPAIRS = {norm(w): w for w in WORD_REPAIRS}

# Short ALL-CAPS words that are ordinary words, not acronyms (acronyms like WCC, QC, TUP stay upper-case).
LOWERCASE_WORDS = {"SAN", "LAS", "STA", "AND", "GEN", "TRI", "DE", "LA", "DEL"}


def has_enye(name):
    return "ñ" in unicodedata.normalize("NFC", name).casefold()


def build_index(objs):
    """norm(name) -> one object. Duplicates: the spelling with ñ wins, then the lowest pk."""
    best = {}
    for obj in sorted(objs, key=lambda o: (not has_enye(o.name), o.pk)):
        best.setdefault(norm(obj.name), obj)
    return best


def pretty(text):
    """Display form for text taken from the sheet: repaired split words, sensible casing."""
    text = clean(text)
    if norm(text) in _REPAIRS:
        return _REPAIRS[norm(text)]
    if text.isupper() or text.islower():
        return " ".join(
            w if (w.isupper() and len(w) <= 3 and w not in LOWERCASE_WORDS) else w.capitalize()
            for w in text.split(" ")
        )
    return text


def city_name(row):
    """'<Campus> (<District>)'. A blank or literal 'DISTRICT' falls back to the pick up location."""
    campus = clean(row.get(COL_CAMPUS))
    prefix = CAMPUS_PREFIX.get(squash(campus)) or pretty(campus)
    district = clean(row.get(COL_DISTRICT))
    if not district or district.upper() == "DISTRICT":
        district = clean(row.get(COL_PICKUP))
    if prefix and district:
        return f"{prefix} ({pretty(district)})"
    return prefix or (pretty(district) if district else None)


def to_decimal(value):
    digits = re.sub(r"[^\d.]", "", str(value if value is not None else ""))
    return Decimal(digits) if digits else None


def price_and_student(row):
    """(price, is_student). No cost -> rebate / 0.5; nothing at all -> 0.00."""
    cost, rebate = to_decimal(row.get(COL_COST)), to_decimal(row.get(COL_REBATE))
    if cost:
        return cost, rebate == cost
    if rebate:
        return (rebate / REBATE_DIVISOR).quantize(Decimal("0.01")), False
    return Decimal("0.00"), False


def read_rows(path):
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    it = ws.iter_rows(values_only=True)
    header = [clean(h) for h in next(it)]
    for excel_row, values in enumerate(it, start=2):
        if any(v is not None for v in values):
            yield excel_row, dict(zip(header, values))


def collect(path):
    """
    Returns (entries, skipped, conflicts, placeholders, student_rows):
      entries       {(city_name, vehicle_name): Decimal price}
      skipped       [(excel_row, reason)]   (CARGO rows only)
      conflicts     [(key, {price: count}, chosen)]
      placeholders  [excel_row]             rows whose vehicle became 'Unidentified'
      student_rows  [excel_row]             rows where rebate == cost
    """
    prices, skipped, placeholders, student_rows = defaultdict(list), [], [], []
    for excel_row, row in read_rows(path):
        if squash(row.get(COL_TYPE)) != ONLY_TYPE:
            continue
        city = city_name(row)
        if not city:
            skipped.append((excel_row, "no campus / district"))
            continue
        price, is_student = price_and_student(row)
        if is_student:
            student_rows.append(excel_row)
        vehicles = vehicle_names(row.get(COL_VEHICLE))
        if not vehicles:
            vehicles = [PLACEHOLDER]
            placeholders.append(excel_row)
        for vehicle in vehicles:  # "VAN/L300" -> the same price on both a Van and an L300 entry
            prices[(city, vehicle)].append(price)

    entries, conflicts = {}, []
    for key, values in prices.items():
        counts = Counter(v for v in values if v) or Counter(values)  # a 0.00 never beats a real price
        chosen = max(counts, key=lambda p: (counts[p], p))
        entries[key] = chosen
        if len(counts) > 1:
            conflicts.append((key, dict(counts), chosen))
    return entries, skipped, conflicts, placeholders, student_rows
