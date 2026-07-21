"""
CS 513 Team 117 - Phase II, S3 steps 1-2 (owner: Kunal)

Parses the pipe-delimited `Violations` free-text field in the raw Chicago Food
Inspections CSV into individual violation rows, and resolves Problem 4 from the
Phase-I report: Chicago revised its inspection checklist on 07/01/2018 and reused
the same numeric violation codes for unrelated violations. Grouping by the raw
code alone silently merges two different violation types under one label.

Approach: rather than relying on an external, hard-to-verify crosswalk document,
we use the fact that the raw data already embeds the *correct* description text
for whichever checklist era a given inspection falls under. We tag each raw code
with an era (pre/post 07/01/2018) to build a canonical `violation_code` that is
safe to GROUP BY, and derive its canonical description as the majority-vote
description observed for that (raw_code, era) pair.

Validation performed before writing this script (see PROFILING.md in this folder):
  - 65 distinct raw codes across 974,597 violation entries in 298,869 rows.
  - Every one of the 65 codes has exactly 2 distinct description strings site-wide,
    consistent with a single checklist revision reusing code numbers.
  - Splitting by the 07/01/2018 boundary, all 130 (code, era) combinations that
    occur are >=98% pure by description (in fact 100% at the >=98% threshold
    tested) - i.e. the era split cleanly separates the two meanings with no
    meaningful cross-contamination at the transition date.

Outputs (matches the VIOLATION / violation_code split implied by Q2 in the
Phase-I report, and by the ER diagram's VIOLATION entity):
  - violation_finding_clean.csv : inspection_id, violation_code, raw_code, era, comment
      (one row per violation entry - this is the fact table)
  - violation_code_lookup.csv   : violation_code, raw_code, era, description
      (one row per distinct (raw_code, era) - this is the dimension/lookup table)

violation_finding_clean.csv carries the same free-text comment volume as the
original Violations column, so it lands well over GitHub's 100MB file limit for
this dataset (~298K rows). It is intentionally NOT committed to git - see
.gitignore and this folder's README. violation_code_lookup.csv (~130 rows) is
small and is committed.

Usage:
    python parse_violations.py <path-to-raw-csv> <output-dir>
"""
import csv
import datetime
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

csv.field_size_limit(10_000_000)

ENTRY_RE = re.compile(r"^\s*(\d+)\.\s*(.*?)(?:\s*-\s*Comments:\s*(.*))?$", re.DOTALL)
DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
CUTOFF = datetime.date(2018, 7, 1)


def parse_date(s: str) -> datetime.date:
    m = DATE_RE.match(s)
    if not m:
        raise ValueError(f"Unrecognized Inspection Date format: {s!r}")
    mm, dd, yyyy = m.groups()
    return datetime.date(int(yyyy), int(mm), int(dd))


def era_for(d: datetime.date) -> str:
    return "pre2018" if d < CUTOFF else "post2018"


def parse_violations_field(raw: str):
    """Yields (raw_code, description, comment) for one Violations cell."""
    if not raw:
        return
    for entry in raw.split(" | "):
        m = ENTRY_RE.match(entry)
        if not m:
            # Not expected to trigger on this dataset (verified during profiling),
            # but fail loudly rather than silently dropping a violation.
            raise ValueError(f"Could not parse violation entry: {entry!r}")
        raw_code, desc, comment = m.group(1), m.group(2).strip(), m.group(3)
        yield raw_code, desc, (comment.strip() if comment else "")


def main(src_path: str, out_dir: str):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    findings_path = out_dir / "violation_finding_clean.csv"
    lookup_path = out_dir / "violation_code_lookup.csv"
    sample_path = out_dir / "sample_violation_finding.csv"

    # (raw_code, era) -> Counter of descriptions seen, for majority-vote canonical text
    desc_counts = defaultdict(Counter)

    n_rows = 0
    n_findings = 0
    n_blank_violations = 0
    sample_rows = []

    with open(src_path, newline="", encoding="utf-8", errors="replace") as f_in, \
         open(findings_path, "w", newline="", encoding="utf-8") as f_out:

        reader = csv.DictReader(f_in)
        writer = csv.writer(f_out)
        writer.writerow(["inspection_id", "violation_code", "raw_code", "era", "comment"])

        for row in reader:
            n_rows += 1
            insp_id = row["Inspection ID"]
            violations = row["Violations"]
            if not violations:
                n_blank_violations += 1
                continue

            insp_date = parse_date(row["Inspection Date"])
            era = era_for(insp_date)

            for raw_code, desc, comment in parse_violations_field(violations):
                violation_code = f"{raw_code}-{era.upper()}"
                desc_counts[(raw_code, era)][desc] += 1
                out_row = [insp_id, violation_code, raw_code, era, comment]
                writer.writerow(out_row)
                n_findings += 1
                if len(sample_rows) < 200:
                    sample_rows.append(out_row)

    # Write the lookup/dimension table using majority-vote canonical description
    with open(lookup_path, "w", newline="", encoding="utf-8") as f_lookup:
        writer = csv.writer(f_lookup)
        writer.writerow(["violation_code", "raw_code", "era", "description", "n_occurrences"])
        for (raw_code, era), counter in sorted(desc_counts.items(), key=lambda kv: (int(kv[0][0]), kv[0][1])):
            desc, _ = counter.most_common(1)[0]
            total = sum(counter.values())
            violation_code = f"{raw_code}-{era.upper()}"
            writer.writerow([violation_code, raw_code, era, desc, total])

    with open(sample_path, "w", newline="", encoding="utf-8") as f_sample:
        writer = csv.writer(f_sample)
        writer.writerow(["inspection_id", "violation_code", "raw_code", "era", "comment"])
        writer.writerows(sample_rows)

    print(f"Rows read:              {n_rows}")
    print(f"Rows with blank Violations: {n_blank_violations} ({n_blank_violations/n_rows:.2%})")
    print(f"Violation findings written: {n_findings}")
    print(f"Distinct (raw_code, era) combos: {len(desc_counts)}")
    print(f"-> {findings_path}")
    print(f"-> {lookup_path}")
    print(f"-> {sample_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <path-to-raw-csv> <output-dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
