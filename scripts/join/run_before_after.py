"""
CS 513 Team 117 - Phase II, S4 (owner: Kunal)

Runs the before/after queries from queries/queries.txt against raw.db (D) and
clean.db (D', both built by build_databases.py) and writes the actual result
values to notes/S4_before_after_results.md for use in the Phase-II report.

Usage:
    python run_before_after.py <raw.db> <clean.db> <output_md_path>
"""
import sqlite3
import sys
from pathlib import Path


def fmt_rows(rows, limit=15):
    lines = []
    for row in rows[:limit]:
        lines.append(" | ".join(str(v) for v in row))
    if len(rows) > limit:
        lines.append(f"... ({len(rows)} rows total)")
    return "\n".join(lines) if lines else "(no rows)"


def main(raw_path, clean_path, out_path):
    raw = sqlite3.connect(raw_path)
    clean = sqlite3.connect(clean_path)
    out = []

    def section(title):
        out.append(f"\n## {title}\n")

    def run(conn, label, sql, limit=15):
        rows = conn.execute(sql).fetchall()
        out.append(f"**{label}**\n```\n{fmt_rows(rows, limit)}\n```")
        return rows

    section("Q1 - Failure rate by facility type and year")
    q1_raw = run(raw, "D (raw)", """
        SELECT facility_type,
               CAST(substr(inspection_date, 7, 4) AS INTEGER) AS yr,
               COUNT(*) AS inspections,
               ROUND(AVG(CASE WHEN results = 'Fail' THEN 1.0 ELSE 0 END), 3) AS fail_rate
        FROM inspection_raw
        WHERE results IN ('Pass', 'Pass w/ Conditions', 'Fail')
        GROUP BY facility_type, yr
        ORDER BY fail_rate DESC
    """)
    n_groups_raw = raw.execute("""
        SELECT COUNT(*) FROM (
            SELECT facility_type, CAST(substr(inspection_date,7,4) AS INTEGER) AS yr
            FROM inspection_raw
            WHERE results IN ('Pass','Pass w/ Conditions','Fail')
            GROUP BY facility_type, yr
        )
    """).fetchone()[0]
    out.append(f"\nTotal (facility_type, year) groups on D: {n_groups_raw}")

    q1_clean = run(clean, "D' (clean)", """
        SELECT e.facility_type,
               CAST(substr(i.inspection_date, 7, 4) AS INTEGER) AS yr,
               COUNT(*) AS inspections,
               ROUND(AVG(CASE WHEN i.outcome_bucket = 'fail' THEN 1.0 ELSE 0 END), 3) AS fail_rate
        FROM inspection i
        JOIN establishment e ON e.license_no = i.license_no
        WHERE i.outcome_bucket IN ('pass', 'fail')
        GROUP BY e.facility_type, yr
        ORDER BY fail_rate DESC
    """)
    n_groups_clean = clean.execute("""
        SELECT COUNT(*) FROM (
            SELECT e.facility_type, CAST(substr(i.inspection_date,7,4) AS INTEGER) AS yr
            FROM inspection i JOIN establishment e ON e.license_no = i.license_no
            WHERE i.outcome_bucket IN ('pass','fail')
            GROUP BY e.facility_type, yr
        )
    """).fetchone()[0]
    out.append(f"\nTotal (facility_type, year) groups on D': {n_groups_clean}")

    # Restaurant fail rate sanity check, both sides
    r = raw.execute("""
        SELECT ROUND(AVG(CASE WHEN results='Fail' THEN 1.0 ELSE 0 END), 3), COUNT(*)
        FROM inspection_raw WHERE facility_type = 'Restaurant'
        AND results IN ('Pass','Pass w/ Conditions','Fail')
    """).fetchone()
    c = clean.execute("""
        SELECT ROUND(AVG(CASE WHEN i.outcome_bucket='fail' THEN 1.0 ELSE 0 END), 3), COUNT(*)
        FROM inspection i JOIN establishment e ON e.license_no = i.license_no
        WHERE e.facility_type = 'Restaurant' AND i.outcome_bucket IN ('pass','fail')
    """).fetchone()
    out.append(f"\n'Restaurant' fail rate on D (exact-spelling only): {r[0]} over {r[1]} inspections")
    out.append(f"'Restaurant' fail rate on D' (canonicalized): {c[0]} over {c[1]} inspections")

    section("Q2 - Most common violations among failed inspections")
    run(raw, "D (raw) - degenerate: grouping on the whole unparsed Violations blob", """
        SELECT substr(violations,1,60) AS violations_snippet, COUNT(*) AS n
        FROM inspection_raw WHERE results = 'Fail' AND violations != ''
        GROUP BY violations ORDER BY n DESC
    """, limit=10)
    n_distinct_blobs = raw.execute("""
        SELECT COUNT(DISTINCT violations) FROM inspection_raw WHERE results='Fail' AND violations != ''
    """).fetchone()[0]
    n_failed_with_violations = raw.execute("""
        SELECT COUNT(*) FROM inspection_raw WHERE results='Fail' AND violations != ''
    """).fetchone()[0]
    out.append(f"\n{n_failed_with_violations} failed inspections with a non-blank Violations "
               f"field produce {n_distinct_blobs} distinct blobs "
               f"({n_distinct_blobs/n_failed_with_violations:.1%} unique) - grouping on the raw "
               f"text answers 'which exact inspections repeat', not 'which violations are common'.")

    run(clean, "D' (clean)", """
        SELECT vc.violation_code, vc.description, COUNT(*) AS times_cited
        FROM violation_finding vf
        JOIN inspection i ON i.inspection_id = vf.inspection_id
        JOIN violation_code vc ON vc.violation_code = vf.violation_code
        WHERE i.outcome_bucket = 'fail'
        GROUP BY vc.violation_code, vc.description
        ORDER BY times_cited DESC
    """)

    section("IC1 - License # must identify a real establishment (Problem 3)")
    a = raw.execute("SELECT COUNT(*) FROM inspection_raw WHERE license_no='0' OR license_no=''").fetchone()[0]
    b = clean.execute("SELECT COUNT(*) FROM inspection WHERE license_no='0' OR license_no=''").fetchone()[0]
    out.append(f"D:  {a} inspections with an unusable License # (unjoinable to any establishment)")
    out.append(f"D': {b} inspections still unjoinable after recovery attempt")
    out.append(f"IC violations reduced by {a-b} ({(a-b)/a:.1%})")
    run(clean, "D' fix_status breakdown", "SELECT license_fix_status, COUNT(*) FROM inspection GROUP BY license_fix_status")

    section("IC2 - Facility Type must be consistent per establishment (Problem 1)")
    a = raw.execute("""
        SELECT COUNT(*) FROM (
            SELECT license_no FROM inspection_raw WHERE license_no NOT IN ('0','')
            GROUP BY license_no HAVING COUNT(DISTINCT facility_type) > 1
        )
    """).fetchone()[0]
    b = clean.execute("""
        SELECT COUNT(*) FROM (
            SELECT license_no FROM establishment GROUP BY license_no
            HAVING COUNT(DISTINCT facility_type) > 1
        )
    """).fetchone()[0]
    out.append(f"D:  {a} license numbers with inconsistent Facility Type across their own inspection history")
    out.append(f"D': {b} (establishment enforces one facility_type per license_no by construction)")

    section("IC3 - Distinct value counts (Problems 1 & 2)")
    for label, sql_raw, sql_clean in [
        ("Facility Type", "SELECT COUNT(DISTINCT facility_type) FROM inspection_raw",
         "SELECT COUNT(DISTINCT facility_type) FROM establishment"),
        ("City", "SELECT COUNT(DISTINCT city) FROM inspection_raw",
         "SELECT COUNT(DISTINCT city) FROM establishment"),
    ]:
        a = raw.execute(sql_raw).fetchone()[0]
        b = clean.execute(sql_clean).fetchone()[0]
        out.append(f"{label}: D = {a} distinct values, D' = {b} distinct canonical values")

    section("IC4 - Results must be a real pass/fail outcome (for U1's fail-rate calc)")
    rows = raw.execute("""
        SELECT results, COUNT(*) FROM inspection_raw
        WHERE results NOT IN ('Pass','Fail','Pass w/ Conditions') GROUP BY results
    """).fetchall()
    total = raw.execute("SELECT COUNT(*) FROM inspection_raw").fetchone()[0]
    non_outcome = sum(r[1] for r in rows)
    out.append(f"D: {non_outcome} of {total} rows ({non_outcome/total:.2%}) have a Results value "
               f"that isn't a real outcome and must be excluded, or they silently distort any "
               f"naive fail-rate calculation:")
    out.append(fmt_rows(rows))
    out.append(f"\nD': all {non_outcome} handled via outcome_bucket = 'no_outcome' "
               f"(see results_bucketed.csv) - U1 queries filter on outcome_bucket IN ('pass','fail').")

    Path(out_path).write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {out_path}")
    raw.close()
    clean.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <raw.db> <clean.db> <output_md_path>")
        sys.exit(1)
    main(*sys.argv[1:])
