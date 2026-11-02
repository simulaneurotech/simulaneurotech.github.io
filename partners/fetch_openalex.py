"""Look up the institutions and countries of all authors in OpenAlex.

Usage: python fetch_openalex.py [output_dir]

OpenAlex (https://openalex.org) is a free, open index of research output that
records each author's institution, with its country, type (education,
healthcare, company, ...) and ROR ID. The centre's publications from
../nva (after merging duplicates) are looked up by DOI; publications without
a DOI, mostly older ones, are not covered.

Partner institutions come from the co-authors' affiliations only. The
investigators' own affiliations on a paper (such as a second position at a
university) are recorded but not counted. Investigators are recognised among
a paper's authors by surname and compatible first name, comparing only with
the investigators known to be on that paper.

Writes to output_dir:

- openalex_affiliations.csv: one row per author per institution per
  publication: result ID, year, DOI, author position and name, OpenAlex
  author ID, the investigator this author is (if any), institution, ROR ID,
  country, institution type, the affiliation text on the paper (such as
  "Department of Neurosurgery, Oslo University Hospital", without any email
  addresses), and the centre investigators on the publication
- openalex_works.csv: one row per publication: research field and subfield
  of its main topic, the fields of all its topics, title, and whether the
  title or abstract has methods terms, physiological terms or wireless
  terms (for publication_relevance.py). Abstracts themselves are not
  stored, as they are usually copyrighted
- openalex_authors.csv: one row per co-author: the research field most of
  their own work is in (for grouping co-authors when the affiliation text
  says nothing)
- partner_institutions.csv: one row per institution: country, type, ROR ID,
  city and coordinates, number of the centre's publications with a co-author
  there, and which investigators those publications are by
"""

import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

NVA_DIR = Path(__file__).resolve().parent.parent / "nva"

sys.path.insert(0, str(NVA_DIR))
from fetch_nva import ascii_fold
from publication_data import compatible, doi_key, id_order, load
from publication_relevance import text_flags

API = "https://api.openalex.org"
AFFILIATION_FIELDS = [
    "result_id",
    "year",
    "doi",
    "author_position",
    "author",
    "openalex_author_id",
    "investigator",
    "institution",
    "ror",
    "country",
    "type",
    "affiliation",
    "investigators",
]
WORK_FIELDS = [
    "result_id",
    "doi",
    "year",
    "title",
    "primary_field",
    "primary_subfield",
    "fields",
    "methods_terms",
    "physiology_terms",
    "wireless_in_abstract",
]
INSTITUTION_FIELDS = [
    "institution",
    "country",
    "type",
    "ror",
    "city",
    "latitude",
    "longitude",
    "publications",
    "investigators",
]


def fetch_works(dois):
    """Return {DOI: OpenAlex work} for the DOIs found in OpenAlex."""
    works = {}
    for i in range(0, len(dois), 50):
        batch = dois[i : i + 50]
        url = f"{API}/works?" + urllib.parse.urlencode(
            {
                "filter": "doi:" + "|".join(batch),
                "per-page": 50,
                "select": "doi,title,authorships,primary_topic,topics,abstract_inverted_index",
            }
        )
        with urllib.request.urlopen(url, timeout=60) as response:
            for work in json.load(response)["results"]:
                works[doi_key(work["doi"])] = work
        time.sleep(0.3)
    return works


def fetch_places(rors):
    """Return {ROR ID: (city, latitude, longitude)} from OpenAlex."""
    places = {}
    for i in range(0, len(rors), 50):
        batch = rors[i : i + 50]
        url = f"{API}/institutions?" + urllib.parse.urlencode(
            {"filter": "ror:" + "|".join(batch), "per-page": 50, "select": "ror,geo"}
        )
        with urllib.request.urlopen(url, timeout=60) as response:
            for institution in json.load(response)["results"]:
                geo = institution.get("geo") or {}
                places[institution["ror"]] = (
                    geo.get("city") or "",
                    geo.get("latitude"),
                    geo.get("longitude"),
                )
        time.sleep(0.3)
    return places


