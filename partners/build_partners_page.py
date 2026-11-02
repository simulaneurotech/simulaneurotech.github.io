"""Build the partnerships page from the curated projects and partner data.

Usage: python build_partners_page.py [output.html]

Reads centre_projects.csv (curated by hand; rows with include = "no" and
projects that started before FIRST_PROJECT_YEAR are left out), institution_merges.csv (institutions to merge or rename, curated
by hand), prosjektbanken_projects.csv (Research Council of Norway funding,
from fetch_prosjektbanken.py; optional), affiliation_exclusions.csv (wrong affiliations of individual
co-authors in OpenAlex, curated by hand), the publications in ../nva (for titles and links), openalex_affiliations.csv and partner_institutions.csv (from
fetch_openalex.py), world-110m.json (country outlines from the world-atlas
package, built from Natural Earth) and ../nva/investigators.csv, and fills
partners_page_template.html.

Members of the Simula Group (institutions with "Simula" in their name) are
not counted as partners, and neither are the investigators' own affiliations
on their papers: partners come from co-authors' affiliations only.

Only publications relevant to the centre are used (publication_relevance.csv,
from publication_relevance.py and checked by hand). Each co-author on each
publication is put in a field (FIELD_GROUPS): by the first rule in
field_rules.csv whose pattern matches their affiliation text (with the
institution's own name removed), else as clinical if the institution is a
hospital, else by the field most of their own work is in
(openalex_authors.csv, AUTHOR_GROUPS), else unclassified. Project dates are read from the free-text durations on
Simula's pages.
"""

import csv
import datetime
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
NVA_DIR = HERE.parent / "nva"
TEMPLATE = HERE / "partners_page_template.html"

MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ],
        1,
    )
}
# Only projects that started in this year or later are shown
FIRST_PROJECT_YEAR = 2016
FIELD_GROUPS = {
    "math": "Mathematics & technology",
    "basic": "Experimental & basic medicine",
    "clinical": "Clinical medicine",
    "unclassified": "Unclassified",
}
# A co-author's own main research field (from OpenAlex) to field group
AUTHOR_GROUPS = {
    **dict.fromkeys(
        [
            "Mathematics",
            "Computer Science",
            "Engineering",
            "Physics and Astronomy",
            "Decision Sciences",
            "Earth and Planetary Sciences",
            "Chemistry",
            "Materials Science",
        ],
        "math",
    ),
    **dict.fromkeys(
        [
            "Neuroscience",
            "Biochemistry, Genetics and Molecular Biology",
            "Agricultural and Biological Sciences",
            "Immunology and Microbiology",
            "Pharmacology, Toxicology and Pharmaceutics",
            "Psychology",
        ],
        "basic",
    ),
    **dict.fromkeys(
        ["Medicine", "Health Professions", "Nursing", "Dentistry"], "clinical"
    ),
}
TYPE_GROUPS = {
    "education": "Universities",
    "healthcare": "Hospitals",
    "facility": "Research institutes",
    "company": "Companies",
    "nonprofit": "Non-profits",
    "government": "Government",
}
FUNDER_GROUPS = [
    ("Research Council of Norway", "Research Council of Norway"),
    ("ERC", "European Union"),
    ("EU", "European Union"),
    ("K. G. Jebsen Foundation", "Foundations"),
    ("Novo Nordisk Foundation", "Foundations"),
    ("Wellcome Trust", "Foundations"),
]


def read_csv(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_duration(duration):
    """Return (start, end) as fractional years from a free-text duration such
    as "2024-2029", "01.10.2021-30.06.2025" or "April 2026 - December 2029",
    or None if it has no years. A year without a month spans the whole year.
    A single date followed by a dash ("2022–") is ongoing: its end is None."""
    found = []
    pattern = (
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})"  # 01.10.2021
        r"|(\d{1,2})/(\d{4})"  # 04/2020
        r"|([A-Za-z]+)\.? (?:\d{1,2}, )?(\d{4})"  # April 2026, June 1, 2015
        r"|(\d{4})"  # 2024
    )
    for m in re.finditer(pattern, duration):
        if m.group(3):
            found.append((int(m.group(3)), int(m.group(2))))
        elif m.group(5):
            found.append((int(m.group(5)), int(m.group(4))))
        elif m.group(7) and m.group(6)[:3].lower() in MONTHS:
            found.append((int(m.group(7)), MONTHS[m.group(6)[:3].lower()]))
        elif m.group(8):
            found.append((int(m.group(8)), 0))
    if not found:
        return None
    (sy, sm), (ey, em) = found[0], found[-1]
    start = sy + ((sm or 1) - 1) / 12
    if len(found) == 1 and re.search(r"[-–]\s*$", duration):
        return round(start, 3), None
    end = ey + (em or 12) / 12
    return round(start, 3), round(end, 3)


