"""Fetch details about the co-authors, to find their discipline.

Usage: python fetch_coauthor_details.py [--all]

For the co-authors whose main institution since the earliest period on the
pages is a university, research institute or company (see
coauthor_fields.py), writes:

- coauthor_profiles.csv: their ORCID iD and the field most of their research
  is in, from OpenAlex, and when their ORCID record and other papers were
  last fetched
- coauthor_employments.csv: their public ORCID employment records:
  organisation, department and years (not role titles or anything else)
- coauthor_affiliations.csv: the affiliation texts that name their main
  institution on their other papers since then (the 50 most recent), with
  the number of papers and the latest year; fetched only for co-authors
  whose papers with the centre and ORCID record name no department

Only co-authors not fetched before are looked up, unless --all is given, so
a weekly refresh makes few requests. OpenAlex allows a limited number of
requests a day: when that is used up, what has been fetched is saved and the
rest is left for the next run.

Run after fetch_openalex.py; build_partners_page.py reads these files.
"""

import csv
import datetime
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from build_partners_page import (
    SINCE,
    read_colleagues,
    read_corrections,
    read_csv,
    read_person_merges,
)
from coauthor_fields import coauthors, names_institution

HERE = Path(__file__).resolve().parent
# Kinds of institution whose co-authors are sorted by their department
WITH_DEPARTMENTS = ("Universities", "Research institutes", "Companies")
OPENALEX = "https://api.openalex.org"
ORCID = "https://pub.orcid.org/v3.0"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "centre-for-digital-neurotechnology",
}
PROFILE_FIELDS = [
    "openalex_author_id",
    "orcid",
    "main_field",
    "employments_fetched",
    "works_fetched",
]
EMPLOYMENT_FIELDS = ["openalex_author_id", "organisation", "department", "start", "end"]
AFFILIATION_FIELDS = ["openalex_author_id", "affiliation", "papers", "latest_year"]
# Waits longer than this (in seconds) mean the daily quota is used up
LONGEST_WAIT = 120


class QuotaExceeded(Exception):
    """The server's daily quota of requests is used up."""


def get(url, tries=5):
    """JSON from url. When the server asks us to slow down (429) or fails
    (5xx), wait and try again, longer each time; raise QuotaExceeded when it
    asks us to wait longer than LONGEST_WAIT, as when a daily quota is used
    up."""
    request = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            if attempt == tries - 1 or (e.code != 429 and e.code < 500):
                if e.code == 429:
                    raise QuotaExceeded(url) from e
                raise
            asked = e.headers.get("Retry-After") or e.headers.get("X-RateLimit-Reset")
            wait = int(asked) if asked and asked.isdigit() else 5 * 2**attempt
            if wait > LONGEST_WAIT:
                raise QuotaExceeded(url) from e
            time.sleep(wait)
    return None


def fetch_profiles(author_ids):
    """{OpenAlex author ID: {"orcid", "main_field"}}."""
    out = {}
    for i in range(0, len(author_ids), 50):
        batch = author_ids[i : i + 50]
        url = f"{OPENALEX}/authors?" + urllib.parse.urlencode(
            {
                "filter": "openalex_id:" + "|".join(batch),
                "per-page": 50,
                "select": "id,orcid,topics",
            }
        )
        for a in get(url)["results"]:
            fields = Counter()
            for topic in a.get("topics") or []:
                fields[topic["field"]["display_name"]] += topic.get("count", 1)
            out[a["id"].rsplit("/", 1)[-1]] = {
                "orcid": (a.get("orcid") or "").rsplit("/", 1)[-1],
                "main_field": fields.most_common(1)[0][0] if fields else "",
            }
        time.sleep(0.3)
    return out


def year(date):
    return ((date or {}).get("year") or {}).get("value", "")


def fetch_employments(orcid):
    """[{"organisation", "department", "start", "end"}] from ORCID."""
    out = []
    for group in get(f"{ORCID}/{orcid}/employments").get("affiliation-group") or []:
        for summary in group.get("summaries") or []:
            e = summary.get("employment-summary") or {}
            out.append(
                {
                    "organisation": (e.get("organization") or {}).get("name", ""),
                    "department": e.get("department-name") or "",
                    "start": year(e.get("start-date")),
                    "end": year(e.get("end-date")),
                }
            )
    return out


def fetch_own_affiliations(author, institution, since):
    """{affiliation text: [papers, latest year]} on the author's own papers
    since the year since, for the texts that name the institution."""
    url = f"{OPENALEX}/works?" + urllib.parse.urlencode(
        {
            "filter": f"author.id:{author},publication_year:>{since - 1}",
            "per-page": 50,
            "sort": "publication_year:desc",
            "select": "id,publication_year,authorships",
        }
    )
    out = {}
    for work in get(url)["results"]:
        for a in work.get("authorships") or []:
            if not ((a.get("author") or {}).get("id") or "").endswith(author):
                continue
            for text in a.get("raw_affiliation_strings") or []:
                if names_institution(text, institution):
                    n, latest = out.get(text, (0, 0))
                    out[text] = (n + 1, max(latest, work.get("publication_year") or 0))
    return out


