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

Two follow-up fixes added after the first pass (see notes/S5_change_summary.md
"known limitations" and the discussion that prompted them):

1. City backfill: a license's establishment row previously took the mode of
   City across all its inspections, including blank/"Inactive" values, which
   could win the mode even when a real city was recorded on other inspections
   of the same establishment. Now blank/"Inactive" are excluded from the mode
   unless that license has literally no other value to offer.
2. Synthetic IDs for genuinely unresolved licenses: the 638 rows where
   license_results found no other record at all previously all collapsed onto
   the literal raw value ("0" or blank), so two unrelated one-off venues could
   still collide under the same key. They're now grouped among themselves by
   normalized (name, address) - so repeat inspections of the same never-
   licensed place (e.g. the soup kitchen example in the Phase-I report) stay
   linked - and each resulting group gets a synthetic license_no
   (SYN-000001, ...) instead of colliding on "0". This does not invent a real
   license number; it just stops accidental collisions between different
   establishments.

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

BLANK_CITY_VALUES = {"", "inactive"}


def normalize(s):
    return re.sub(r"\s+", " ", (s or "").strip().upper())


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def build_synthetic_license_map(raw_csv_path, license_fix):
    """For inspection_ids whose license_fix_status is 'unresolved', group them
    by normalized (address, name) - trying both DBA and AKA as the name - so
    repeat inspections of the same never-licensed place get the same synthetic
    ID instead of each colliding on the raw '0'/blank value. Returns
    {inspection_id: synthetic_license_no}.
    """
    uf = UnionFind()
    unresolved_ids = []
    key_of = {}  # inspection_id -> list of (addr, name) keys
    with open(raw_csv_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            insp_id = row["Inspection ID"]
            fix = license_fix.get(insp_id)
            if not fix or fix["fix_status"] != "unresolved":
                continue
            addr = normalize(row["Address"])
            names = {normalize(row["DBA Name"]), normalize(row["AKA Name"])} - {""}
            keys = [f"{addr}|{n}" for n in names] or [f"{addr}|__NONAME__{insp_id}"]
            key_of[insp_id] = keys
            unresolved_ids.append(insp_id)
            for k in keys:
                uf.union(("row", insp_id), ("key", k))

    group_id = {}
    next_idx = 1
    result = {}
    for insp_id in unresolved_ids:
        root = uf.find(("row", insp_id))
        if root not in group_id:
            group_id[root] = f"SYN-{next_idx:06d}"
            next_idx += 1
        result[insp_id] = group_id[root]
    return result, len(group_id)

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
    synthetic_license, n_synthetic_groups = build_synthetic_license_map(raw_csv_path, license_fix)
    print(f"synthetic licenses: {len(synthetic_license)} unresolved inspections -> {n_synthetic_groups} groups")

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
            elif fix and fix["fix_status"] == "unresolved":
                license_no = synthetic_license[insp_id]  # e.g. SYN-000042, not raw '0'
                fix_status = fix["fix_status"]
            elif fix:
                license_no = raw_license  # still 0/blank - ambiguous
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
            # (synthetic SYN-###### IDs count as real here - they exist precisely so these
            # rows get an establishment instead of colliding on '0')
            if license_no and license_no != "0":
                canon_ft = facility_map.get(row["Facility Type"], row["Facility Type"])
                canon_city = city_map.get(row["City"], row["City"])
                attrs = est_attr_counts[license_no]
                attrs["dba_name"][row["DBA Name"]] += 1
                attrs["aka_name"][row["AKA Name"]] += 1
                attrs["address"][row["Address"]] += 1
                # Blank/"Inactive" City shouldn't win the mode over a real value recorded
                # on another inspection of the same establishment - only counted here if
                # nothing better turns up (see "city" fallback logic when building est_rows).
                if canon_city.strip().lower() not in BLANK_CITY_VALUES:
                    attrs["city_valid"][canon_city] += 1
                attrs["city_all"][canon_city] += 1
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
    n_city_backfilled = 0
    for license_no, attrs in est_attr_counts.items():
        lat, lon = est_geo.get(license_no, (None, None))
        # Prefer a real city seen on any of this license's inspections; only fall back
        # to blank/"Inactive" if literally nothing better was ever recorded for it.
        if attrs["city_valid"]:
            city = attrs["city_valid"].most_common(1)[0][0]
            if attrs["city_all"].most_common(1)[0][0].strip().lower() in BLANK_CITY_VALUES:
                n_city_backfilled += 1
        else:
            city = attrs["city_all"].most_common(1)[0][0]
        est_rows.append((
            license_no,
            attrs["dba_name"].most_common(1)[0][0],
            attrs["aka_name"].most_common(1)[0][0],
            attrs["address"].most_common(1)[0][0],
            city,
            attrs["state"].most_common(1)[0][0],
            attrs["zip"].most_common(1)[0][0],
            attrs["facility_type"].most_common(1)[0][0],
            lat, lon,
        ))
    conn.executemany("INSERT INTO establishment VALUES (?,?,?,?,?,?,?,?,?,?)", est_rows)
    print(f"city backfilled from a sibling inspection for {n_city_backfilled} establishments "
          f"that would otherwise have shown blank/Inactive")

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
