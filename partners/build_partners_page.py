"""Build the collaborations page from the co-authors' institutions.

Usage: python build_partners_page.py [output.html]

Writes ../site/collaborators.html by default, a page on the website next to the
overview page, which loads its fonts and scripts from ../site/assets.

Reads institution_merges.csv (institutions to merge or rename, curated by
hand), affiliation_exclusions.csv (wrong affiliations of individual co-authors
in OpenAlex, curated by hand), the publications in ../nva (for titles and
links), openalex_affiliations.csv and partner_institutions.csv (from
fetch_openalex.py), world-110m.json (country outlines from the world-atlas
package, built from Natural Earth) and ../nva/investigators.csv, and fills
partners_page_template.html. centre_projects.csv (curated by hand; rows with
include = "no" and projects that started before FIRST_PROJECT_YEAR are left
out) gives the number of active projects; the projects themselves are on
their own page (build_projects_page.py).

Institutions are counted as on the overview page (../centre): each co-author
once, at their main institution in the period, the one they are listed at
most often (main_institutions). Colleagues whose main institution is in the
Simula Group (institutions with "Simula" in their name) are not counted, and
neither are the investigators' own affiliations on their papers. All the
investigators' publications found in OpenAlex are used. Project dates are
read from the free-text durations on Simula's pages.
"""

