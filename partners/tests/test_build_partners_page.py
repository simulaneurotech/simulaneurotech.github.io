import re
from pathlib import Path

import pytest

import build_partners_page as bpp


@pytest.mark.parametrize(
    "duration, expected",
    [
        ("2024-2029", (2024.0, 2030.0)),
        ("01.10.2021-30.06.2025", (2021.75, 2025.5)),
        ("April 2026 - December 2029", (2026.25, 2030.0)),
        ("04/2020-03/2023", (2020.25, 2023.25)),
        ("June 1, 2015 – May 31, 2019", (2015.417, 2019.417)),
        ("2022–", (2022.0, None)),
        ("", None),
    ],
)
def test_parse_duration(duration, expected):
    assert bpp.parse_duration(duration) == expected


def test_short_name_and_funder_group():
    assert bpp.short_name("aCleanBrain: The Brain Fluids") == "aCleanBrain"
    assert bpp.short_name("Wireless Access Points (DISCO)") == "DISCO"
    assert bpp.short_name("SIMENT - Simulating mental illness") == "SIMENT"
    assert bpp.funder_group(["ERC", "EU"]) == "European Union"
    assert bpp.funder_group(["Novo Nordisk Foundation"]) == "Foundations"
    assert bpp.funder_group(["Wellcome Trust"]) == "Foundations"
    assert bpp.funder_group(["NordForsk"]) == "Other"
    assert bpp.funder_group(["Centre for Advanced Study"]) == "Other"
    assert bpp.funder_group([]) == "Other"


def test_projects_leave_out_excluded_rows():
    row = {
        "title": "Waterscape: The Numerical Waterscape",
        "url": "u",
        "duration": "2016-2020",
        "status": "ended",
        "leader": "Marie E. Rognes",
        "leader_role": "lead",
        "host": "Simula Research Laboratory",
        "participants": "Kent-Andre Mardal",
        "funders": "Research Council of Norway",
        "scheme": "Researcher Project",
        "grants": "250731",
        "funding": "NOK 7000992",
        "collaborators": "University of Oslo; Oslo University Hospital",
        "collaborator_countries": "",
        "collaborator_source": "Simula's project page",
    }
    projects = bpp.projects(
        [
            {**row, "include": "yes"},
            {**row, "title": "Out", "include": "no"},
            # Started before 2016: left out
            {**row, "title": "Old", "include": "yes", "duration": "2011-2015"},
        ]
    )
    assert len(projects) == 1
    p = projects[0]
    assert (p["short"], p["start"], p["end"], p["funderGroup"]) == (
        "Waterscape",
        2016.0,
        2021.0,
        "Research Council of Norway",
    )
    assert p["investigators"] == ["Marie E. Rognes", "Kent-Andre Mardal"]
    assert p["collaborators"] == ["University of Oslo", "Oslo University Hospital"]
    # Funding amounts stay in the CSV file
    assert not any("funding" in k.lower() for k in p)


def test_simula_group():
    for name in (
        "Simula Research Laboratory",
        "Simula Metropolitan Center for Digital Engineering",
        "Simula School",
        "Simula UiB",
    ):
        assert bpp.is_simula_group(name)
    assert not bpp.is_simula_group("University of Oslo")


def aff(rid, year, author, institution, ror, investigators="Ann A", **extra):
    """An openalex_affiliations.csv row for a co-author."""
    return {
        "result_id": rid,
        "year": year,
        "author": author,
        "openalex_author_id": "",
        "investigator": "",
        "investigators": investigators,
        "institution": institution,
        "ror": ror,
        "country": "NO",
        **extra,
    }


def inst(name, ror, type_="education", city="", country="NO", lat="", lon=""):
    """A partner_institutions.csv row."""
    return {
        "institution": name,
        "ror": ror,
        "country": country,
        "type": type_,
        "city": city,
        "latitude": lat,
        "longitude": lon,
    }


