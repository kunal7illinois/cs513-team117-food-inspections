# S2 - Kunal's profiling of the Violations column

Full profiling run against `Chicago-Food-Inspection/Food-Inspections-20251023.csv`
(298,869 rows). Scripts used are ad-hoc (not committed - see methodology below,
and `scripts/violations/parse_violations.py` for the production version).

## Format of the raw field

Each `Violations` cell is a set of entries joined by `" | "`. Each entry matches:

    <code>. <DESCRIPTION> - Comments: <free text>

Confirmed via regex over all entries with zero unparseable entries out of 974,597.
1,730 entries (0.18%) have no `- Comments:` section at all (inspector logged the
violation with no comment); this is handled as an empty comment string, not an error.

## Volume

| Metric | Value |
|---|---|
| Total rows | 298,869 |
| Rows with blank Violations | 83,344 (27.89%) |
| Total violation entries (non-blank rows) | 974,597 |
| Distinct raw violation codes | 65 |

Violation-count-per-inspection distribution (non-blank rows), most common counts:
3 violations (35,035 rows), 2 (34,857), 4 (30,368), 1 (28,859), 5 (23,883), 6 (17,976),
7 (12,874), 8 (9,270) ... tapering off after that. Matches the Phase-I report's
"usually 4 to 5" characterization reasonably well, with 1-3 being slightly more
common than initially estimated.

## Confirming Problem 4 (code collision across the 07/01/2018 checklist change)

This is the key profiling result for my S3 step. Method:

1. Split every violation entry by inspection era: `pre2018` (Inspection Date <
   07/01/2018) vs `post2018` (>= 07/01/2018).
2. For each (raw_code, era) pair, count how many distinct description strings
   appear, and how dominant the most common one is (purity).

Result (re-verified directly against the raw CSV): of the 65 distinct raw codes,
**45 appear in both eras, and every one of those 45 has a different top
description pre- vs. post-2018** - these are the genuinely reused/collided codes.
The other 20 codes appear in only one era (new or retired checklist items), so
they only ever have one meaning in the data and aren't part of the collision.
Across all 110 (raw_code, era) combinations that actually occur, **every one is
>=98% pure** (in practice the top description accounts for effectively all
occurrences) - i.e., splitting by the 07/01/2018 boundary cleanly separates the
two meanings of each reused code, with no meaningful bleed-over at the transition
date. (An earlier version of this note said "all 65 codes have exactly 2 distinct
meanings," which is wrong - that's only true of the 45 that appear in both eras.)

This directly confirms the report's Problem 4 example (code 18: rodent-proofing
pre-2018 vs. cooking temperature post-2018) generalizes to the other 44 reused
codes - and gives an empirical basis for the remap approach in S3 (era-tagging
each code) instead of needing to track down an external, harder-to-verify city
crosswalk document.

The 20 single-era codes include codes 61-64, which only appear post-2018 (new
checklist items), and code 70, which only appears pre-2018 (retired item, "NO
SMOKING REGULATIONS"). These don't need era-tagging to disambiguate (there's only
one meaning to begin with), but they get an era suffix anyway for a consistent
`violation_code` format across the lookup table.

## Where this feeds into S3

`scripts/violations/parse_violations.py` implements the parse + era-tag directly
based on these findings. See that folder's README for the output schema.
