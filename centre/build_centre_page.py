"""Build the centre's overview page.

Usage: python build_centre_page.py [output.html]

Writes ../site/index.html by default, the page published on GitHub Pages,
which loads its fonts and d3 from ../site/assets.

Reads the investigators and their publications from ../nva (after merging
duplicates), the co-authors and their institutions from
../partners/openalex_affiliations.csv, and the projects from
../partners/centre_projects.csv (with Research Council funding from
../partners/prosjektbanken_projects.csv), and fills
centre_page_template.html. Investigators link to their Simula pages from
investigator_pages.csv (checked by hand).

Key figures are given since each year in SINCE:

- publications: the investigators' publications in NVA
- co-authors: everyone else on the investigators' publications found in
  OpenAlex (by DOI), counted once, except colleagues whose main institution
  (see below) is in the Simula Group
- institutions: each co-author's main institution (the one they are listed
  at most often on these publications), counted once; Simula Group
  institutions are not counted, and the merges and exclusions in
  ../partners apply
- countries: the countries of these institutions
"""

import csv
import datetime
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
NVA_DIR = HERE.parent / "nva"
PARTNERS_DIR = HERE.parent / "partners"
TEMPLATE = HERE / "centre_page_template.html"
OUTPUT = HERE.parent / "site" / "index.html"
SINCE = [2024, 2021, 2016]
# The project timeline is hidden for now; set to True to show it again
SHOW_PROJECTS = False
# Pages linked under "More about the centre"; the co-authorship page
# (coauthorship.html) is not linked yet
LINKED_PAGES = ["collaborators.html", "projects.html"]
AFFILIATIONS = {"SRL": "Simula Research Laboratory", "SimulaMet": "SimulaMet"}

sys.path.insert(0, str(NVA_DIR))
sys.path.insert(0, str(PARTNERS_DIR))
from build_partners_page import (
    main_institutions,
    projects,
    read_colleagues,
    read_corrections,
    read_person_merges,
)
from publication_data import id_order, load


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def year_of(value):
    return int(value) if str(value).isdigit() else 0


def key_figures(
    pub_years,
    affiliations,
    since,
    merges=None,
    exclusions=(),
    people=None,
    colleagues=(),
    fixed=None,
):
    """Publications, co-authors, institutions and countries since each year,
    with the lists behind each number.

    pub_years is {result ID: year} for the investigators' publications.
    affiliations are openalex_affiliations.csv rows; merges is {institution:
    name to use}, exclusions a list of (author, institution) to leave out and
    people records of the same person to count as one (person_merges.csv);
    colleagues are Simula colleagues to leave out (simula_colleagues.csv);
    fixed sets co-authors' institutions by hand (coauthor_corrections.csv).

    Returns {year: {"publications", "coauthors", "institutions", "countries":
    counts, "lists": {"publications": [result IDs], "coauthors": [[name, main
    institution, country, [result IDs]]], "institutions": [[name, country,
    [indices into coauthors]]]}}}."""
    figures = {}
    for start in since:
        found, country_of = main_institutions(
            affiliations, start, merges, exclusions, people, colleagues, fixed
        )
        pubs_of = {c: {r["result_id"] for r in v["rows"]} for c, v in found.items()}
        coauthors = sorted(found, key=lambda c: (-len(pubs_of[c]), found[c]["name"]))
        coauthor_rows = [
            [
                found[c]["name"],
                found[c]["main"],
                country_of.get(found[c]["main"], ""),
                sorted(pubs_of[c], key=lambda rid: (-pub_years.get(rid, 0), rid)),
            ]
            for c in coauthors
        ]
        members = defaultdict(list)
        for i, c in enumerate(coauthors):
            if found[c]["main"]:
                members[found[c]["main"]].append(i)
        institution_rows = sorted(
            ([name, country_of.get(name, ""), idx] for name, idx in members.items()),
            key=lambda r: (-len({p for i in r[2] for p in coauthor_rows[i][3]}), r[0]),
        )
        publications = sorted(
            (rid for rid, y in pub_years.items() if y >= start),
            key=lambda rid: (-pub_years[rid], rid),
        )
        figures[start] = {
            "publications": len(publications),
            "coauthors": len(coauthors),
            "institutions": len(institution_rows),
            "countries": len({r[1] for r in institution_rows if r[1]}),
            "lists": {
                "publications": publications,
                "coauthors": coauthor_rows,
                "institutions": institution_rows,
            },
        }
    return figures


MAX_AUTHORS = 5


