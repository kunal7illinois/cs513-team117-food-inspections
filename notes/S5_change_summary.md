# S5 - Change summary, D -> D'

Quantifies the actual changes made building D' from D (`scripts/join/build_databases.py`).
Full before/after query results are in `S4_before_after_results.md`.

## By column

| Column | Rows touched | Breakdown |
|---|---|---|
| **Facility Type** | 298,869 total; 16,550 cells changed (5.54%) | 2,286 (0.76%) case/whitespace-only; 14,264 (4.77%) real reclassification (e.g. "Daycare Above and Under 2 Years" -> "Daycare", "TAVERN" -> "Liquor"). Raw: 521 distinct values -> canonical: 240 (231 actually appear in the final `establishment` table after the per-license mode collapse - up from 218 before the synthetic-license-ID follow-up fix added 638 previously-orphaned inspections to the table). |
| **City** | 298,869 total; 298,222 cells "changed" (99.78%) | Almost all of that is cosmetic: 298,105 (99.74%) is case/whitespace normalization only (`CHICAGO` -> `Chicago`). Only 117 rows (0.04%) are substantive fixes (`CCHICAGO`, `CHICAGOO`, `312CHICAGO`, etc. -> `Chicago`). Raw: 90 distinct values -> canonical: 70 (69 in `establishment`). |
| **License #** | 787 rows had a placeholder (`0` or blank) | 89 recovered with a real license (name+address match against other inspections of the same establishment). Of the remaining 698, 638 "unresolved" rows (no other record at all) are now grouped among themselves by normalized (name, address) into 240 synthetic establishments (`SYN-000001`, ...) instead of all colliding on the literal `0` - this doesn't invent a real license, it just stops unrelated one-off venues from being merged together, and lets those inspections join to an establishment at all. Only the 60 "ambiguous" rows (multiple real candidate licenses, genuinely unclear which is right) remain unresolved/unchanged. |
| **Results** | 298,869 rows gained a derived `outcome_bucket` field | 257,987 map 1:1 to `pass`/`fail` (no semantic change beyond lower-casing); 41,882 (14.01%) collapse from 4 distinct "didn't happen" strings (`Out of Business`, `No Entry`, `Not Ready`, `Business Not Located`) into one `no_outcome` category. |
| **Violations** | 0 structured rows -> 974,597 (`violation_finding`) | Entirely new structure - was one unparsed text blob per inspection. Of the 974,597 parsed entries, 711,085 (73.0%) belong to one of 45 raw codes that are reused across the 07/01/2018 checklist change, and would have been silently mis-grouped without the era-tag remap. |

## Integrity-constraint violations, before vs. after

| Check | D (before) | D' (after) |
|---|---|---|
| Inspections with unusable License # (unjoinable to any establishment) | 787 | 60 (-92.4%) |
| License numbers with inconsistent Facility Type across their own history | 387 | 0 (enforced by construction - establishment is one row per license) |
| Distinct Facility Type spellings | 521 | 231 |
| Distinct City spellings | 90 | 69 |
| (facility_type, year) groups in Q1 (fragmentation) | 2,344 | 1,183 |
| Rows with a non-outcome Results value silently included if you forget to filter | 41,882 (14.01%) | 0 (excluded via `outcome_bucket`) |
| Q2 (violations by code) answerable at all | No (unparsed blob) | Yes (110 grouped categories) |

Note: the 387 figure for Facility-Type inconsistency is higher than the "198 license numbers" estimate in the Phase-I report - that number was a rough eyeball estimate before full profiling; 387 is the actual measured count and is the one we should use going forward.

The License # row improved sharply (787 -> 60) after adding the synthetic-grouping fix (see the License # row above); only the genuinely ambiguous cases (multiple real candidate licenses, no way to tell which is right without guessing) are still counted as unjoinable. Facility Type's distinct-value count went up slightly (218 -> 231) because the 638 previously-orphaned inspections now have an establishment row at all, surfacing a few more categories that only ever appeared on those unlicensed venues.

## Known limitations / things NOT fixed

- **City backfill (added after initial review):** blank/"Inactive" City values are now backfilled from another inspection of the same establishment when one exists (same trick as the License # fix, applied across columns). This resolved 22 of the 170 affected rows (162 blank + 8 "Inactive") - the rest (148 rows) belong to establishments where *every* recorded inspection has a blank/Inactive City, so there's nothing to borrow from. Those 148 are a genuine data gap, not something we didn't try.
- **Synthetic establishment IDs (added after initial review):** the 638 "unresolved" bad-License # rows (no other record with a real license) are grouped among themselves by normalized (name, address) into 240 synthetic establishments (`SYN-000001`, ...) instead of colliding on the literal `0`. This makes them joinable and keeps repeat inspections of the same never-licensed place together, but it does **not** invent a real government-issued license number - `establishment.license_no` starting with `SYN-` is a giveaway if anyone needs to distinguish real licenses from these.
- **60 "ambiguous" bad-License # rows remain genuinely unresolved** - multiple real candidate licenses were found and none was clearly correct, so nothing was guessed. A tiebreaker heuristic (e.g. most-recent-candidate) could reduce this further but risks picking wrong; not implemented.
- **Over-merge caught and fixed during review:** the original City clustering had merged 2 rows of `"CHICAGO HEIGHTS"` into `"Chicago"` (a real, separate incorporated city, not a misspelling) and left `"NILES NILES"` canonicalized to `"Niles Niles"` instead of `"Niles"`. Both corrected directly in `city_lookup.csv` before building D' - worth mentioning in the report as an example of QA catching a clustering false positive.
- **`"BANNOCKBURNDEERFIELD"`** (2 rows, two real Illinois towns concatenated) and **`"CHARLES A HAYES"`** (4 rows, looks like a building/institution name in the City field) were left as single canonical values rather than split or reclassified - lower-confidence edge cases, flagged here rather than guessed at.
