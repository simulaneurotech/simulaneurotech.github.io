"""Fetch publications and author lists from NVA (Nasjonalt vitenarkiv).

Usage: python fetch_nva.py [investigators.csv] [publications_dir] [contributors_dir]

NVA replaced Cristin and keeps Cristin's person IDs, and the Cristin result ID
of records registered there. For each investigator, the person with a Simula,
SimulaMet or Simula UiB affiliation is found, and all their results are
fetched, together with those of any extra Cristin IDs (duplicate profiles) in
the extra_cristin_ids column of investigators.csv, separated by semicolons.

Writes to publications_dir:

- <Name>.csv: one file per person: year, title, category, journal, DOI,
  result ID (the Cristin result ID, or the NVA identifier for records without
  one), NVA identifier and venue (the journal; for a chapter or conference
  paper "In: " the book or proceedings and its series; for a book the
  publisher and series)
- cristin_ids.csv: the Cristin person IDs used for each name

and to contributors_dir:

- contributors.csv: one row per author per publication (authors only, not
  editors or other roles)
- institutions.csv: names of the institutions authors belong to
- chapters.csv: for each chapter, the NVA record of the book it is part of
- editors.csv: the editors of those books

Some chapter records list the book's editors among the authors; the editors
are used by publication_data.py to remove them.
"""

import csv
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import fetch_log

API = "https://api.nva.unit.no"

# Simula (Simula Research Laboratory), SimulaMet, Simula UiB
SIMULA_INSTITUTIONS = {"7498", "20277", "20428"}

# NVA publication types to keep, with the category names used before (from
# Cristin): journal articles, conference papers, chapters and books
CATEGORIES = {
    "AcademicArticle": "Academic article",
    "AcademicLiteratureReview": "Academic literature review",
    "AcademicChapter": "Academic chapter/article/Conference paper",
    "NonFictionChapter": "Chapter",
    "AcademicMonograph": "Academic monograph",
    "Textbook": "Textbook",
    "NonFictionMonograph": "Non-fiction book",
    "ReportWorkingPaper": "Compendium",
}
CHAPTER_TYPES = {"AcademicChapter", "NonFictionChapter"}

FIELDS = [
    "year",
    "title",
    "category",
    "journal",
    "doi",
    "cristin_result_id",
    "nva_id",
    "venue",
]
CONTRIBUTOR_FIELDS = [
    "cristin_result_id",
    "order",
    "cristin_person_id",
    "first_name",
    "surname",
    "institutions",
]
SURNAME_PARTICLES = {"van", "von", "der", "den", "de", "di", "da", "del", "la", "le"}


def get(url, params=None):
    """Return the parsed JSON response for an NVA API GET request."""
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def ascii_fold(text):
    text = text.translate(str.maketrans({"æ": "ae", "ø": "o", "Æ": "Ae", "Ø": "O"}))
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def file_stem(name):
    """Return the per-person CSV file name (without .csv) for name."""
    return ascii_fold(name).replace(" ", "_").replace(".", "")


def last_segment(url):
    return url.rstrip("/").rsplit("/", 1)[-1] if url else ""


def split_name(name):
    """Split a full name into (first name, surname); surname particles such
    as "van der" stay with the surname."""
    tokens = name.split()
    if len(tokens) < 2:
        return "", name.strip()
    i = len(tokens) - 1
    while i > 1 and tokens[i - 1].lower() in SURNAME_PARTICLES:
        i -= 1
    return " ".join(tokens[:i]), " ".join(tokens[i:])


# People


def name_queries(name):
    """Search strings to try: full name, then without initials, then ASCII-folded."""
    without_initials = re.sub(r"\b\w\.\s*", "", name).strip()
    queries = [name, without_initials, ascii_fold(without_initials)]
    return list(dict.fromkeys(queries))


def is_simula_affiliated(person):
    return any(
        last_segment(a.get("organization", "")).split(".")[0] in SIMULA_INSTITUTIONS
        for a in person.get("affiliations", [])
    )


def count_results(person_id):
    return get(f"{API}/search/resources", {"contributor": person_id, "size": 1}).get(
        "totalHits", 0
    )


def find_person(name):
    """Return the Cristin person ID for name with a Simula affiliation, or None.
    If several match, the one with most results is used."""
    for query in name_queries(name):
        people = get(f"{API}/cristin/person", {"name": query, "results": 100})
        ids = [
            last_segment(p["id"])
            for p in people.get("hits", [])
            if is_simula_affiliated(p)
        ]
        if ids:
            return max(ids, key=count_results)
    return None


# Publications


def search_results(person_id):
    """Return all NVA records with person_id as a contributor."""
    hits = []
    url = f"{API}/search/resources?" + urllib.parse.urlencode(
        {"contributor": person_id, "size": 100, "from": 0, "aggregation": "none"}
    )
    while url:
        page = get(url)
        hits.extend(page.get("hits", []))
        url = page.get("nextResults") if page.get("hits") else None
        time.sleep(0.2)
    return hits


def instance_type(hit):
    return hit["entityDescription"]["reference"]["publicationInstance"]["type"]


def result_id(hit):
    """The Cristin result ID, or the NVA identifier if the record has none."""
    for identifier in hit.get("additionalIdentifiers", []):
        if identifier.get("type") == "CristinIdentifier":
            return identifier["value"]
    return hit["identifier"]


def venue(context):
    """Where a publication appeared, from its NVA publication context."""
    if context.get("type") in ("Journal", "UnconfirmedJournal"):
        return context.get("name") or context.get("title") or ""
    if context.get("type") == "Anthology":
        book = context.get("entityDescription") or {}
        inner = (book.get("reference") or {}).get("publicationContext") or {}
        series = (inner.get("series") or {}).get("name", "")
        title = book.get("mainTitle", "")
        if not title:
            return series
        return f"In: {title}" + (f" ({series})" if series else "")
    if context.get("type") == "Book":
        parts = [
            (context.get("publisher") or {}).get("name", ""),
            (context.get("series") or {}).get("name", ""),
        ]
        return ", ".join(p for p in parts if p)
    return ""