import csv
import datetime
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
NVA_DIR = HERE.parent / "nva"
TEMPLATE = HERE / "partners_page_template.html"
OUTPUT = HERE.parent / "site" / "collaborators.html"

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
# Publication periods on the page: since each of these years
SINCE = [2024, 2021, 2016]
# OpenAlex institution types to kinds of institution (institution_kinds.csv
# corrects a few by hand)
KINDS = {
    "education": "Universities",
    "healthcare": "Hospitals",
    "facility": "Research institutes",
    "nonprofit": "Research institutes",
    "government": "Research institutes",
    "funder": "Research institutes",
    "archive": "Research institutes",
    "other": "Research institutes",
    "company": "Companies",
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
                "short": (r.get("short") or "").strip()
                or short_name(r["title"].strip()),
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


def name_key(name):
    """Compare names ignoring case, accents and the kind of dash."""
    name = name.translate({ord(c): "-" for c in "\u2010\u2011\u2012\u2013\u2014"})
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(folded.lower().split())


def year_of(value):
    return int(value) if str(value).isdigit() else 0


def read_person_merges(path):
    """{co-author: OpenAlex author ID to count them as} from person_merges.csv,
    for the same person under several OpenAlex records. A co-author is their
    OpenAlex author ID, else their name (as compared by name_key)."""
    if not path.exists():
        return {}
    return {
        r["openalex_author_id"] or name_key(r["author"]): r["same_as"]
        for r in read_csv(path)
    }


def read_colleagues(path):
    """Co-authors to count as Simula colleagues whatever their institutions
    in OpenAlex (simula_colleagues.csv): their OpenAlex author ID, else name
    (as compared by name_key)."""
    if not path.exists():
        return set()
    return {r["openalex_author_id"] or name_key(r["author"]) for r in read_csv(path)}


def read_corrections(path):
    """{co-author: row} from coauthor_corrections.csv: the institution,
    department and discipline to use for a co-author, set by hand where
    OpenAlex has none or the wrong one. A co-author is their OpenAlex author
    ID, else their name (as compared by name_key)."""
    if not path.exists():
        return {}
    return {r["openalex_author_id"] or name_key(r["author"]): r for r in read_csv(path)}


def main_institutions(
    affiliations,
    start,
    merges=None,
    exclusions=(),
    people=None,
    colleagues=(),
    fixed=None,
):
    """Co-authors on the investigators' publications from start on, each at
    their main institution: the one they are listed at most often on these
    publications (merged as in merges, {institution: name to use}).

    affiliations are openalex_affiliations.csv rows; exclusions are (author,
    institution) pairs to leave out. Co-authors are told apart by their
    OpenAlex ID, else by name; people ({co-author: co-author}, see
    read_person_merges) counts records of the same person as one, with the
    name of the record kept. Colleagues listed in colleagues (see
    read_colleagues), and colleagues whose main institution is in the
    Simula Group are left out. fixed ({co-author: institution}, from
    read_corrections) sets a co-author's main institution by hand.
    Co-authors with no known institution have main institution "".

    Returns ({co-author: {"name", "main", "rows"}}, {institution: country})."""
    merges, people, fixed = merges or {}, people or {}, fixed or {}
    excluded = {(name_key(a), name_key(i)) for a, i in exclusions}
    counts = defaultdict(Counter)  # co-author -> institution -> rows
    name_of, rows_of, country_of = {}, defaultdict(list), {}
    merged_name = {}  # names from merged records, used only as a last resort
    for r in affiliations:
        if year_of(r["year"]) < start or r["investigator"]:
            continue
        if (name_key(r["author"]), name_key(r["institution"])) in excluded:
            continue
        record = r["openalex_author_id"] or name_key(r["author"])
        coauthor = people.get(record, record)
        if coauthor == record:
            name_of.setdefault(coauthor, r["author"])
        else:
            merged_name.setdefault(coauthor, r["author"])
        rows_of[coauthor].append(r)
        # every co-author counts, with or without an institution
        counts[coauthor]
        if r["institution"]:
            name = merges.get(r["institution"], r["institution"])
            counts[coauthor][name] += 1
            country_of.setdefault(name, r["country"])
    out = {}
    for c, by_institution in counts.items():
        main = by_institution.most_common(1)[0][0] if by_institution else ""
        if fixed.get(c):
            main = fixed[c]
            if main not in country_of:
                country_of[main] = next(
                    (
                        r["country"]
                        for r in affiliations
                        if merges.get(r["institution"], r["institution"]) == main
                    ),
                    "",
                )
        if is_simula_group(main) or c in colleagues:
            continue
        name = name_of.get(c) or merged_name[c]
        out[c] = {"name": name, "main": main, "rows": rows_of[c]}
    return out, country_of


def partner_data(
    affiliations,
    institutions,
    investigators,
    papers=None,
    merges=None,
    exclusions=(),
    people=None,
    colleagues=(),
    fixed=None,
    kinds=None,
    since=SINCE,
):
    """Publications and the co-authors' main institutions, for filtering by
    period on the page. Counted as on the overview page: each co-author once,
    at their main institution in the period (see main_institutions), so an
    institution's publications are all those of the co-authors who are mainly
    there.

    papers is {result ID: {"year", "title", "doi", "nva_id"}} from ../nva, for
    titles and links. merges is {institution name: name to use}
    (institution_merges.csv); merged institutions take the place and type of
    the one with most publications. exclusions is a set of (author,
    institution) pairs that are wrong in OpenAlex (affiliation_exclusions.csv).
    people merges records of the same person (person_merges.csv), and
    colleagues are Simula colleagues to leave out (simula_colleagues.csv),
    fixed sets co-authors' institutions by hand (coauthor_corrections.csv),
    and kinds sets institutions' kinds by hand (institution_kinds.csv).

    Each institution lists its publications, and for each the co-authors as
    [name, [periods]], the periods (from since) in which this is their main
    institution."""
    papers, merges, kinds = papers or {}, merges or {}, kinds or {}
    info = {(r["ror"] or r["institution"]): r for r in institutions}
    index = {name: i for i, name in enumerate(investigators)}
    publications, pub_index = [], {}

    def publication(r):
        rid = r["result_id"]
        if rid not in pub_index:
            pub_index[rid] = len(publications)
            paper = papers.get(rid, {})
            names = [n for n in r["investigators"].split("; ") if n in index]
            doi = paper.get("doi") or (
                f"https://doi.org/{r['doi']}" if r.get("doi") else ""
            )
            publications.append(
                {
                    "year": year_of(r["year"]) or None,
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
        return pub_index[rid]

    def merged(r):
        return merges.get(r["institution"], r["institution"])

    # All the investigators' publications in the periods, also those with no
    # collaborating institution
    for r in affiliations:
        if year_of(r["year"]) >= min(since):
            publication(r)

    # Place and type: the merged institution's record with most rows
    rows_of = defaultdict(Counter)  # name -> institution key -> rows
    for r in affiliations:
        key = r["ror"] or r["institution"]
        if r["institution"] and key in info:
            rows_of[merged(r)][key] += 1

    names = {}  # co-author -> name, from the longest period
    coauthors = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    for start in sorted(since):
        found, _ = main_institutions(
            affiliations, start, merges, exclusions, people, colleagues, fixed
        )
        for c, v in found.items():
            if not v["main"] or v["main"] not in rows_of:
                continue
            names.setdefault(c, v["name"])
            for r in v["rows"]:
                coauthors[v["main"]][publication(r)][c].add(start)
    out = []
    for name, by_pub in coauthors.items():
        i = info[rows_of[name].most_common(1)[0][0]]
        pubs = sorted(by_pub)
        out.append(
            {
                "name": name,
                "country": i["country"],
                "type": kinds.get(name) or KINDS.get(i["type"], "Research institutes"),
                "city": i["city"],
                "lat": float(i["latitude"]) if i["latitude"] else None,
                "lon": float(i["longitude"]) if i["longitude"] else None,
                "pubs": pubs,
                "coauthors": [
                    sorted(
                        [names[c], sorted(periods, reverse=True)]
                        for c, periods in by_pub[k].items()
                    )
                    for k in pubs
                ],
            }
        )
    out.sort(key=lambda x: (-len(x["pubs"]), x["name"]))
    return publications, out


def read_optional(path):
    return read_csv(path) if path.exists() else []


def field_data(affiliations, here, **args):
    """For each period, the co-authors' institutions with their kind and the
    departments by research area (see coauthor_fields.py), from the curated
    files in args and the files written by fetch_coauthor_details.py:
    {"kinds", "fields", "areas": {start: {"institutions", "departments"}}}."""
    from coauthor_fields import FIELDS, KIND_ORDER, coauthors, group

    employments, own = defaultdict(list), defaultdict(list)
    for r in read_optional(here / "coauthor_employments.csv"):
        employments[r["openalex_author_id"]].append(r)
    for r in read_optional(here / "coauthor_affiliations.csv"):
        own[r["openalex_author_id"]].append(r["affiliation"])
    profiles = {
        r["openalex_author_id"]: r
        for r in read_optional(here / "coauthor_profiles.csv")
    }
    areas = {}
    for start in SINCE:
        found = coauthors(
            affiliations,
            start,
            profiles=profiles,
            employments=employments,
            own=own,
            **args,
        )
        areas[start] = dict(zip(("institutions", "departments"), group(found)))
    return {"kinds": KIND_ORDER, "fields": FIELDS, "areas": areas}


def collect(here=HERE):
    sys.path.insert(0, str(NVA_DIR))
    from publication_data import load

    data = load(
        NVA_DIR / "publications",
        NVA_DIR / "contributors",
        NVA_DIR / "investigators.csv",
    )
    investigators = list(data.investigators)
    # All the investigators' publications in NVA since each year, counted as
    # on the overview page
    years = [
        year_of(data.papers[rid]["year"])
        for rid in set().union(*data.papers_of.values())
    ]
    publication_counts = {start: sum(y >= start for y in years) for start in SINCE}
    merges = {
        r["institution"]: r["use_name"]
        for r in read_csv(here / "institution_merges.csv")
    }
    exclusions = [
        (r["author"], r["institution"])
        for r in read_csv(here / "affiliation_exclusions.csv")
    ]
    affiliations = read_csv(here / "openalex_affiliations.csv")
    people = read_person_merges(here / "person_merges.csv")
    colleagues = read_colleagues(here / "simula_colleagues.csv")
    corrections = read_corrections(here / "coauthor_corrections.csv")
    institution_kinds = read_optional(here / "institution_kinds.csv")
    kinds = {r["institution"]: r["kind"] for r in institution_kinds if r["kind"]}
    publications, institutions = partner_data(
        affiliations,
        read_csv(here / "partner_institutions.csv"),
        investigators,
        data.papers,
        merges,
        exclusions,
        people,
        colleagues,
        {k: r["institution"] for k, r in corrections.items() if r["institution"]},
        kinds,
    )
    research_areas = field_data(
        affiliations,
        here,
        merges=merges,
        exclusions=exclusions,
        people=people,
        colleagues=colleagues,
        kinds=kinds,
        corrections=corrections,
        fields={
            r["institution"]: r["discipline"]
            for r in institution_kinds
            if r["discipline"]
        },
    )
    return {
        "generated": datetime.date.today().isoformat(),
        "investigators": investigators,
        # The projects are on their own page (build_projects_page.py)
        "activeProjects": sum(
            p["status"] == "active"
            for p in projects(read_csv(here / "centre_projects.csv"))
        ),
        "publications": publications,
        "publicationCounts": publication_counts,
        "since": SINCE,
        "institutions": institutions,
        **research_areas,
    }


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT
    data = collect()
    world = (HERE / "world-110m.json").read_text(encoding="utf-8")
    html = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("__DATA__", json.dumps(data, ensure_ascii=False))
        .replace("__WORLD__", world)
    )
    output.write_text(html, encoding="utf-8")
    for start in SINCE:
        partners = [
            i
            for i in data["institutions"]
            if any(start in ps for who in i["coauthors"] for _, ps in who)
        ]
        departments = data["areas"][start]["departments"]
        print(
            f"  since {start}: {len(partners)} collaborating institutions in "
            f"{len({i['country'] for i in partners})} countries; "
            f"{len(departments)} departments, "
            f"{sum(d[5] for d in departments)} uncertain"
        )


if __name__ == "__main__":
    main()
