"""Builds demo/data.json for the static explorer from the extracted course sheets.

    python demo/build_data.py

Same inputs and the same prerequisite parsing as part2_test/import_test.py, so
the explorer shows what the Neo4j graph contains, without needing a database.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SHEETS = ROOT / "part2_test"

# sheet file prefix -> (group shown in the explorer, is this a specialization?)
GROUPS = {
    "math": ("Mathematics", False),
    "ComputerScience": ("Computer Science", False),
    "ScienceEngineering": ("Science & Engineering", False),
    "Gen_Ed": ("General Education", False),
    "Elective": ("Electives", False),
    "Minor": ("Minor", False),
    "AI": ("AI", True),
    "BDA": ("Big Data Analytics", True),
    "SE": ("Software Engineering", True),
    "CSys": ("Computer Systems", True),
    "ACS": ("Advanced Computer Science", True),
}


def course_codes(text: str) -> list[str]:
    return sorted({d + n for d, n in re.findall(r"\b([A-Z]{2,4})\s*(\d{4})\b", str(text).upper())})


def clean(value) -> str:
    value = "" if pd.isna(value) else str(value).strip()
    return "" if value.upper() in {"NONE", "NAN", "EMPTY"} else value


def main() -> None:
    courses: dict[str, dict] = {}
    for prefix, (group, is_spec) in GROUPS.items():
        df = pd.read_excel(SHEETS / f"{prefix}_test.xlsx")
        for _, row in df.iterrows():
            code = clean(row["Course Code"]).replace(" ", "").upper()
            if not code:
                continue
            c = courses.setdefault(code, {"code": code, "title": "", "credits": None,
                                          "prereqText": "", "groups": []})
            c["title"] = c["title"] or clean(row["Course Title"])
            credits = clean(row["Course Credits"])
            if c["credits"] is None and credits:
                try:
                    c["credits"] = int(float(credits))
                except ValueError:
                    pass
            c["prereqText"] = c["prereqText"] or clean(row["Prerequisites"])
            tag = {"group": group, "specialization": is_spec, "role": clean(row["Category"])}
            if tag not in c["groups"]:
                c["groups"].append(tag)

    edges = []
    for code, c in courses.items():
        for pre in course_codes(c["prereqText"]):
            if pre != code:
                edges.append({"course": code, "requires": pre})

    # Prerequisites mentioned in the catalog but not listed as courses of the program.
    for pre in {e["requires"] for e in edges} - set(courses):
        courses[pre] = {"code": pre, "title": "", "credits": None, "prereqText": "",
                        "groups": [], "external": True}

    data = {
        "program": "BSc Computer Science (2023–2025 catalog)",
        "courses": sorted(courses.values(), key=lambda c: c["code"]),
        "edges": sorted(edges, key=lambda e: (e["course"], e["requires"])),
    }
    out = Path(__file__).resolve().parent / "data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(data['courses'])} courses, {len(edges)} prerequisite links -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
