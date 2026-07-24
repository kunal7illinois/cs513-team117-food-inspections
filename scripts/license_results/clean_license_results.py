"""
CS 513 Team 117 - Phase II, S3 (owner: Che-Min)

Cleans the two columns assigned to me, working only off the raw CSV per our
file contract (Kunal joins everything at the end):

1. License # (Phase-I report, Problem 3). 787 of 298,869 rows carry a
   placeholder instead of a real license number: 769 rows with "0" and 18
   blank. For each affected inspection I try to recover the real license
   from OTHER inspections of the same establishment: rows are matched on
   normalized (name, Address), where "name" is either DBA Name or AKA Name
   (the two name columns are used inconsistently for the same
   establishment, so both are indexed and both names of the bad row are
   looked up). If the union of matches holds exactly one distinct real
   license the row is fixed; several distinct licenses -> flagged
   "ambiguous" and left unfixed; no match at all -> "unresolved" (mostly
   Special Events, churches, shelters - one-off venues that plausibly
   never held a license).

2. Results. The raw column mixes true inspection outcomes with
   couldn't-inspect statuses. I bucket the 7 observed values into
   pass / fail / no_outcome so U1 ("which violations drive failures")
   can filter on real outcomes. Emitted as a small lookup table keyed on
   the raw value, same shape as Kunal's violation_code_lookup.csv.

Validation performed before writing this script (profiling over the full
298,869-row file, see notes/S2_chemin_profiling_license_results.md):
  - License #: 298,082 real values (all pure digits), 769 "0", 18 blank.
  - Recovery over the 787 bad rows: 89 recovered, 60 ambiguous,
    638 unresolved.
  - Results has exactly the 7 values mapped in RESULT_BUCKETS below;
    the script raises on anything else.

Outputs (written to <output-dir>, both small enough to commit):
  license_fix.csv     one row per affected inspection:
                      inspection_id, dba_name, address, raw_license,
                      resolved_license, fix_status, candidate_licenses
  results_bucketed.csv  lookup: raw_result, outcome_bucket, n_occurrences

Usage:
  python clean_license_results.py <path-to-raw-csv> <output-dir>
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10_000_000)

PLACEHOLDER_LICENSES = {"", "0"}

# Raw Results value -> outcome bucket. pass/fail are true inspection
# outcomes; no_outcome means the inspection never actually happened
# (excluded from U1 pass/fail analysis).
RESULT_BUCKETS = {
    "Pass": "pass",
    "Pass w/ Conditions": "pass",
    "Fail": "fail",
    "Out of Business": "no_outcome",
    "No Entry": "no_outcome",
    "Not Ready": "no_outcome",
    "Business Not Located": "no_outcome",
}

WS_RE = re.compile(r"\s+")


def norm(s: str) -> str:
    """Uppercase and collapse whitespace so name/address matching is not
    defeated by casing or double spaces."""
    return WS_RE.sub(" ", (s or "").strip().upper())


def main(src_path: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    bad_rows = []                       # rows with a placeholder license
    name_addr = defaultdict(set)        # (DBA or AKA, addr) -> real licenses seen
    result_counts = Counter()

    n_rows = 0
    with open(src_path, newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            n_rows += 1
            result_counts[row["Results"]] += 1

            lic = (row["License #"] or "").strip()
            dba = norm(row["DBA Name"])
            aka = norm(row["AKA Name"])
            addr = norm(row["Address"])
            if lic in PLACEHOLDER_LICENSES:
                bad_rows.append((row["Inspection ID"], row["DBA Name"], row["Address"], lic, dba, aka, addr))
            else:
                if not lic.isdigit():
                    # verified not to trigger on the 20251023 snapshot
                    raise ValueError(f"unexpected License # format: {lic!r}")
                name_addr[(dba, addr)].add(lic)
                if aka:
                    name_addr[(aka, addr)].add(lic)

    unexpected = set(result_counts) - set(RESULT_BUCKETS)
    if unexpected:
        raise ValueError(f"unmapped Results value(s): {unexpected}")

    # --- license_fix.csv ---------------------------------------------------
    fix_status_counts = Counter()
    fix_path = out / "license_fix.csv"
    with open(fix_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["inspection_id", "dba_name", "address", "raw_license",
                    "resolved_license", "fix_status", "candidate_licenses"])
        for iid, dba_raw, addr_raw, lic_raw, dba, aka, addr in bad_rows:
            candidates = set(name_addr.get((dba, addr), ()))
            if aka:
                candidates |= name_addr.get((aka, addr), set())
            if not candidates:
                status = "unresolved"
            elif len(candidates) == 1:
                status = "recovered_name_addr"
            else:
                status = "ambiguous"
            resolved = next(iter(candidates)) if status == "recovered_name_addr" else ""
            fix_status_counts[status] += 1
            w.writerow([iid, dba_raw, addr_raw, lic_raw, resolved, status,
                        ";".join(sorted(candidates))])

    # --- results_bucketed.csv ----------------------------------------------
    bucket_path = out / "results_bucketed.csv"
    with open(bucket_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["raw_result", "outcome_bucket", "n_occurrences"])
        for raw, count in result_counts.most_common():
            w.writerow([raw, RESULT_BUCKETS[raw], count])

    # --- summary -----------------------------------------------------------
    n_bad = len(bad_rows)
    print(f"Rows read:                {n_rows}")
    print(f"Placeholder License #:    {n_bad} ({n_bad / n_rows:.2%})")
    for status, c in fix_status_counts.most_common():
        print(f"  {status}: {c}")
    n_outcome = sum(c for raw, c in result_counts.items() if RESULT_BUCKETS[raw] != "no_outcome")
    print(f"Results with true outcome: {n_outcome} ({n_outcome / n_rows:.2%})")
    print(f"-> {fix_path}")
    print(f"-> {bucket_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python clean_license_results.py <path-to-raw-csv> <output-dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
