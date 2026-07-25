"""
CS 513 Team 117 - Phase II, S3 (Facility Type / City)

Zehra's OpenRefine export (`Food-Inspections City Lookup Table.csv` and
`Food-Inspections Facility Type Lookup Table.csv`) is a full row-level export of
the OpenRefine project: one row per original inspection (298,869 rows) with the
raw value and the clustered/canonicalized value side by side. That's correct
output from OpenRefine's "Export" feature, but it's the wrong shape for a lookup
table - it repeats the same raw->canonical mapping thousands of times and has no
join key (no Inspection ID / License #), so it can only be reattached to the main
dataset by trusting row order, which is fragile.

This script deduplicates both exports down to a real dimension table: one row per
distinct raw value. Verified first that the mapping is single-valued (no raw
value maps to more than one canonical value) - see output below - so this is a
safe, lossless deduplication, not a re-decision of any clustering choices Zehra
made in OpenRefine.

Usage:
    python dedupe_lookup_tables.py
(paths are hardcoded to this folder - it's a one-shot cleanup of a specific pair
of files, not a general tool)
"""
import csv
import collections
from pathlib import Path

HERE = Path(__file__).parent

JOBS = [
    {
        "src": HERE / "Food-Inspections City Lookup Table.csv",
        "raw_col": "City",
        "canon_col": "Canonicalized City",
        "out": HERE / "city_lookup.csv",
        "out_raw_col": "raw_city",
        "out_canon_col": "canonical_city",
    },
    {
        "src": HERE / "Food-Inspections Facility Type Lookup Table.csv",
        "raw_col": "Facility Type",
        "canon_col": "Canonicalized Facility Type",
        "out": HERE / "facility_type_lookup.csv",
        "out_raw_col": "raw_facility_type",
        "out_canon_col": "canonical_facility_type",
    },
]


def main():
    for job in JOBS:
        counts = collections.Counter()
        canon_for = {}
        with open(job["src"], newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw = row[job["raw_col"]]
                canon = row[job["canon_col"]]
                counts[raw] += 1
                if raw in canon_for and canon_for[raw] != canon:
                    raise ValueError(
                        f"Ambiguous mapping in {job['src'].name}: "
                        f"{raw!r} -> {canon_for[raw]!r} and {canon!r}"
                    )
                canon_for[raw] = canon

        with open(job["out"], "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([job["out_raw_col"], job["out_canon_col"], "n_occurrences"])
            for raw in sorted(counts, key=lambda r: -counts[r]):
                writer.writerow([raw, canon_for[raw], counts[raw]])

        print(
            f"{job['src'].name}: {sum(counts.values())} rows -> "
            f"{len(counts)} distinct raw values, "
            f"{len(set(canon_for.values()))} distinct canonical values "
            f"-> {job['out'].name}"
        )


if __name__ == "__main__":
    main()