def test_partner_data_counts_main_institutions():
    affiliations = [
        aff(
            "1", "2021", "Carl Co", "Oslo University Hospital", "r2", type="healthcare"
        ),
        aff("1", "2021", "Dana Do", "Simula Research Laboratory", "r1"),
        aff(
            "2",
            "2019",
            "Carl Co",
            "Oslo University Hospital",
            "r2",
            "Ann A; Bo B",
            type="healthcare",
        ),
        aff("2", "2019", "Dana Do", "Simula Research Laboratory", "r1", "Ann A; Bo B"),
        aff("2", "2019", "Dana Do", "University of Oslo", "r3", "Ann A; Bo B"),
    ]
    institutions = [
        inst("Simula Research Laboratory", "r1", "facility", "Oslo"),
        inst(
            "Oslo University Hospital",
            "r2",
            "healthcare",
            "Oslo",
            lat="59.9",
            lon="10.7",
        ),
        inst("University of Oslo", "r3", "education", "Oslo"),
    ]
    papers = {
        "1": {"title": "Paper one", "doi": "https://doi.org/10.1/a", "nva_id": "n1"},
        "2": {"title": "Paper two", "doi": "", "nva_id": "n2"},
    }
    publications, out = bpp.partner_data(
        affiliations, institutions, ["Ann A", "Bo B"], papers, since=[2021, 2016]
    )
    assert publications == [
        {
            "year": 2021,
            "title": "Paper one",
            "url": "https://doi.org/10.1/a",
            "inv": [0],
        },
        {
            "year": 2019,
            "title": "Paper two",
            "url": "https://nva.sikt.no/registration/n2",
            "inv": [0, 1],
        },
    ]
    # Dana Do is mainly at Simula, so neither Simula nor the University of
    # Oslo, where she is also listed, is counted. Paper two is only in the
    # period since 2016.
    assert [(i["name"], i["type"], i["pubs"], i["coauthors"]) for i in out] == [
        (
            "Oslo University Hospital",
            "Hospitals",
            [0, 1],
            [
                [["Carl Co", [2021, 2016]]],
                [["Carl Co", [2016]]],
            ],
        )
    ]


def test_coauthors_count_only_at_their_main_institution():
    affiliations = [
        aff("1", "2023", "Co", "UiB", "u"),
        aff("2", "2023", "Co", "UiO", "o"),
        aff("2", "2023", "Co", "UiB", "u"),
    ]
    _, out = bpp.partner_data(
        affiliations, [inst("UiB", "u"), inst("UiO", "o")], ["Ann A"]
    )
    # All of Co's publications count for UiB, their main institution
    assert [(i["name"], i["pubs"], i["coauthors"]) for i in out] == [
        ("UiB", [0, 1], [[["Co", [2021, 2016]]], [["Co", [2021, 2016]]]])
    ]


def test_excluded_affiliations_are_left_out():
    affiliations = [
        aff("1", "2022", "Ricardo Ruíz\u2010Baier", "Sechenov University", "s"),
        aff("1", "2022", "Ricardo Ruíz\u2010Baier", "Monash University", "m"),
        aff("2", "2022", "Ivan Other", "Sechenov University", "s"),
    ]
    institutions = [
        inst("Sechenov University", "s", country="RU"),
        inst("Monash University", "m", country="AU"),
    ]
    _, out = bpp.partner_data(
        affiliations,
        institutions,
        ["Ann A"],
        exclusions=[("Ricardo Ruiz-Baier", "Sechenov University")],
    )
    # Ruiz-Baier counts only for Monash; Sechenov stays for another co-author
    assert {i["name"]: i["coauthors"] for i in out} == {
        "Monash University": [[["Ricardo Ruíz\u2010Baier", [2021, 2016]]]],
        "Sechenov University": [[["Ivan Other", [2021, 2016]]]],
    }


def test_merged_institutions_are_counted_once():
    affiliations = [
        aff(
            "1", "2023", "Geir R", "Sørlandet Hospital Arendal", "a", type="healthcare"
        ),
        aff("1", "2023", "Geir R", "Sørlandet Sykehus", "b", type="healthcare"),
        aff("2", "2023", "Per E", "Sørlandet Hospital Arendal", "a", type="healthcare"),
        # The investigator's own affiliation is not a collaborating institution
        aff("2", "2023", "Ann A", "University of Bergen", "c", investigator="Ann A"),
    ]
    institutions = [
        inst(
            "Sørlandet Hospital Arendal",
            "a",
            "healthcare",
            "Arendal",
            lat="58",
            lon="8",
        ),
        inst("Sørlandet Sykehus", "b", "healthcare", "Kristiansand", lat="58", lon="8"),
        inst("University of Bergen", "c", "education", "Bergen", lat="60", lon="5"),
    ]
    merges = {
        "Sørlandet Hospital Arendal": "Sørlandet sykehus",
        "Sørlandet Sykehus": "Sørlandet sykehus",
    }
    _, out = bpp.partner_data(affiliations, institutions, ["Ann A"], merges=merges)
    assert [(i["name"], i["city"], i["pubs"], i["coauthors"]) for i in out] == [
        (
            "Sørlandet sykehus",
            "Arendal",
            [0, 1],
            [
                [["Geir R", [2021, 2016]]],
                [["Per E", [2021, 2016]]],
            ],
        )
    ]


