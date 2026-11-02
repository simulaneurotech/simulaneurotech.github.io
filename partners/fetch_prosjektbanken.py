"""Look up the centre's Research Council of Norway projects in Prosjektbanken.

Usage: python fetch_prosjektbanken.py [output_dir]

Prosjektbanken (https://prosjektbanken.forskningsradet.no) is the Research
Council of Norway's project database. Each project page embeds its data as
JSON (the page's __NEXT_DATA__); this is the website's own data, not a
documented API, so it may change. Projects are looked up by the grant
numbers in centre_projects.csv for projects funded by the Research Council.
Prosjektbanken has no partner institutions, and very new projects may be
missing.

Writes to output_dir:

- prosjektbanken_projects.csv: one row per grant: found or not, English and
  Norwegian title, project leader, the institution leading the project and
  its full organisation path, start and end year, total funding of the whole
  project (NOK, including any partners' shares), programmes, application
  type, funding ministries, summary and the results reported to the Research
  Council
"""

import csv
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = "https://prosjektbanken.forskningsradet.no/project/FORISS/{grant}"
FIELDS = [
    "grant",
    "found",
    "title",
    "title_no",
    "lead",
    "lead_institution",
    "organisation",
    "start",
    "end",
    "total_funding_nok",
    "programmes",
    "application_type",
    "funding_ministries",
    "summary",
    "achieved_effects",
]


def grants(rows):
    """Grant numbers (six or more digits) of projects funded by the Research
    Council of Norway, in order."""
    found = []
    for r in rows:
        if "Research Council of Norway" in r["funders"]:
            for g in re.findall(r"\b\d{6,}\b", r["grants"]):
                if g not in found:
                    found.append(g)
    return found


def page_project(html):
    """The project data embedded in a Prosjektbanken project page, or None
    if the project was not found."""
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not m:
        return None
    state = json.loads(m.group(1))["props"]["pageProps"]["initialState"]["PROJECT"]
    if state.get("httpStatus") != 200:
        return None
    return state.get("project")


def institution(path):
    """The institution in an organisation path such as ["UoH-sektor",
    "Universiteter", "UNIVERSITETET I OSLO", faculty, department], in
    normal capitalisation."""
    name = path[2] if len(path) > 2 else path[-1]
    small = {"i", "og", "for", "as"}
    words = name.split()
    if name.isupper():
        words = [
            w
            if w.lower() == "as" and i == len(words) - 1
            else (w.lower() if w.lower() in small and i else w.capitalize())
            for i, w in enumerate(words)
        ]
    return " ".join(words)


def to_row(grant, project):
    if not project:
        return {"grant": grant, "found": "no"}
    activities = [a["activity"] for a in project.get("pastActivities", [])]
    if project.get("currentActivity"):
        activities.append(project["currentActivity"]["activity"])
    programmes = list(dict.fromkeys(a.split("-")[0] for a in activities))
    duration = project.get("duration") or {}
    return {
        "grant": grant,
        "found": "yes",
        "title": project.get("title", ""),
        "title_no": project.get("alternativeTitle", ""),
        "lead": project.get("leadName", ""),
        "lead_institution": "; ".join(
            institution(o) for o in project.get("organisation", []) if o
        ),
        "organisation": "; ".join(
            " > ".join(o) for o in project.get("organisation", []) if o
        ),
        "start": duration.get("startYear", ""),
        "end": duration.get("endYear", ""),
        "total_funding_nok": project.get("totalFunding") or "",
        "programmes": "; ".join(programmes),
        "application_type": "; ".join(
            " – ".join(t) for t in project.get("applicationTypes", [])
        ),
        "funding_ministries": "; ".join(project.get("fundingBodies", [])),
        "summary": project.get("summary", ""),
        "achieved_effects": project.get("achievedEffects", ""),
    }


def fetch(grant):
    request = urllib.request.Request(
        URL.format(grant=grant), headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def main():
    output_dir = Path(sys.argv[1] if len(sys.argv) > 1 else HERE)
    with (HERE / "centre_projects.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for grant in grants(rows):
        out.append(to_row(grant, page_project(fetch(grant))))
        time.sleep(0.5)
    with (output_dir / "prosjektbanken_projects.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)
    found = [r for r in out if r["found"] == "yes"]
    print(f"{len(out)} grants, {len(found)} found in Prosjektbanken")
    for r in out:
        print(
            f"  {r['grant']}: "
            + (
                f"{r['title'][:50]} | NOK {r['total_funding_nok'] or '?'} | {r['programmes']}"
                if r["found"] == "yes"
                else "not found"
            )
        )


if __name__ == "__main__":
    main()
