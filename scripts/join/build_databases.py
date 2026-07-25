"""
CS 513 Team 117 - Phase II, S3 join step (owner: Kunal)

Builds two SQLite databases with the SAME table/column names but different
data quality, so the exact same Q1/Q2-style SQL can be pointed at either one
to show a direct before/after comparison (this is the approach our Phase-I
plan committed to - see notes there re: "Q1 and Q2 ... run unmodified against
both D and D'").

  raw.db   - D:  one flat table (`inspection_raw`), a straight load of the
             original CSV with no cleaning applied at all. Violations stays
             as one unparsed text blob per row, matching the real raw data.

  clean.db - D': normalized schema matching our Phase-I ER diagram:
               establishment(license_no, dba_name, aka_name, address, city,
                              state, zip, facility_type, latitude, longitude)
               inspection(inspection_id, license_no, inspection_date,
                           inspection_type, risk, raw_result, outcome_bucket,
                           license_fix_status)
               violation_finding(inspection_id, violation_code, raw_code,
                                  era, comment)
               violation_code(violation_code, raw_code, era, description)

Inputs (all relative to the repo root, produced by the three S3 workstreams):
  Chicago-Food-Inspection/Food-Inspections-20251023.csv   raw data (gitignored, local only)
  scripts/facility_type_city/facility_type_lookup.csv
  scripts/facility_type_city/city_lookup.csv
  scripts/license_results/license_fix.csv
  scripts/license_results/results_bucketed.csv
  scripts/violations/violation_code_lookup.csv
  (violation findings are re-parsed fresh here rather than read from the
  ~200MB violation_finding_clean.csv, using the same logic as
  scripts/violations/parse_violations.py, to avoid depending on that large
  intermediate file existing on disk)

Usage:
    python build_databases.py <raw_csv> <facility_type_lookup> <city_lookup> \\
        <license_fix> <results_bucketed> <violation_code_lookup> <output_dir>
"""
import csv
import datetime
import re
import sqlite3
import sys
import collections
from pathlib import Path

csv.field_size_limit(10_000_000)

# --- Violation parsing (same logic as scripts/violations/parse_violations.py) ---
ENTRY_RE = re.compile(r"^\s*(\d+)\.\s*(.*?)(?:\s*-\s*Comments:\s*(.*))?$", re.DOTALL)
DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
CUTOFF = datetime.date(2018, 7, 1)


def parse_date(s):
    m = DATE_RE.match(s)
    mm, dd, yyyy = m.groups()
    return datetime.date(int(yyyy), int(mm), int(dd))


def era_for(d):
    return "pre2018" if d < CUTOFF else "post2018"


def parse_violations_field(raw):
    if not raw:
        return
    for entry in raw.split(" | "):
        m = ENTRY_RE.match(entry)
        if not m:
            raise ValueError(f"Could not parse violation entry: {entry!r}")
        raw_code, desc, comment = m.group(1), m.group(2).strip(), m.group(3)
        yield raw_code, desc, (comment.strip() if comment else "")


def load_csv_dict(path, key_col=None):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    if key_col:
        return {r[key_col]: r for r in rows}
    return rows


