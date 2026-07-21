# Violations (owner: Kunal) - S3 steps 1-2

Parses the pipe-delimited `Violations` field into individual violation rows, and
resolves Problem 4 from the Phase-I report (Chicago reused violation code numbers
for unrelated violations after a 07/01/2018 checklist revision) by tagging each
code with the era it was cited in. See `../../notes/S2_kunal_profiling_violations.md`
for the profiling that justifies this approach.

## Running it

```
python parse_violations.py <path-to-raw-csv> <output-dir>
```

Takes about 15 seconds on the full 298,869-row file. Writes three files to
`<output-dir>`:

- **`violation_finding_clean.csv`** (~200MB, one row per violation entry, ~975K
  rows) - `inspection_id, violation_code, raw_code, era, comment`. This is the
  fact table. **Not committed to git** (exceeds GitHub's 100MB file limit and
  isn't required as a deliverable itself - only the final D' needs a Box link).
  Regenerate it locally whenever the join step (S3, `scripts/join/`) needs it.
- **`violation_code_lookup.csv`** (~130 rows, committed) - `violation_code,
  raw_code, era, description, n_occurrences`. The dimension/lookup table:
  canonical description per (raw_code, era), chosen by majority vote (in
  practice unambiguous - see profiling notes, purity is effectively 100%).
  This is the `violation_code` table referenced by Q2 in the Phase-I report.
- **`sample_violation_finding.csv`** (200 rows, committed) - preview of the fact
  table for a quick sanity check without needing the full file.

`violation_code` values look like `18-PRE2018` / `18-POST2018` - traceable back
to the original numeric code, safe to `GROUP BY` without conflating two eras.

## Known edge case

1,730 violation entries (0.18%) have no `- Comments:` section at all (inspector
logged the code with no comment) - these get an empty `comment` value, not an error.