def author_lists(contributors, investigator_ids, removed=()):
    """{result ID: [[name, is an investigator], ...]} in author order, from
    ../nva/contributors/contributors.csv rows, leaving out the book editors
    removed from chapters (removed: (result ID, name) pairs)."""
    removed = set(removed)
    rows = defaultdict(list)
    for r in contributors:
        rows[r["cristin_result_id"]].append(r)
    out = {}
    for rid, rs in rows.items():
        authors = []
        for r in sorted(rs, key=lambda r: int(r["order"] or 0)):
            name = f"{r['first_name']} {r['surname']}".strip()
            if (rid, name) in removed:
                continue
            if "," in name:  # "Zikatanov, Ludmil T." -> "Ludmil T. Zikatanov"
                last, _, first = name.partition(",")
                name = f"{first.strip()} {last.strip()}"
            authors.append([name, r["cristin_person_id"] in investigator_ids])
        out[rid] = authors
    return out


def publication_records(papers, papers_of, first_year, authors=None):
    """{result ID: {"year", "title", "url", "venue", "investigators",
    "authors"}} for the investigators' publications from first_year on, with
    all authors in order as (name, is an investigator). The page shows the
    first MAX_AUTHORS, then "et al.", naming any emphasised author further
    down the list."""
    authors = authors or {}
    investigators = defaultdict(list)
    for name, rids in papers_of.items():
        for rid in sorted(rids, key=id_order):
            investigators[rid].append(name)
    out = {}
    for rid in sorted(investigators, key=id_order):
        names = investigators[rid]
        p = papers[rid]
        if year_of(p["year"]) < first_year:
            continue
        url = p.get("doi") or (
            f"https://nva.sikt.no/registration/{p['nva_id']}" if p.get("nva_id") else ""
        )
        listed = authors.get(rid) or [[n, True] for n in names]
        out[rid] = {
            "year": year_of(p["year"]),
            "title": p["title"],
            "url": url,
            "venue": p.get("venue") or p.get("journal", ""),
            "investigators": names,
            "authors": listed,
        }
    return out


def collect():
    data = load(
        NVA_DIR / "publications",
        NVA_DIR / "contributors",
        NVA_DIR / "investigators.csv",
    )
    pub_years = {
        rid: year_of(data.papers[rid]["year"])
        for rids in data.papers_of.values()
        for rid in sorted(rids, key=id_order)
    }
    roles = {r["name"]: r["role"] for r in read_csv(NVA_DIR / "investigators.csv")}
    pages = {
        r["name"]: r["simula_page"] for r in read_csv(HERE / "investigator_pages.csv")
    }
    investigators = [
        {
            "name": name,
            "affiliation": AFFILIATIONS.get(info["aff"], info["aff"]),
            "page": pages.get(name, ""),
            "role": "; ".join(
                part.strip()
                for part in roles.get(name, "").split(";")
                if part.strip() and part.strip() != "Investigator"
            ),
        }
        for name, info in data.investigators.items()
    ]
    merges = {
        r["institution"]: r["use_name"]
        for r in read_csv(PARTNERS_DIR / "institution_merges.csv")
    }
    exclusions = [
        (r["author"], r["institution"])
        for r in read_csv(PARTNERS_DIR / "affiliation_exclusions.csv")
    ]
    prosjektbanken = {
        r["grant"]: r for r in read_csv(PARTNERS_DIR / "prosjektbanken_projects.csv")
    }
    return {
        "generated": datetime.date.today().isoformat(),
        "investigators": investigators,
        "publications": publication_records(
            data.papers,
            data.papers_of,
            min(SINCE),
            author_lists(
                read_csv(NVA_DIR / "contributors" / "contributors.csv"),
                {pid for info in data.investigators.values() for pid in info["ids"]},
                [(rid, name) for rid, name, _ in data.removed_editors],
            ),
        ),
        "figures": key_figures(
            pub_years,
            read_csv(PARTNERS_DIR / "openalex_affiliations.csv"),
            SINCE,
            merges,
            exclusions,
            read_person_merges(PARTNERS_DIR / "person_merges.csv"),
            read_colleagues(PARTNERS_DIR / "simula_colleagues.csv"),
            {
                k: r["institution"]
                for k, r in read_corrections(
                    PARTNERS_DIR / "coauthor_corrections.csv"
                ).items()
                if r["institution"]
            },
        ),
        "showProjects": SHOW_PROJECTS,
        "linkedPages": LINKED_PAGES,
        "projects": projects(
            read_csv(PARTNERS_DIR / "centre_projects.csv"),
            prosjektbanken=prosjektbanken,
        ),
    }


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT
    data = collect()
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "__DATA__", json.dumps(data, ensure_ascii=False)
    )
    output.write_text(html, encoding="utf-8")
    print(
        f"{output.name}: {len(data['investigators'])} investigators, {len(data['projects'])} projects"
    )
    for start, f in data["figures"].items():
        print(
            f"  since {start}: "
            + ", ".join(f"{k} {v}" for k, v in f.items() if k != "lists")
        )


if __name__ == "__main__":
    main()
