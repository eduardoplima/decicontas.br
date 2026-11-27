"""Recompute the selection funnel from the published files (standard library only).

Run from this directory: python verify_counts.py
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED_BIB = {"acm.bib": 175, "ieee.bib": 78, "scopus.bib": 229}


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ok = True

    def check(label: str, got, expected) -> None:
        nonlocal ok
        flag = "ok" if got == expected else "MISMATCH"
        ok = ok and got == expected
        print(f"{label:<45} {got!s:>6}  (expected {expected})  {flag}")

    for name, n in EXPECTED_BIB.items():
        text = (HERE / "search" / name).read_text(encoding="utf-8")
        check(f"search/{name} entries", len(re.findall(r"^@\w+\s*\{", text, re.M)), n)
    check("search/scopus_not_imported.csv", len(rows(HERE / "search" / "scopus_not_imported.csv")), 9)

    records = rows(HERE / "screening" / "records.csv")
    check("records", len(records), 473)
    by_source = Counter(r["source"] for r in records)
    check("records by source (ACM, IEEE, Scopus)",
          (by_source["ACM"], by_source["IEEE"], by_source["Scopus"]), (175, 78, 220))
    status = Counter(r["status"] for r in records)
    check("duplicated", status["Duplicated"], 40)
    check("rejected on title/abstract", status["Rejected"], 343)
    check("accepted on title/abstract", status["Accepted"], 90)
    final = Counter(r["final_decision"] for r in records)
    check("excluded at eligibility", final["excluded_eligibility"], 11)
    check("included", final["included"], 79)

    check("eligibility_exclusions.csv",
          len(rows(HERE / "screening" / "eligibility_exclusions.csv")), 11)
    extracted = rows(HERE / "extraction" / "extracted.csv")
    check("extraction/extracted.csv", len(extracted), 79)
    check("extraction/cache/*.json", len(list((HERE / "extraction" / "cache").glob("*.json"))), 79)
    bib = (HERE / "extraction" / "included_studies.bib").read_text(encoding="utf-8")
    check("extraction/included_studies.bib entries", len(re.findall(r"^@\w+\s*\{", bib, re.M)), 79)

    print("\nall counts match" if ok else "\nCOUNTS DO NOT MATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
