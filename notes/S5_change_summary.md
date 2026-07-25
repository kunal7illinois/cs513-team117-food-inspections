# S5 - Change summary, D -> D'

Quantifies the actual changes made building D' from D (`scripts/join/build_databases.py`).
Full before/after query results are in `S4_before_after_results.md`.

## By column

| Column | Rows touched | Breakdown |
|---|---|---|
| **Facility Type** | 298,869 total; 16,550 cells changed (5.54%) | 2,286 (0.76%) case/whitespace-only; 14,264 (4.77%) real reclassification (e.g. "Daycare Above and Under 2 Years" -> "Daycare", "TAVERN" -> "Liquor"). Raw: 521 distinct values -> canonical: 240 (218 actually appear in the final `establishment` table after the per-license mode collapse). |
| **City** | 298,869 total; 298,222 cells "changed" (99.78%) | Almost all of that is cosmetic: 298,105 (99.74%) is case/whitespace normalization only (`CHICAGO` -> `Chicago`). Only 117 rows (0.04%) are substantive fixes (`CCHICAGO`, `CHICAGOO`, `312CHICAGO`, etc. -> `Chicago`). Raw: 90 distinct values -> canonical: 70 (69 in `establishment`). |
| **License #** | 787 rows had a placeholder (`0` or blank) | 89 actually recovered and overwritten with a real license (matched via normalized name+address across other inspections of the same establishment); 698 remain unresolved/ambiguous and unchanged (known limitation, see below). |
| **Results** | 298,869 rows gained a derived `outcome_bucket` field | 257,987 map 1:1 to `pass`/`fail` (no semantic change beyond lower-casing); 41,882 (14.01%) collapse from 4 distinct "didn't happen" strings (`Out of Business`, `No Entry`, `Not Ready`, `Business Not Located`) into one `no_outcome` category. |
| **Violations** | 0 structured rows -> 974,597 (`violation_finding`) | Entirely new structure - was one unparsed text blob per inspection. Of the 974,597 parsed entries, 711,085 (73.0%) belong to one of 45 raw codes that are reused across the 07/01/2018 checklist change, and would have been silently mis-grouped without the era-tag remap. |

## Integrity-constraint violations, before vs. after

| Check | D (before) | D' (after) |
|---|---|---|
| Inspections with unusable License # (unjoinable) | 787 | 698 (-11.3%) |
| License numbers with inconsistent Facility Type across their own history | 387 | 0 (enforced by construction - establishment is one row per license) |
| Distinct Facility Type spellings | 521 | 218 |
| Distinct City spellings | 90 | 69 |
| (facility_type, year) groups in Q1 (fragmentation) | 2,344 | 1,147 |
| Rows with a non-outcome Results value silently included if you forget to filter | 41,882 (14.01%) | 0 (excluded via `outcome_bucket`) |
| Q2 (violations by code) answerable at all | No (unparsed blob) | Yes (109 grouped categories) |

Note: the 387 figure for Facility-Type inconsistency is higher than the "198 license numbers" estimate in the Phase-I report - that number was a rough eyeball estimate before full profiling; 387 is the actual measured count and is the one we should use going forward.

## Known limitations / things NOT fixed

- **162 rows with blank City** are still blank in D' - never inferred (e.g. from Address/Zip), just left as-is.
- **8 rows with City = "INACTIVE"** were only capitalized to "Inactive", not actually resolved - this isn't a real city value and the underlying problem (facility status leaking into the City field) is still there.
- **698 of 787 bad License # rows remain unresolved** (60 ambiguous, 638 with no other record at all - mostly Special Events/one-off venues that plausibly never held a license).
- **Over-merge caught and fixed during review:** the original City clustering had merged 2 rows of `"CHICAGO HEIGHTS"` into `"Chicago"` (a real, separate incorporated city, not a misspelling) and left `"NILES NILES"` canonicalized to `"Niles Niles"` instead of `"Niles"`. Both corrected directly in `city_lookup.csv` before building D' - worth mentioning in the report as an example of QA catching a clustering false positive.
- **`"BANNOCKBURNDEERFIELD"`** (2 rows, two real Illinois towns concatenated) and **`"CHARLES A HAYES"`** (4 rows, looks like a building/institution name in the City field) were left as single canonical values rather than split or reclassified - lower-confidence edge cases, flagged here rather than guessed at.
