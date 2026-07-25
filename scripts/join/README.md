# Join (owner: Kunal) - S3 join, S4, S5

- **`build_databases.py`** - builds `raw.db` (D, one flat table, no cleaning)
  and `clean.db` (D', normalized `establishment` / `inspection` /
  `violation_finding` / `violation_code`) from the raw CSV plus the three
  teammates' cleaning outputs. Both DBs use the same table/column names where
  applicable so the same query can be pointed at either one. Not committed
  (each DB is 200-400MB) - regenerate locally:
  ```
  python build_databases.py <raw_csv> \
      ../facility_type_city/facility_type_lookup.csv \
      ../facility_type_city/city_lookup.csv \
      ../license_results/license_fix.csv \
      ../license_results/results_bucketed.csv \
      ../violations/violation_code_lookup.csv \
      <output_dir>
  ```
- **`run_before_after.py`** - runs the Q1/Q2/IC queries from
  `../../queries/queries.txt` against both DBs and writes the actual result
  values to `../../notes/S4_before_after_results.md`.
  ```
  python run_before_after.py <output_dir>/raw.db <output_dir>/clean.db ../../notes/S4_before_after_results.md
  ```

D' itself (the cleaned dataset) is exported from `clean.db` as 4 CSVs into
`../../D_prime_export/` (also gitignored - see `../../DataLinks.txt`, needs
uploading to Box).
