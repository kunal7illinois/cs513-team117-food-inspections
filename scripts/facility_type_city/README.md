# Facility Type & City (owner: Zehra) - S3

OpenRefine clustering to canonicalize the raw `Facility Type` (521 distinct raw
values -> 240 canonical) and `City` (90 distinct raw values -> 70 canonical)
columns (Phase-I report, Problems 1 and 2). OpenRefine operation history is at
`../../openrefine/OpenRefineHistory.json`.

## Files

- **`city_lookup.csv`**, **`facility_type_lookup.csv`** - the actual lookup
  tables: `raw_value, canonical_value, n_occurrences`, one row per distinct raw
  value. Join these against the main dataset's `City` / `Facility Type` columns
  by value (not row position) to get the canonical version.
- **`dedupe_lookup_tables.py`** - one-shot script that produced the two files
  above from Zehra's original OpenRefine export (see below). Verified the
  mapping is single-valued (no raw value maps to two different canonical
  values) before deduplicating, so this is a lossless reshape, not a
  re-decision of any clustering choices.

## QA correction made after dedup

Two rows in `city_lookup.csv` were hand-corrected after review, both edited
directly in that file (not re-run through OpenRefine): `"CHICAGO HEIGHTS"` was
being merged into `"Chicago"` - it's a real, separate incorporated Illinois
city, not a misspelling, so it now maps to itself. `"NILES NILES"` was
canonicalized to `"Niles Niles"` (duplication carried through) instead of
`"Niles"`. Both are reflected in `notes/S5_change_summary.md`. Worth a mention
in the report as a caught clustering false-positive. `"BANNOCKBURNDEERFIELD"`
and `"CHARLES A HAYES"` are similar-looking edge cases that were left as-is
(lower confidence on the right fix) - see that same notes file.
- **`Food-Inspections City Lookup Table.csv`**, **`Food-Inspections Facility
  Type Lookup Table.csv`** - Zehra's original OpenRefine export. Kept for
  provenance, but this is a full row-level export (298,869 rows, one per
  inspection, no join key) rather than a deduplicated table, so use the
  `*_lookup.csv` files above for the actual join, not these.

## Still needed

Profiling notes (`notes/S2_zehra_profiling_facility_city.md`, matching the
pattern in `notes/S2_kunal_profiling_violations.md`) - what thresholds/methods
were used in OpenRefine, any values that were hard to cluster, anything left
ambiguous.