def funder_group(funders):
    """The group of the first listed funder, for colouring."""
    for funder in funders:
        for name, group in FUNDER_GROUPS:
            if funder == name:
                return group
    return "Other"


def short_name(title):
    """A project's acronym or short name: the part before ":" or " - ",
    or a trailing "(ACRONYM)"."""
    m = re.search(r"\(([A-Z][A-Za-z0-9-]{1,15})\)\s*$", title)
    if m:
        return m.group(1)
    return re.split(r":| [-–] ", title)[0].strip()


def rcn_details(grants, prosjektbanken):
    """Research Council of Norway details for the first of a project's grants
    found in Prosjektbanken ({grant: row}), or None."""
    for grant in re.findall(r"\b\d{6,}\b", grants):
        r = prosjektbanken.get(grant)
        if r and r["found"] == "yes":
            funding = (
                int(float(r["total_funding_nok"])) if r["total_funding_nok"] else None
            )
            return {
                "grant": grant,
                "funding": funding or None,
                "programmes": [x for x in r["programmes"].split("; ") if x],
                "scheme": r["application_type"],
                "lead": r["lead"],
                "institution": r["lead_institution"],
                "ledHere": is_simula_group(r["lead_institution"]),
                "titleNo": r["title_no"],
                "effects": r["achieved_effects"],
            }
    return None


def projects(rows, first_year=FIRST_PROJECT_YEAR, prosjektbanken=None):
    """Included projects that started in first_year or later, with Research
    Council of Norway details from prosjektbanken ({grant: row}) when known."""
    prosjektbanken = prosjektbanken or {}
    out = []
    for r in rows:
        if r.get("include", "").strip().lower() == "no":
            continue
        dates = parse_duration(r["duration"])
        if dates and dates[0] < first_year:
            continue
        funders = [f.strip() for f in r["funders"].split(";") if f.strip()]
        out.append(
            {
                "title": r["title"].strip(),
                "short": short_name(r["title"].strip()),
                "url": r["url"],
                "status": r["status"],
                "start": dates[0] if dates else None,
                "end": dates[1] if dates else None,
                "investigators": [
                    x.strip() for x in r["investigators"].split(";") if x.strip()
                ],
                "funders": funders,
                "funderGroup": funder_group(funders),
                "grants": r["grants"],
                "partners": [
                    x.strip() for x in re.split(r"[;|]", r["partners"]) if x.strip()
                ],
                "rcn": rcn_details(r["grants"], prosjektbanken),
            }
        )
    return out


def is_simula_group(institution):
    """Simula Research Laboratory, SimulaMet, Simula School, Simula UiB and
    other members of the Simula Group."""
    return "simula" in institution.lower()


def read_field_rules(path):
    """[(compiled pattern, group)] from field_rules.csv, in order."""
    return [
        (re.compile(r["pattern"], re.IGNORECASE), r["group"]) for r in read_csv(path)
    ]


def field_group(row, rules, author_fields):
    """The field group of a co-author's affiliation row."""
    text = re.sub(
        re.escape(row["institution"]),
        " ",
        row.get("affiliation", ""),
        flags=re.IGNORECASE,
    )
    for pattern, group in rules:
        if pattern.search(text):
            return group
    if row.get("type") == "healthcare":
        return "clinical"
    return AUTHOR_GROUPS.get(
        author_fields.get(row.get("openalex_author_id", ""), ""), "unclassified"
    )


def name_key(name):
    """Compare names ignoring case, accents and the kind of dash."""
    name = name.translate({ord(c): "-" for c in "\u2010\u2011\u2012\u2013\u2014"})
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(folded.lower().split())


