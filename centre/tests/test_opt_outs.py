"""With the real data: someone in opt_outs.csv is named on no page.

The co-author is picked from the data when the test runs, so no names are
written here. Skipped without the co-author data.
"""

import csv
import json

import pytest
from collaboration_map import collect as coauthorship_data

import build_centre_page as bcp
import build_partners_page as bpp
import coauthor_data
from publication_data import load

pytestmark = pytest.mark.skipif(
    not coauthor_data.available(),
    reason="needs the co-author data (see nva/coauthor_data.py)",
)


def rows(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pages():
    """What the overview, "Who we publish with" and "Who publishes with whom"
    pages show, as text."""
    data = load(
        bcp.NVA_DIR / "publications",
        coauthor_data.CONTRIBUTORS,
        bcp.NVA_DIR / "investigators.csv",
    )
    return json.dumps(
        [bcp.collect(), bpp.collect(), coauthorship_data(data)], ensure_ascii=False
    )


def test_an_opted_out_coauthor_is_named_on_no_page(tmp_path, monkeypatch):
    shown = pages()
    contributors = rows(coauthor_data.CONTRIBUTORS / "contributors.csv")
    affiliations = [
        r
        for r in rows(coauthor_data.PARTNERS / "openalex_affiliations.csv")
        if not r["investigator"] and r["openalex_author_id"]
    ]
    cristin_ids = {}
    for r in contributors:
        if r["cristin_person_id"]:
            name = f"{r['first_name']} {r['surname']}"
            cristin_ids.setdefault(name, set()).add(r["cristin_person_id"])
    # A co-author in both NVA and OpenAlex under the same name, named on the
    # pages, with a name no other name contains
    names = sorted({r["author"] for r in affiliations} & set(cristin_ids))
    name = next(
        n
        for n in names
        if len(n) > 10
        and shown.count(n) > 0
        and not any(n in other for other in names if other != n)
    )

    path = tmp_path / "opt_outs.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=coauthor_data.OPT_OUT_FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "names": name,
                "cristin_person_id": ";".join(sorted(cristin_ids[name])),
                "openalex_author_id": ";".join(
                    sorted(
                        {
                            r["openalex_author_id"]
                            for r in affiliations
                            if r["author"] == name
                        }
                    )
                ),
            }
        )
    monkeypatch.setattr(coauthor_data, "OPT_OUTS", path)

    assert name not in pages()
