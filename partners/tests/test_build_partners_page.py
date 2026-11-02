import re

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
        "investigators": "Kent-Andre Mardal; Marie E. Rognes",
        "funders": "Research Council of Norway",
        "grants": "250731",
        "partners": "University of Oslo | Oslo University Hospital",
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
    assert p["partners"] == ["University of Oslo", "Oslo University Hospital"]


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
                [["Carl Co", "clinical", [2021, 2016]]],
                [["Carl Co", "clinical", [2016]]],
            ],
        )
    ]


def test_coauthors_count_only_at_their_main_institution():
    rules = bpp.read_field_rules(bpp.HERE / "field_rules.csv")
    affiliations = [
        aff("1", "2023", "Co", "UiB", "u", affiliation="Department of Mathematics"),
        aff(
            "2",
            "2023",
            "Co",
            "UiO",
            "o",
            affiliation="Institute of Basic Medical Sciences",
        ),
        aff("2", "2023", "Co", "UiB", "u", affiliation="Department of Mathematics"),
    ]
    _, out = bpp.partner_data(
        affiliations, [inst("UiB", "u"), inst("UiO", "o")], ["Ann A"], rules=rules
    )
    # All of Co's publications count for UiB, in the field of the UiB row
    assert [(i["name"], i["pubs"], i["coauthors"]) for i in out] == [
        (
            "UiB",
            [0, 1],
            [[["Co", "math", [2021, 2016]]], [["Co", "math", [2021, 2016]]]],
        )
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
        "Monash University": [
            [["Ricardo Ruíz\u2010Baier", "unclassified", [2021, 2016]]]
        ],
        "Sechenov University": [[["Ivan Other", "unclassified", [2021, 2016]]]],
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
                [["Geir R", "clinical", [2021, 2016]]],
                [["Per E", "clinical", [2021, 2016]]],
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


def test_field_group():
    rules = bpp.read_field_rules(bpp.HERE / "field_rules.csv")

    def group(affiliation, institution="Some University", type_="education", author=""):
        row = {
            "affiliation": affiliation,
            "institution": institution,
            "type": type_,
            "openalex_author_id": author,
        }
        return bpp.field_group(row, rules, {"A1": "Neuroscience", "A2": "Medicine"})

    assert (
        group(
            "Department of Neurosurgery, Oslo University Hospital",
            "Oslo University Hospital",
            "healthcare",
        )
        == "clinical"
    )
    assert group("Institute of Basic Medical Sciences, University of Oslo") == "basic"
    assert group("Department of Mathematics, University of Oslo") == "math"
    # The institution's own name does not decide: "Life Sciences" is the university
    assert (
        group(
            "Faculty of Science and Technology, Norwegian University of Life Sciences",
            "Norwegian University of Life Sciences",
        )
        == "math"
    )
    # No department: hospital type, then the author's own field
    assert (
        group("Oslo University Hospital", "Oslo University Hospital", "healthcare")
        == "clinical"
    )
    assert group("University of Oslo", "University of Oslo", author="A1") == "basic"
    assert group("University of Oslo", "University of Oslo", author="A2") == "clinical"
    assert group("University of Oslo", "University of Oslo") == "unclassified"


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