def partner_data(
    affiliations,
    institutions,
    investigators,
    papers=None,
    merges=None,
    exclusions=(),
    relevant=None,
    rules=(),
    author_fields=None,
):
    """Publications and the institutions where co-authors are, for filtering
    by period on the page.

    papers is {result ID: {"year", "title", "doi", "nva_id"}} from ../nva, for
    titles and links. merges is {institution name: name to use}
    (institution_merges.csv); merged institutions take the place and type of
    the one with most publications. exclusions is a set of (author,
    institution) pairs that are wrong in OpenAlex (affiliation_exclusions.csv).
    relevant is the set of result IDs to use (all when None); rules and
    author_fields decide each co-author's field group."""
    papers, merges, author_fields = papers or {}, merges or {}, author_fields or {}
    excluded = {(name_key(a), name_key(i)) for a, i in exclusions}
    info = {(r["ror"] or r["institution"]): r for r in institutions}
    index = {name: i for i, name in enumerate(investigators)}
    publications, pub_index = [], {}
    coauthors = defaultdict(lambda: defaultdict(set))  # name -> pub -> authors
    rows_of = defaultdict(set)  # name -> institution keys merged into it
    for r in affiliations:
        rid = r["result_id"]
        if relevant is not None and rid not in relevant:
            continue
        if rid not in pub_index:
            pub_index[rid] = len(publications)
            paper = papers.get(rid, {})
            names = [n for n in r["investigators"].split("; ") if n in index]
            doi = paper.get("doi") or (
                f"https://doi.org/{r['doi']}" if r.get("doi") else ""
            )
            publications.append(
                {
                    "year": int(r["year"]) if r["year"].isdigit() else None,
                    "title": paper.get("title", ""),
                    "url": doi
                    or (
                        f"https://nva.sikt.no/registration/{paper['nva_id']}"
                        if paper.get("nva_id")
                        else ""
                    ),
                    "inv": [index[n] for n in names],
                }
            )
        key = r["ror"] or r["institution"]
        if (name_key(r.get("author", "")), name_key(r["institution"])) in excluded:
            continue
        if r["institution"] and key in info and not r.get("investigator"):
            name = merges.get(r["institution"], r["institution"])
            rows_of[name].add(key)
            group = field_group(r, rules, author_fields)
            coauthors[name][pub_index[rid]].add((r["author"], group))
    out = []
    for name, by_pub in coauthors.items():
        # Place and type from the merged institution with most publications
        keys = sorted(
            rows_of[name],
            key=lambda k: (
                -sum(1 for r in affiliations if (r["ror"] or r["institution"]) == k)
            ),
        )
        i = info[keys[0]]
        pubs = sorted(by_pub)
        out.append(
            {
                "name": name,
                "country": i["country"],
                "type": TYPE_GROUPS.get(i["type"], "Other"),
                "city": i["city"],
                "lat": float(i["latitude"]) if i["latitude"] else None,
                "lon": float(i["longitude"]) if i["longitude"] else None,
                "own": is_simula_group(name),
                "pubs": pubs,
                "coauthors": [[list(a) for a in sorted(by_pub[k])] for k in pubs],
            }
        )
    out.sort(key=lambda x: (-len(x["pubs"]), x["name"]))
    return publications, out


def collect(here=HERE):
    sys.path.insert(0, str(NVA_DIR))
    from publication_data import load

    data = load(
        NVA_DIR / "publications",
        NVA_DIR / "contributors",
        NVA_DIR / "investigators.csv",
    )
    investigators = list(data.investigators)
    merges = {
        r["institution"]: r["use_name"]
        for r in read_csv(here / "institution_merges.csv")
    }
    exclusions = [
        (r["author"], r["institution"])
        for r in read_csv(here / "affiliation_exclusions.csv")
    ]
    relevance = (
        read_csv(here / "publication_relevance.csv")
        if (here / "publication_relevance.csv").exists()
        else []
    )
    sys.path.insert(0, str(here))
    from publication_relevance import relevant as is_relevant

    relevant = (
        {r["result_id"] for r in relevance if is_relevant(r)} if relevance else None
    )
    author_fields = {
        r["openalex_author_id"]: r["main_field"]
        for r in (
            read_csv(here / "openalex_authors.csv")
            if (here / "openalex_authors.csv").exists()
            else []
        )
    }
    publications, institutions = partner_data(
        read_csv(here / "openalex_affiliations.csv"),
        read_csv(here / "partner_institutions.csv"),
        investigators,
        data.papers,
        merges,
        exclusions,
        relevant,
        read_field_rules(here / "field_rules.csv"),
        author_fields,
    )
    return {
        "generated": datetime.date.today().isoformat(),
        "investigators": investigators,
        "projects": projects(
            read_csv(here / "centre_projects.csv"),
            prosjektbanken={
                r["grant"]: r
                for r in (
                    read_csv(here / "prosjektbanken_projects.csv")
                    if (here / "prosjektbanken_projects.csv").exists()
                    else []
                )
            },
        ),
        "publications": publications,
        "fields": FIELD_GROUPS,
        "relevance": {
            "used": len(relevant) if relevant is not None else None,
            "total": len(relevance),
        },
        "institutions": institutions,
    }


def main():
    output = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "partners_page.html")
    data = collect()
    world = (HERE / "world-110m.json").read_text(encoding="utf-8")
    html = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("__DATA__", json.dumps(data, ensure_ascii=False))
        .replace("__WORLD__", world)
    )
    output.write_text(html, encoding="utf-8")
    partners = [i for i in data["institutions"] if not i["own"]]
    print(
        f"{output.name}: {len(data['projects'])} projects, {len(partners)} collaborating "
        f"institutions in {len({i['country'] for i in partners})} countries"
    )


if __name__ == "__main__":
    main()