def write(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read(path):
    return read_csv(path) if path.exists() else []


def wanted_coauthors():
    """{OpenAlex author ID: (main institution, needs other papers)} for the
    co-authors at universities, research institutes and companies since the
    earliest period."""
    merges = {
        r["institution"]: r["use_name"]
        for r in read_csv(HERE / "institution_merges.csv")
    }
    employments = {}
    for r in read(HERE / "coauthor_employments.csv"):
        employments.setdefault(r["openalex_author_id"], []).append(r)
    out = {}
    for c in coauthors(
        read_csv(HERE / "openalex_affiliations.csv"),
        min(SINCE),
        merges,
        [
            (r["author"], r["institution"])
            for r in read_csv(HERE / "affiliation_exclusions.csv")
        ],
        read_person_merges(HERE / "person_merges.csv"),
        read_colleagues(HERE / "simula_colleagues.csv"),
        {
            r["institution"]: r["kind"]
            for r in read(HERE / "institution_kinds.csv")
            if r["kind"]
        },
        employments=employments,
        corrections=read_corrections(HERE / "coauthor_corrections.csv"),
    ):
        if c["kind"] in WITH_DEPARTMENTS and c["id"].startswith("A"):
            out[c["id"]] = (c["institution"], c["needs_other_papers"])
    return out


def main():
    refetch = "--all" in sys.argv[1:]
    today = datetime.date.today().isoformat()
    since = min(SINCE)
    wanted = wanted_coauthors()
    # What has been fetched before, for the co-authors still wanted
    profiles = (
        {}
        if refetch
        else {
            r["openalex_author_id"]: {f: r.get(f, "") for f in PROFILE_FIELDS}
            for r in read(HERE / "coauthor_profiles.csv")
            if r["openalex_author_id"] in wanted
        }
    )
    employments = (
        []
        if refetch
        else [
            r
            for r in read(HERE / "coauthor_employments.csv")
            if r["openalex_author_id"] in profiles
        ]
    )
    own = (
        []
        if refetch
        else [
            r
            for r in read(HERE / "coauthor_affiliations.csv")
            if r["openalex_author_id"] in profiles
        ]
    )
    new = sorted(set(wanted) - set(profiles))
    print(f"{len(wanted)} co-authors with an OpenAlex author ID, {len(new)} new")

    def save():
        write(
            HERE / "coauthor_profiles.csv",
            PROFILE_FIELDS,
            [profiles[a] for a in sorted(profiles)],
        )
        write(
            HERE / "coauthor_employments.csv",
            EMPLOYMENT_FIELDS,
            sorted(employments, key=lambda r: r["openalex_author_id"]),
        )
        write(
            HERE / "coauthor_affiliations.csv",
            AFFILIATION_FIELDS,
            sorted(own, key=lambda r: (r["openalex_author_id"], r["affiliation"])),
        )

    try:
        for a, p in fetch_profiles(new).items():
            profiles[a] = {
                "openalex_author_id": a,
                **p,
                "employments_fetched": "",
                "works_fetched": "",
            }
        for a in sorted(profiles):
            p = profiles[a]
            if p["employments_fetched"]:
                continue
            if p["orcid"]:
                try:
                    found = fetch_employments(p["orcid"])
                except (
                    OSError,
                    ValueError,
                ) as e:  # one failed record should not stop the rest
                    print(f"ORCID {p['orcid']}: {e}")
                    continue
                employments += [{"openalex_author_id": a, **e} for e in found]
                time.sleep(0.1)
            p["employments_fetched"] = today
        for a in sorted(profiles):
            p = profiles[a]
            institution, needed = wanted[a]
            if p["works_fetched"] or not needed:
                continue
            try:
                found = fetch_own_affiliations(a, institution, since)
            except (
                OSError,
                ValueError,
            ) as e:  # one failed author should not stop the rest
                print(f"OpenAlex works of {a}: {e}")
                continue
            own += [
                {
                    "openalex_author_id": a,
                    "affiliation": t,
                    "papers": n,
                    "latest_year": y,
                }
                for t, (n, y) in sorted(found.items())
            ]
            p["works_fetched"] = today
            time.sleep(0.2)
    except QuotaExceeded:
        print(
            "OpenAlex's daily quota is used up: saved what was fetched; "
            "run again tomorrow for the rest"
        )
    save()
    waiting = sum(
        1 for a, p in profiles.items() if wanted[a][1] and not p["works_fetched"]
    )
    print(
        f"{sum(bool(p['orcid']) for p in profiles.values())} with an ORCID iD, "
        f"{len({e['openalex_author_id'] for e in employments if e['department']})} "
        f"with a department in ORCID, "
        f"{len({r['openalex_author_id'] for r in own})} with affiliation texts from "
        f"their other papers; {len(set(wanted) - set(profiles)) + waiting} still to fetch"
    )


if __name__ == "__main__":
    main()