def fetch_author_fields(author_ids):
    """Return {OpenAlex author ID: the field most of their topics are in}."""
    fields = {}
    for i in range(0, len(author_ids), 50):
        batch = author_ids[i : i + 50]
        url = f"{API}/authors?" + urllib.parse.urlencode(
            {
                "filter": "openalex_id:" + "|".join(batch),
                "per-page": 50,
                "select": "id,topics",
            }
        )
        with urllib.request.urlopen(url, timeout=60) as response:
            for author in json.load(response)["results"]:
                counts = Counter()
                for topic in author.get("topics") or []:
                    counts[topic["field"]["display_name"]] += topic.get("count", 1)
                if counts:
                    fields[author["id"].rsplit("/", 1)[-1]] = counts.most_common(1)[0][
                        0
                    ]
        time.sleep(0.3)
    return fields


def abstract(work):
    """The abstract as text, from OpenAlex's inverted index."""
    index = work.get("abstract_inverted_index") or {}
    words = sorted(
        (pos, word) for word, positions in index.items() for pos in positions
    )
    return " ".join(word for _, word in words)


def work_row(rid, year, doi, work):
    topic = work.get("primary_topic") or {}
    fields = dict.fromkeys(t["field"]["display_name"] for t in work.get("topics") or [])
    return {
        "result_id": rid,
        "doi": doi,
        "year": year,
        "title": work.get("title") or "",
        "primary_field": (topic.get("field") or {}).get("display_name", ""),
        "primary_subfield": (topic.get("subfield") or {}).get("display_name", ""),
        "fields": "; ".join(fields),
        **text_flags(work.get("title") or "", abstract(work)),
    }


EMAIL = re.compile(
    r"(?:(?:electronic address|e-?mail)\s*:?\s*)?[\w.+-]+@[\w-]+(?:\.[\w-]+)+",
    re.IGNORECASE,
)


def without_emails(text):
    """Affiliation text without email addresses, which papers sometimes include."""
    return re.sub(r"\s{2,}", " ", EMAIL.sub("", text)).strip(" ;,.")


DASHES = str.maketrans({c: "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2212"})


def which_investigator(author_name, investigators):
    """The investigator (from those on the paper) this author is, or "".
    The author's last name must be one of the investigator's names after the
    first (or part of a hyphenated one), and the first names must be
    compatible. Dashes of all kinds count as hyphens, and "Last, First" is
    read as "First Last"."""
    author_name = author_name.translate(DASHES)
    if "," in author_name:  # "Rognes, Marie E."
        last_part, _, first_part = author_name.partition(",")
        author_name = f"{first_part} {last_part}"
    tokens = author_name.split()
    if len(tokens) < 2:
        return ""
    last = ascii_fold(tokens[-1]).lower()
    for name in investigators:
        parts = name.translate(DASHES).split()
        later = set()
        for p in parts[1:]:
            p = ascii_fold(p).lower().strip(".")
            later |= {p, *p.split("-")}
        if last in later and compatible(tokens[0], parts[0]):
            return name
    return ""


def affiliation_rows(rid, year, doi, work, investigators):
    rows = []
    for i, authorship in enumerate(work.get("authorships", []), 1):
        author = authorship.get("author") or {}
        investigator = which_investigator(author.get("display_name", ""), investigators)
        # Affiliation text per institution, where OpenAlex links them
        texts = defaultdict(list)
        for a in authorship.get("affiliations") or []:
            for institution_id in a.get("institution_ids") or [""]:
                texts[institution_id].append(a.get("raw_affiliation_string", ""))
        for institution in authorship.get("institutions", []) or [{}]:
            text = (
                texts.get(institution.get("id", ""))
                or authorship.get("raw_affiliation_strings")
                or []
            )
            rows.append(
                {
                    "result_id": rid,
                    "year": year,
                    "doi": doi,
                    "author_position": i,
                    "author": author.get("display_name", ""),
                    "openalex_author_id": (author.get("id") or "").rsplit("/", 1)[-1],
                    "investigator": investigator,
                    "institution": institution.get("display_name", ""),
                    "ror": institution.get("ror") or "",
                    "country": institution.get("country_code") or "",
                    "type": institution.get("type") or "",
                    "affiliation": "; ".join(
                        dict.fromkeys(without_emails(t) for t in text if t)
                    ),
                    "investigators": "; ".join(investigators),
                }
            )
    return rows


