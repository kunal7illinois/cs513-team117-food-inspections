# License # & Results (owner: Che-Min) - S3

Resolves rows where `License #` is 0 or blank (Phase-I report, Problem 3) and
buckets `Results` down to true pass/fail outcomes (excluding No Entry, Out of
Business, etc.). See `../../notes/S2_chemin_profiling_license_results.md` for
the profiling that justifies this approach.

## Running it

```
python clean_license_results.py <path-to-raw-csv> <output-dir>
```

Takes about 10 seconds on the full 298,869-row file. Writes two files to
`<output-dir>`, both small and committed:

- **`license_fix.csv`** (787 rows) - `inspection_id, dba_name, address,
  raw_license, resolved_license, fix_status, candidate_licenses`. One row per
  inspection whose `License #` was `0` (769) or blank (18). 89 rows are
  recovered (`fix_status = recovered_name_addr`) by finding other inspections
  of the same establishment - matched on normalized name + address, where the
  name can be `DBA Name` or `AKA Name` - that all agree on a single real
  license. 60 rows are `ambiguous` (the establishment held multiple license
  numbers over time; candidates listed but nothing guessed) and 638 are
  `unresolved` (no other record of the establishment - mostly Special Events,
  churches, shelters that plausibly never held a license).
- **`results_bucketed.csv`** (7 rows) - `raw_result, outcome_bucket,
  n_occurrences`. Lookup table over the 7 distinct raw `Results` values:
  `Pass` and `Pass w/ Conditions` -> `pass`, `Fail` -> `fail`, and the four
  "inspection never happened" statuses -> `no_outcome` (14.01% of all rows -
  these must be excluded from U1's pass/fail rates).

## For the join (Kunal)

- Overwrite `License #` with `resolved_license` where
  `fix_status = recovered_name_addr`, joining on `Inspection ID`; carry
  `fix_status` through as a quality flag for the ambiguous/unresolved rows.
- Join `Results` against `results_bucketed.csv` to add `outcome_bucket`;
  U1 queries filter to `outcome_bucket IN ('pass', 'fail')`.

The script fails loudly (raises) if it ever sees a `Results` value outside the
7 mapped ones or a non-digit real license, so a newer snapshot can't silently
mis-bucket.
