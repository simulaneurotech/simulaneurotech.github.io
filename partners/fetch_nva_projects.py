"""Fetch the investigators' research projects from NVA.

Usage: python fetch_nva_projects.py [output_dir] [coauthors_dir]

NVA (which replaced Cristin) has a project register with participants,
dates, funding (with grant numbers) and the coordinating institution. It is
incomplete: not all projects are registered, and some investigators have
none. Projects are found for every Cristin ID of each investigator in
../nva/publications/cristin_ids.csv.

Writes to output_dir (by default this folder):

- nva_projects.csv: one row per project: NVA project ID, title, start and
  end year, funding (funder and grant number), coordinating institution,
  number of participants, and centre investigators taking part

and to coauthors_dir (by default the co-author data, see
../nva/coauthor_data.py), leaving out people who have opted out:

- nva_project_participants.csv: one row per participant per project, with
  their unit (department) and the institution it belongs to
"""

import csv
import sys
import time
from pathlib import Path

NVA_DIR = Path(__file__).resolve().parent.parent / "nva"

sys.path.insert(0, str(NVA_DIR))
import fetch_log

import coauthor_data
from fetch_nva import API, get, last_segment

PROJECT_FIELDS = [
    "nva_project_id",
    "title",
    "start",
    "end",
    "funding",
    "coordinator",
    "n_participants",
    "investigators",
]
PARTICIPANT_FIELDS = [
    "nva_project_id",
    "cristin_person_id",
    "name",
    "role",
    "institution_id",
    "institution",
    "unit",
]


def label(labels):
    """English label if there is one, else any."""
    if isinstance(labels, str):
        return labels
    labels = labels or {}
    return labels.get("en") or next(iter(labels.values()), "")


def projects_of(person_id):
    projects, page = [], 1
    while True:
        result = get(
            f"{API}/cristin/project",
            {"participant": person_id, "results": 100, "page": page},
        )
        projects.extend(result.get("hits", []))
        if not result.get("nextResults"):
            return projects
        page += 1
        time.sleep(0.2)


def funding(project):
    parts = []
    for f in project.get("funding", []):
        source = label(f.get("labels")) or last_segment(f.get("source", ""))
        parts.append(f"{source} {f.get('identifier', '')}".strip())
    return "; ".join(parts)


def institution_names(ids):
    """Return {institution ID: name} from NVA's organisation register."""
    names = {}
    for institution_id in sorted(ids, key=int):
        organization = get(f"{API}/cristin/organization/{institution_id}.0.0.0")
        names[institution_id] = label(organization.get("labels"))
        time.sleep(0.2)
    return names


def participants(project, names=None):
    """One row per participant role; institution is the top-level
    institution from names ({institution ID: name}) when given."""
    names = names or {}
    rows = []
    for c in project.get("contributors", []):
        identity = c.get("identity", {})
        name = " ".join(
            x for x in (identity.get("firstName"), identity.get("lastName")) if x
        )
        for role in c.get("roles", []) or [{}]:
            organization = role.get("affiliation", {}) if isinstance(role, dict) else {}
            institution_id = last_segment(organization.get("id", "")).split(".")[0]
            unit = label(organization.get("labels"))
            rows.append(
                {
                    "nva_project_id": last_segment(project["id"]),
                    "cristin_person_id": last_segment(identity.get("id", "")),
                    "name": name,
                    "role": role.get("type", "") if isinstance(role, dict) else "",
                    "institution_id": institution_id,
                    "institution": names.get(institution_id, unit),
                    "unit": unit,
                }
            )
    return rows


def to_row(project, investigators):
    return {
        "nva_project_id": last_segment(project["id"]),
        "title": label(project.get("title")),
        "start": str(project.get("startDate") or "")[:4],
        "end": str(project.get("endDate") or "")[:4],
        "funding": funding(project),
        "coordinator": label(
            (project.get("coordinatingInstitution") or {}).get("labels")
        ),
        "n_participants": len(project.get("contributors", [])),
        "investigators": "; ".join(investigators),
    }


def main():
    output_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    coauthors_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else coauthor_data.PARTNERS
    with (NVA_DIR / "publications" / "cristin_ids.csv").open(encoding="utf-8") as f:
        people = [
            (
                r["name"],
                [
                    r["cristin_person_id"],
                    *[i for i in r["extra_cristin_ids"].split(";") if i],
                ],
            )
            for r in csv.DictReader(f)
            if r["cristin_person_id"]
        ]

    projects, members = {}, {}
    for name, ids in people:
        for pid in ids:
            for project in projects_of(pid):
                projects[project["id"]] = project
                members.setdefault(project["id"], [])
                if name not in members[project["id"]]:
                    members[project["id"]].append(name)

    order = sorted(projects, key=lambda k: (str(projects[k].get("startDate")), k))
    with (output_dir / "nva_projects.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PROJECT_FIELDS)
        writer.writeheader()
        writer.writerows(to_row(projects[k], members[k]) for k in order)
    with (coauthors_dir / "nva_project_participants.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=PARTICIPANT_FIELDS)
        writer.writeheader()
        ids = {
            r["institution_id"]
            for k in order
            for r in participants(projects[k])
            if r["institution_id"].isdigit()
        }
        names = institution_names(ids)
        for k in order:
            writer.writerows(
                coauthor_data.drop_opted_out(participants(projects[k], names))
            )
    fetch_log.record(output_dir / "fetched.csv", "nva_projects")
    shared = sum(1 for k in order if len(members[k]) > 1)
    print(f"{len(projects)} projects, {shared} with two or more investigators")


if __name__ == "__main__":
    main()