def to_row(hit):
    description = hit["entityDescription"]
    reference = description["reference"]
    context = reference.get("publicationContext", {})
    journal = ""
    if context.get("type") in ("Journal", "UnconfirmedJournal"):
        journal = context.get("name") or context.get("title") or ""
    return {
        "year": description.get("publicationDate", {}).get("year", ""),
        "title": description.get("mainTitle", ""),
        "category": CATEGORIES[instance_type(hit)],
        "journal": journal,
        "doi": reference.get("doi", ""),
        "cristin_result_id": result_id(hit),
        "nva_id": hit["identifier"],
        "venue": venue(context),
    }


def contributor_rows(hit):
    rows = []
    for c in hit["entityDescription"].get("contributors", []):
        if c.get("role", {}).get("type") != "Creator":
            continue
        identity = c.get("identity", {})
        first, surname = split_name(identity.get("name", ""))
        person = identity.get("id", "")
        institutions = dict.fromkeys(
            last_segment(a.get("id", "")).split(".")[0]
            for a in c.get("affiliations", [])
            if a.get("id")
        )
        rows.append(
            {
                "cristin_result_id": result_id(hit),
                "order": c.get("sequence", ""),
                "cristin_person_id": last_segment(person)
                if "/cristin/person/" in person
                else "",
                "first_name": first,
                "surname": surname,
                "institutions": ";".join(institutions),
            }
        )
    return rows


def book_editors(url):
    """Return (Cristin person ID, first name, surname) for the editors of a book."""
    book = get(url)
    editors = []
    for c in (book.get("entityDescription") or {}).get("contributors", []):
        if c.get("role", {}).get("type") == "Editor":
            identity = c.get("identity", {})
            person = identity.get("id", "")
            pid = last_segment(person) if "/cristin/person/" in person else ""
            editors.append((pid, *split_name(identity.get("name", ""))))
    return editors


def institution_name(institution_id):
    organization = get(f"{API}/cristin/organization/{institution_id}.0.0.0")
    labels = organization.get("labels", {})
    name = labels.get("en") or next(iter(labels.values()), "")
    return {
        "cristin_institution_id": institution_id,
        "name": name,
        "country": organization.get("country", ""),
    }


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    investigators_csv = Path(sys.argv[1] if len(sys.argv) > 1 else "investigators.csv")
    publications_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "publications")
    contributors_dir = Path(sys.argv[3] if len(sys.argv) > 3 else "contributors")
    publications_dir.mkdir(exist_ok=True)
    contributors_dir.mkdir(exist_ok=True)

    with investigators_csv.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    ids, kept = [], {}
    for row in rows:
        name = row["name"]
        extra_ids = [i for i in row.get("extra_cristin_ids", "").split(";") if i]
        person_id = find_person(name)
        results = {}
        if person_id is None:
            print(f"{name}: no Simula-affiliated person found in NVA")
        else:
            for pid in [person_id, *extra_ids]:
                for hit in search_results(pid):
                    if instance_type(hit) in CATEGORIES:
                        results[hit["identifier"]] = hit
            print(f"{name}: Cristin person ID {person_id}, {len(results)} results")
        kept.update(results)
        write_csv(
            publications_dir / f"{file_stem(name)}.csv",
            FIELDS,
            sorted(
                (to_row(h) for h in results.values()),
                key=lambda r: str(r["year"]),
                reverse=True,
            ),
        )
        ids.append(
            {
                "name": name,
                "cristin_person_id": person_id or "",
                "extra_cristin_ids": ";".join(extra_ids),
                "n_results": len(results),
            }
        )
    write_csv(
        publications_dir / "cristin_ids.csv",
        ["name", "cristin_person_id", "extra_cristin_ids", "n_results"],
        ids,
    )

    contributors = [row for hit in kept.values() for row in contributor_rows(hit)]
    write_csv(contributors_dir / "contributors.csv", CONTRIBUTOR_FIELDS, contributors)

    institution_ids = sorted(
        {i for row in contributors for i in row["institutions"].split(";") if i},
        key=int,
    )
    write_csv(
        contributors_dir / "institutions.csv",
        ["cristin_institution_id", "name", "country"],
        [institution_name(i) for i in institution_ids],
    )

    chapters = [
        {
            "cristin_result_id": result_id(hit),
            "part_of": hit["entityDescription"]["reference"]
            .get("publicationContext", {})
            .get("id", ""),
        }
        for hit in kept.values()
        if instance_type(hit) in CHAPTER_TYPES
    ]
    write_csv(
        contributors_dir / "chapters.csv", ["cristin_result_id", "part_of"], chapters
    )

    editors = []
    for url in sorted({c["part_of"] for c in chapters if c["part_of"]}):
        for pid, first, surname in book_editors(url):
            editors.append(
                {
                    "part_of": url,
                    "cristin_person_id": pid,
                    "first_name": first,
                    "surname": surname,
                }
            )
        time.sleep(0.2)
    write_csv(
        contributors_dir / "editors.csv",
        ["part_of", "cristin_person_id", "first_name", "surname"],
        editors,
    )
    # Next to the publications folder: nva/fetched.csv
    fetch_log.record(publications_dir.parent / "fetched.csv", "nva_publications")
    print(
        f"{len(kept)} publications, {len(contributors)} author rows, "
        f"{len(institution_ids)} institutions, {len(chapters)} chapters"
    )


if __name__ == "__main__":
    main()
