# CS 513 - Team 117 - Chicago Food Inspections

Phase-II data cleaning project for CS 513 (Summer 2026), UIUC.

**Team:** Kunal Sinha (kunal7@illinois.edu), Che-Min Lin (cheminl2@illinois.edu), Zehra Khan (zehraak2@illinois.edu)

**Dataset:** Chicago Food Inspections (CFI), snapshot `Food-Inspections-20251023.csv`, from
[data.cityofchicago.org](https://data.cityofchicago.org/Health-Human-Services/Food-Inspections/4ijn-s7e5/about_data),
via the course [Box link](https://uofi.box.com/s/vns80mmodwj66fj5l30cu31xdgnzcbac).

**Target use case (U1):** Which violations drive failures, by facility type and ZIP, over time?
See the Phase-I report for full details on U1/U0/U2 and the four documented data quality problems.

## Getting the data

The raw CSV (~313MB) is **not** in this repo - it's too large for GitHub and the assignment asks
us to link data via Box rather than commit it. Download it from the Box link above and drop it in
`Chicago-Food-Inspection/` locally (that path is gitignored).

## Repo layout

Mirrors the file contract from our Phase-I plan (Section 4): each person reads only the raw CSV
and writes to their own output file, so work stayed independent until the final join.

```
scripts/
  violations/          Kunal    - parse Violations field, remap pre/post 07/01/2018 codes
                                   -> violation_code_lookup.csv (committed), violation_finding_clean.csv (local only, ~200MB)
  facility_type_city/  Zehra    - OpenRefine clustering for Facility Type + City
                                   -> facility_type_lookup.csv, city_lookup.csv
  license_results/     Che-Min  - resolve License #=0, bucket Results into true outcomes
                                   -> license_fix.csv, results_bucketed.csv
  join/                Kunal    - build_databases.py builds raw.db (D) + clean.db (D') from all
                                   of the above; run_before_after.py runs the before/after queries

openrefine/            OpenRefineHistory.json - operation history (115 ops, Facility Type + City)
queries/               queries.txt - SQL used to profile D and D' and check ICs before/after
workflow/              Workflow_W1_outer.* (whole pipeline) and Workflow_W2_inner.* (OpenRefine steps)
notes/                 Per-step writeups (S1 review, S2 profiling, S4 results, S5 change summary)
D_prime_export/        CSV export of clean.db - the actual D' files, gitignored (~230MB total),
                        upload to Box and link in DataLinks.txt
DataLinks.txt           Box links to raw + cleaned datasets (cleaned link still TODO)
```

## Plan / timeline (from Phase-I report, Section 4)

| Step | Description | Owner(s) | Target |
|---|---|---|---|
| S1 | Review/update U1 + dataset description | All | 07/15 |
| S2 | Profile D to confirm the 4 DQ problems | Kunal (Violations), Zehra (Facility Type/City), Che-Min (License #/Results) | 07/18 |
| S3 | Clean each problem independently, then join | All | done |
| S4 | Before/after checks, re-run Q1/Q2 on D' | Kunal | done - see `notes/S4_before_after_results.md` |
| S5 | Document + quantify changes | All | done - see `notes/S5_change_summary.md` |

## Submission checklist (Phase-II)

- [ ] Phase-II report PDF (workflow description, before/after IC checks, change summary, conclusions) - final review in progress
- [x] Workflow model (`workflow/`)
- [x] OpenRefine operation history (`openrefine/OpenRefineHistory.json`)
- [x] Other scripts / provenance (`scripts/`)
- [x] Queries (`queries/queries.txt`)
- [x] `DataLinks.txt` with Box links to raw + cleaned data
