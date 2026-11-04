"""Fetch Simula's research projects from the public API of simula.no.

Usage: python fetch_simula_projects.py [output_dir]

Simula's website (https://www.simula.no/research/projects) is built on a
Drupal content system whose JSON:API is public. Projects have structured
fields for title, duration, completion and research area; partners, funding
and contacts are only in the description text, under headings such as
"Partners", "All partners", "Funding source" and "Contact". These sections
are extracted as text and need checking by hand.

A project is linked to a centre investigator when the investigator's name or
email address (investigator_emails.csv) appears in its description.

Writes to output_dir:

- simula_projects.csv: one row per project: Simula's ID, title, URL,
  duration, completed, research areas, centre investigators, and the funding
  and partner sections as text. Contact email addresses on the pages are only
  used to recognise the investigators, and are not stored
"""

import csv
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://cms.simula.no/jsonapi/node/project"
SITE = "https://www.simula.no"
NVA_DIR = Path(__file__).resolve().parent.parent / "nva"

sys.path.insert(0, str(NVA_DIR))
import fetch_log

from fetch_nva import ascii_fold

FIELDS = [
    "simula_id",
    "title",
    "url",
    "duration",
    "completed",
    "research_areas",
    "investigators",
    "funding",
    "partners",
]
SECTIONS = {
    "funding": re.compile(r"^funding( source)?:?$", re.IGNORECASE),
    "partners": re.compile(r"partners:?$", re.IGNORECASE),
}


def get(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def fetch_projects():
    """Return all projects, with research area names in "_areas"."""
    url = f"{API}?" + urllib.parse.urlencode(
        {"page[limit]": 50, "include": "field_research_area"}
    )
    projects, names = [], {}
    while url:
        page = get(url)
        projects.extend(page["data"])
        for item in page.get("included", []):
            names[item["id"]] = item["attributes"].get("name", "")
        url = page.get("links", {}).get("next", {}).get("href")
        time.sleep(0.3)
    for p in projects:
        areas = p.get("relationships", {}).get("field_research_area", {}).get("data")
        p["_areas"] = [names.get(a["id"], "") for a in areas or []]
    return projects


def to_text(fragment):
    """Plain text of an HTML fragment, one line per block or list item."""
    fragment = re.sub(r"<br\s*/?>|</(p|li|h[1-6]|div)>", "\n", fragment)
    text = html.unescape(re.sub(r"<[^>]+>", "", fragment))
    lines = (re.sub(r"\s+", " ", line).strip() for line in text.splitlines())
    return [line for line in lines if line]


def sections(body):
    """Return {"funding": [lines], "partners": [lines]} from a description,
    taking the text under each matching h2/h3 heading up to the next heading
    or a "Contact" line, without email addresses."""
    found = {}
    parts = re.split(r"<h[23][^>]*>(.*?)</h[23]>", body, flags=re.DOTALL)
    # parts alternates: text, heading, text, heading, text, ...
    for heading, content in zip(parts[1::2], parts[2::2]):
        title = " ".join(to_text(heading))
        for key, pattern in SECTIONS.items():
            if pattern.search(title) and key not in found:
                lines = []
                for line in to_text(content):
                    if line.lower().rstrip(":") in ("contact", "contacts"):
                        break
                    if "@" not in line:
                        lines.append(line)
                found[key] = lines
    return found


def investigators_in(text, emails, names):
    """Investigators whose email or name (first and last name) appears in text."""
    folded = ascii_fold(text).lower()
    found = []
    for name in names:
        tokens = ascii_fold(name).lower().replace(".", "").split()
        if emails.get(name, "\0") in folded or f"{tokens[0]} {tokens[-1]}" in folded:
            found.append(name)
    return found


def to_row(project, emails, names):
    a = project["attributes"]
    body = (a.get("body") or {}).get("value") or ""
    text = "\n".join(to_text(body))
    found = sections(body)
    return {
        "simula_id": a.get("drupal_internal__nid", ""),
        "title": a["title"],
        "url": SITE + (a.get("path") or {}).get("alias", ""),
        "duration": (a.get("field_study_duration") or "").strip(),
        "completed": "yes" if a.get("field_project_completed") else "no",
        "research_areas": "; ".join(x for x in project["_areas"] if x),
        "investigators": "; ".join(
            investigators_in(a["title"] + "\n" + text, emails, names)
        ),
        "funding": " | ".join(found.get("funding", [])),
        "partners": " | ".join(found.get("partners", [])),
    }


def main():
    output_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    here = Path(__file__).resolve().parent
    with (here / "investigator_emails.csv").open(encoding="utf-8") as f:
        emails = {row["name"]: row["email"] for row in csv.DictReader(f)}
    with (NVA_DIR / "investigators.csv").open(encoding="utf-8") as f:
        names = [r["name"] for r in csv.DictReader(f) if "Investigator" in r["role"]]

    rows = [to_row(p, emails, names) for p in fetch_projects()]
    rows.sort(key=lambda r: r["title"].lower())
    with (output_dir / "simula_projects.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    fetch_log.record(output_dir / "fetched.csv", "simula_projects")
    linked = sum(1 for r in rows if r["investigators"])
    print(f"{len(rows)} projects, {linked} linked to centre investigators")


if __name__ == "__main__":
    main()