def test_research_council_details():
    found = {
        "found": "yes",
        "total_funding_nok": "7000992",
        "programmes": "FRINATEK",
        "application_type": "Forskerprosjekt",
        "lead": "Marie Elisabeth Rognes",
        "title_no": "",
        "achieved_effects": "",
    }
    prosjektbanken = {
        "250731": {**found, "lead_institution": "Simula Research Laboratory AS"},
        "248828": {
            **found,
            "lead_institution": "Universitetet i Oslo",
            "total_funding_nok": "40369867",
        },
        "357482": {
            **found,
            "lead_institution": "Simula Research Laboratory AS",
            "total_funding_nok": "",
        },
        "360005": {"found": "no"},
    }
    assert bpp.rcn_details("250731", prosjektbanken)["funding"] == 7000992
    assert bpp.rcn_details("250731", prosjektbanken)["ledHere"] is True
    # Led elsewhere: marked, so it is not added to the Simula total
    assert bpp.rcn_details("248828", prosjektbanken)["ledHere"] is False
    # Found but no amount yet; not found at all
    assert bpp.rcn_details("357482", prosjektbanken)["funding"] is None
    assert bpp.rcn_details("360005", prosjektbanken) is None
    assert bpp.rcn_details("", prosjektbanken) is None


def test_page_loads_nothing_from_other_sites():
    # Fonts and scripts are served from ../site/assets, so that visitors'
    # browsers make no requests elsewhere (links the reader follows are fine)
    site = bpp.OUTPUT.parent
    for page in [bpp.TEMPLATE, bpp.OUTPUT]:
        html = page.read_text(encoding="utf-8")
        tags = [
            t for t in re.findall(r"<[a-z]+\b[^>]*>", html) if not t.startswith("<a ")
        ]
        loaded = [u for t in tags for u in re.findall(r'\b(?:src|href)="([^"]*)"', t)]
        assert "@import" not in html and "url(http" not in html, page.name
        for url in loaded:
            if url.startswith("data:"):
                continue
            assert not re.match(r"[a-z]+:|//", url), (page.name, url)
            assert (site / url).exists(), (page.name, url)


def test_records_of_the_same_person_are_merged(tmp_path):
    path = tmp_path / "person_merges.csv"
    path.write_text(
        "author,openalex_author_id,same_as,note\n"
        "Sylvia Saalfield,A2,A1,misspelt\n"
        "Kei Yamamoto,,A3,no ID on one paper\n",
        encoding="utf-8",
    )
    people = bpp.read_person_merges(path)
    assert people == {"A2": "A1", "kei yamamoto": "A3"}
    affiliations = [
        aff("1", "2023", "Sylvia Saalfield", "Magdeburg", "m", openalex_author_id="A2"),
        aff("2", "2023", "Sylvia Saalfeld", "Magdeburg", "m", openalex_author_id="A1"),
        aff("3", "2023", "Kei Yamamoto", "UiO", "u"),
        aff(
            "4",
            "2023",
            "Kei Yamamoto",
            "Simula Research Laboratory",
            "s",
            openalex_author_id="A3",
        ),
        aff(
            "5",
            "2023",
            "Kei Yamamoto",
            "Simula Research Laboratory",
            "s",
            openalex_author_id="A3",
        ),
    ]
    found, _ = bpp.main_institutions(affiliations, 2016, people=people)
    # One Sylvia Saalfeld, named as in the record kept, with both papers;
    # Kei Yamamoto is one person, mainly at Simula, so not a co-author
    assert {c: (v["name"], len(v["rows"])) for c, v in found.items()} == {
        "A1": ("Sylvia Saalfeld", 2)
    }
    assert bpp.read_person_merges(tmp_path / "missing.csv") == {}


def test_listed_simula_colleagues_are_left_out(tmp_path):
    path = tmp_path / "simula_colleagues.csv"
    path.write_text(
        "author,openalex_author_id,note\nBastian Zapf,A1,Simula\nNo Id,,Simula\n",
        encoding="utf-8",
    )
    colleagues = bpp.read_colleagues(path)
    assert colleagues == {"A1", "no id"}
    affiliations = [
        aff(
            "1",
            "2023",
            "Bastian Zapf",
            "University of Oslo",
            "u",
            openalex_author_id="A1",
        ),
        aff("1", "2023", "No Id", "University of Oslo", "u"),
        aff("1", "2023", "Ann Other", "University of Oslo", "u"),
    ]
    found, _ = bpp.main_institutions(affiliations, 2016, colleagues=colleagues)
    # Only the co-author who is not a listed colleague counts
    assert [v["name"] for v in found.values()] == ["Ann Other"]
    assert bpp.read_colleagues(tmp_path / "missing.csv") == set()


def test_institutions_set_by_hand():
    affiliations = [
        aff("1", "2023", "Placed Here", "", ""),
        aff("2", "2023", "Someone", "University of Oslo", "u"),
    ]
    found, country_of = bpp.main_institutions(
        affiliations, 2016, fixed={"placed here": "University of Oslo"}
    )
    assert {v["name"]: v["main"] for v in found.values()} == {
        "Placed Here": "University of Oslo",
        "Someone": "University of Oslo",
    }
    assert country_of["University of Oslo"] == "NO"
    assert bpp.read_corrections(Path("missing.csv")) == {}