def partner_institutions(rows, places):
    """Aggregate co-authors' affiliation rows to one row per institution, with
    the city and coordinates in places ({ROR ID: (city, latitude, longitude)}).
    The investigators' own affiliations are left out."""
    papers, investigators, info = defaultdict(set), defaultdict(Counter), {}
    for r in rows:
        if not r["institution"] or r["investigator"]:
            continue
        key = r["ror"] or r["institution"]
        info[key] = (r["institution"], r["country"], r["type"], r["ror"])
        if r["result_id"] not in papers[key]:
            papers[key].add(r["result_id"])
            for name in filter(None, r["investigators"].split("; ")):
                investigators[key][name] += 1
    return [
        {
            "institution": info[k][0],
            "country": info[k][1],
            "type": info[k][2],
            "ror": info[k][3],
            "city": places.get(info[k][3], ("", "", ""))[0],
            "latitude": places.get(info[k][3], ("", "", ""))[1],
            "longitude": places.get(info[k][3], ("", "", ""))[2],
            "publications": len(papers[k]),
            "investigators": "; ".join(
                f"{n} ({c})" for n, c in investigators[k].most_common()
            ),
        }
        for k in sorted(papers, key=lambda k: (-len(papers[k]), info[k][0]))
    ]


def main():
    output_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    data = load(
        NVA_DIR / "publications",
        NVA_DIR / "contributors",
        NVA_DIR / "investigators.csv",
    )
    investigators = defaultdict(list)
    for name in data.investigators:
        for rid in data.papers_of[name]:
            investigators[rid].append(name)
    with_doi = {
        rid: doi_key(p["doi"])
        for rid, p in sorted(data.papers.items(), key=lambda kv: id_order(kv[0]))
        if p["doi"] and rid in investigators
    }
    works = fetch_works(sorted(set(with_doi.values())))

    rows = [
        row
        for rid, doi in with_doi.items()
        if doi in works
        for row in affiliation_rows(
            rid, data.papers[rid]["year"], doi, works[doi], investigators[rid]
        )
    ]
    with (output_dir / "openalex_affiliations.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=AFFILIATION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with (output_dir / "openalex_works.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=WORK_FIELDS)
        writer.writeheader()
        writer.writerows(
            work_row(rid, data.papers[rid]["year"], doi, works[doi])
            for rid, doi in with_doi.items()
            if doi in works
        )
    co_authors = sorted(
        {
            r["openalex_author_id"]
            for r in rows
            if r["openalex_author_id"] and not r["investigator"]
        }
    )
    author_fields = fetch_author_fields(co_authors)
    with (output_dir / "openalex_authors.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["openalex_author_id", "main_field"])
        writer.writerows(sorted(author_fields.items()))
    places = fetch_places(sorted({r["ror"] for r in rows if r["ror"]}))
    institutions = partner_institutions(rows, places)
    with (output_dir / "partner_institutions.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=INSTITUTION_FIELDS)
        writer.writeheader()
        writer.writerows(institutions)
    found = sum(1 for doi in with_doi.values() if doi in works)
    print(
        f"{len(investigators)} publications, {len(with_doi)} with a DOI, "
        f"{found} found in OpenAlex; {len(institutions)} institutions"
    )


if __name__ == "__main__":
    main()