def build_raw_db(raw_csv_path, out_path):
    if out_path.exists():
        out_path.unlink()
    conn = sqlite3.connect(out_path)
    conn.execute("""
        CREATE TABLE inspection_raw (
            inspection_id TEXT, dba_name TEXT, aka_name TEXT, license_no TEXT,
            facility_type TEXT, risk TEXT, address TEXT, city TEXT, state TEXT,
            zip TEXT, inspection_date TEXT, inspection_type TEXT, results TEXT,
            violations TEXT, latitude TEXT, longitude TEXT
        )
    """)
    with open(raw_csv_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append((
                row["Inspection ID"], row["DBA Name"], row["AKA Name"], row["License #"],
                row["Facility Type"], row["Risk"], row["Address"], row["City"], row["State"],
                row["Zip"], row["Inspection Date"], row["Inspection Type"], row["Results"],
                row["Violations"], row["Latitude"], row["Longitude"],
            ))
            if len(rows) >= 20000:
                conn.executemany("INSERT INTO inspection_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
                rows = []
        if rows:
            conn.executemany("INSERT INTO inspection_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.execute("CREATE INDEX idx_raw_license ON inspection_raw(license_no)")
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM inspection_raw").fetchone()[0]
    conn.close()
    print(f"raw.db: {n} rows in inspection_raw -> {out_path}")


def build_clean_db(raw_csv_path, facility_lookup_path, city_lookup_path,
                    license_fix_path, results_bucketed_path, violation_code_path,
                    out_path):
    if out_path.exists():
        out_path.unlink()

    facility_map = {r["raw_facility_type"]: r["canonical_facility_type"]
                     for r in load_csv_dict(facility_lookup_path)}
    city_map = {r["raw_city"]: r["canonical_city"] for r in load_csv_dict(city_lookup_path)}
    results_map = {r["raw_result"]: r["outcome_bucket"] for r in load_csv_dict(results_bucketed_path)}
    license_fix = load_csv_dict(license_fix_path, key_col="inspection_id")

    conn = sqlite3.connect(out_path)
    conn.execute("""
        CREATE TABLE inspection (
            inspection_id TEXT PRIMARY KEY, license_no TEXT, inspection_date TEXT,
            inspection_type TEXT, risk TEXT, raw_result TEXT, outcome_bucket TEXT,
            license_fix_status TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE violation_finding (
            inspection_id TEXT, violation_code TEXT, raw_code TEXT, era TEXT, comment TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE violation_code (
            violation_code TEXT PRIMARY KEY, raw_code TEXT, era TEXT,
            description TEXT, n_occurrences INTEGER
        )
    """)

    # establishment attributes: mode (most common) value per resolved license_no
    est_attr_counts = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    est_geo = {}  # license_no -> (lat, lon) from most recent inspection

    insp_rows = []
    vf_rows = []
    n_violation_entries = 0

    with open(raw_csv_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            insp_id = row["Inspection ID"]
            raw_license = row["License #"]
            fix = license_fix.get(insp_id)
            if fix and fix["fix_status"] == "recovered_name_addr":
                license_no = fix["resolved_license"]
                fix_status = fix["fix_status"]
            elif fix:
                license_no = raw_license  # still 0/blank - ambiguous or unresolved
                fix_status = fix["fix_status"]
            else:
                license_no = raw_license
                fix_status = "ok"

            raw_result = row["Results"]
            outcome_bucket = results_map[raw_result]

            insp_rows.append((
                insp_id, license_no, row["Inspection Date"], row["Inspection Type"],
                row["Risk"], raw_result, outcome_bucket, fix_status,
            ))

            # only build establishment rows for inspections with a real (non-0/blank) license
            if license_no and license_no != "0":
                canon_ft = facility_map.get(row["Facility Type"], row["Facility Type"])
                canon_city = city_map.get(row["City"], row["City"])
                attrs = est_attr_counts[license_no]
                attrs["dba_name"][row["DBA Name"]] += 1
                attrs["aka_name"][row["AKA Name"]] += 1
                attrs["address"][row["Address"]] += 1
                attrs["city"][canon_city] += 1
                attrs["state"][row["State"]] += 1
                attrs["zip"][row["Zip"]] += 1
                attrs["facility_type"][canon_ft] += 1
                if row["Latitude"] and row["Longitude"]:
                    est_geo[license_no] = (row["Latitude"], row["Longitude"])

            violations = row["Violations"]
            if violations:
                d = parse_date(row["Inspection Date"])
                era = era_for(d)
                for raw_code, desc, comment in parse_violations_field(violations):
                    violation_code = f"{raw_code}-{era.upper()}"
                    vf_rows.append((insp_id, violation_code, raw_code, era, comment))
                    n_violation_entries += 1

            if len(insp_rows) >= 20000:
                conn.executemany("INSERT INTO inspection VALUES (?,?,?,?,?,?,?,?)", insp_rows)
                insp_rows = []
            if len(vf_rows) >= 20000:
                conn.executemany("INSERT INTO violation_finding VALUES (?,?,?,?,?)", vf_rows)
                vf_rows = []

    if insp_rows:
        conn.executemany("INSERT INTO inspection VALUES (?,?,?,?,?,?,?,?)", insp_rows)
    if vf_rows:
        conn.executemany("INSERT INTO violation_finding VALUES (?,?,?,?,?)", vf_rows)

    conn.execute("""
        CREATE TABLE establishment (
            license_no TEXT PRIMARY KEY, dba_name TEXT, aka_name TEXT, address TEXT,
            city TEXT, state TEXT, zip TEXT, facility_type TEXT,
            latitude TEXT, longitude TEXT
        )
    """)
    est_rows = []
    for license_no, attrs in est_attr_counts.items():
        lat, lon = est_geo.get(license_no, (None, None))
        est_rows.append((
            license_no,
            attrs["dba_name"].most_common(1)[0][0],
            attrs["aka_name"].most_common(1)[0][0],
            attrs["address"].most_common(1)[0][0],
            attrs["city"].most_common(1)[0][0],
            attrs["state"].most_common(1)[0][0],
            attrs["zip"].most_common(1)[0][0],
            attrs["facility_type"].most_common(1)[0][0],
            lat, lon,
        ))
    conn.executemany("INSERT INTO establishment VALUES (?,?,?,?,?,?,?,?,?,?)", est_rows)

    vc_rows = [(r["violation_code"], r["raw_code"], r["era"], r["description"], int(r["n_occurrences"]))
               for r in load_csv_dict(violation_code_path)]
    conn.executemany("INSERT INTO violation_code VALUES (?,?,?,?,?)", vc_rows)

    conn.execute("CREATE INDEX idx_insp_license ON inspection(license_no)")
    conn.execute("CREATE INDEX idx_vf_insp ON violation_finding(inspection_id)")
    conn.execute("CREATE INDEX idx_vf_code ON violation_finding(violation_code)")
    conn.commit()

    n_insp = conn.execute("SELECT COUNT(*) FROM inspection").fetchone()[0]
    n_est = conn.execute("SELECT COUNT(*) FROM establishment").fetchone()[0]
    n_vf = conn.execute("SELECT COUNT(*) FROM violation_finding").fetchone()[0]
    n_vc = conn.execute("SELECT COUNT(*) FROM violation_code").fetchone()[0]
    conn.close()
    print(f"clean.db: {n_insp} inspection, {n_est} establishment, "
          f"{n_vf} violation_finding, {n_vc} violation_code -> {out_path}")


def main():
    if len(sys.argv) != 8:
        print(f"Usage: {sys.argv[0]} <raw_csv> <facility_type_lookup> <city_lookup> "
              f"<license_fix> <results_bucketed> <violation_code_lookup> <output_dir>")
        sys.exit(1)
    raw_csv, fac_lookup, city_lookup, license_fix, results_bucketed, vcode_lookup, out_dir = map(Path, sys.argv[1:])
    out_dir.mkdir(parents=True, exist_ok=True)
    build_raw_db(raw_csv, out_dir / "raw.db")
    build_clean_db(raw_csv, fac_lookup, city_lookup, license_fix, results_bucketed, vcode_lookup, out_dir / "clean.db")


if __name__ == "__main__":
    main()
