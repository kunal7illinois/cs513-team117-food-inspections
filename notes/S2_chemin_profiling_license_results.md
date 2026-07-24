# S2 - Che-Min's profiling of License # and Results

Profiled the full raw snapshot `Chicago-Food-Inspection/Food-Inspections-20251023.csv`
(298,869 data rows), the same file Kunal profiled for Violations. Ad-hoc
profiling scripts were not committed; the cleaning script that came out of
this (`scripts/license_results/clean_license_results.py`) re-verifies the
key counts and raises if the file ever disagrees.

## Confirming Problem 3 (placeholder License #)

1. Counted rows where `License #` is `"0"` or blank after stripping
   whitespace.
2. Result: **769 rows with `0` and 18 blank rows, 787 total (0.26%)**.
   The 769 figure matches the Phase-I report; the 18 blanks are new -
   worth folding into the Phase-II writeup since they're the same defect.
3. All 298,082 remaining values are pure digit strings - no floats, no
   stray characters - so `License #` can be treated as an opaque integer
   key with `0`/blank as the only placeholder forms.

Who has the placeholder? Top facility types among the 787: Special Event
(164), Restaurant (182), blank facility type (64), Shelter (56), School
(45), Church (34), Navy Pier Kiosk (33). The rows are spread evenly across
2010-2025, so this is a steady intake artifact, not a one-time glitch.
The concentration in one-off/institutional venues suggests many of these
establishments genuinely never held a city food license.

## Recoverability

For each of the 787 rows I looked for OTHER inspections of the same
establishment, matching on normalized (name, Address) where the name can
be either `DBA Name` or `AKA Name` (the two columns are used
inconsistently for the same place - indexing both recovers 24 extra rows
over DBA-only matching):

| outcome | rows |
|---|---|
| recovered - matches agree on exactly one real license | 89 |
| ambiguous - matches span 2+ distinct licenses | 60 |
| unresolved - no other record of the establishment | 638 |

Notes on the two unfixed groups:

- **Ambiguous** is usually license churn, not bad matching: e.g.
  MCDONALD'S at 6560 S STONY ISLAND AVE has held 4 different license
  numbers over the years. Picking the license nearest the inspection date
  would resolve some of these, but I left them flagged rather than guess.
- **Unresolved** is dominated by the one-off venues above (Special
  Events, churches, shelters). For these, `0` arguably *means* "no
  license exists"; we can't invent a number, so they stay flagged.

## Results distribution

Exactly 7 distinct values over all 298,869 rows, no casing or whitespace
variants:

| raw value | rows | share | bucket |
|---|---|---|---|
| Pass | 154,452 | 51.68% | pass |
| Fail | 57,819 | 19.35% | fail |
| Pass w/ Conditions | 44,716 | 14.96% | pass |
| Out of Business | 24,726 | 8.27% | no_outcome |
| No Entry | 12,953 | 4.33% | no_outcome |
| Not Ready | 4,110 | 1.38% | no_outcome |
| Business Not Located | 93 | 0.03% | no_outcome |

Bucketing rationale: `Pass w/ Conditions` still means the establishment
passed (violations were correctable on site), so it buckets to `pass`;
the raw value is preserved in the lookup if we later want to split it
out. The four `no_outcome` values mean no inspection actually took place
- 14.01% of all rows - and must be excluded from U1's pass/fail rates,
otherwise failure rates are diluted.

## Where this feeds into S3 / the join

`clean_license_results.py <raw-csv> <out-dir>` writes both outputs
(committed, both small):

- `license_fix.csv` (787 rows) - keyed on `inspection_id`; Kunal's join
  should overwrite `License #` with `resolved_license` where
  `fix_status = recovered_name_addr`, and can carry `fix_status` through
  as a quality flag for the ambiguous/unresolved rows.
- `results_bucketed.csv` (7 rows) - lookup keyed on the raw `Results`
  string; join adds `outcome_bucket`, and U1 queries filter to
  `outcome_bucket IN ('pass','fail')`.
