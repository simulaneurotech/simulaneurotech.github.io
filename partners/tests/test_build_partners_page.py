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


def test_partner_data_marks_simula_as_own():
    affiliations = [
        {
            "result_id": "1",
            "year": "2021",
            "institution": "Simula Research Laboratory",
            "ror": "https://ror.org/00vn06n10",
            "investigators": "Ann A",
            "author": "Carl Co",
        },
        {
            "result_id": "1",
            "year": "2021",
            "institution": "Oslo University Hospital",
            "ror": "r2",
            "investigators": "Ann A",
            "author": "Carl Co",
        },
        {
            "result_id": "2",
            "year": "2019",
            "institution": "Oslo University Hospital",
            "ror": "r2",
            "investigators": "Ann A; Bo B",
            "author": "Carl Co",
        },
    ]
    institutions = [
        {
            "institution": "Simula Research Laboratory",
            "ror": "https://ror.org/00vn06n10",
            "country": "NO",
            "type": "facility",
            "city": "Oslo",
            "latitude": "59.9",
            "longitude": "10.7",
        },
        {
            "institution": "Oslo University Hospital",
            "ror": "r2",
            "country": "NO",
            "type": "healthcare",
            "city": "Oslo",
            "latitude": "59.9",
            "longitude": "10.7",
        },
    ]
    papers = {
        "1": {"title": "Paper one", "doi": "https://doi.org/10.1/a", "nva_id": "n1"},
        "2": {"title": "Paper two", "doi": "", "nva_id": "n2"},
    }
    publications, out = bpp.partner_data(
        affiliations, institutions, ["Ann A", "Bo B"], papers
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
    hospital = next(i for i in out if i["name"] == "Oslo University Hospital")
    assert (hospital["type"], hospital["own"], hospital["pubs"]) == (
        "Hospitals",
        False,
        [0, 1],
    )
    assert next(i for i in out if i["name"].startswith("Simula"))["own"] is True


def test_excluded_affiliations_are_left_out():
    def aff(rid, author, institution, ror):
        return {
            "result_id": rid,
            "year": "2022",
            "institution": institution,
            "ror": ror,
            "investigators": "Ann A",
            "author": author,
            "investigator": "",
        }

    affiliations = [
        aff("1", "Ricardo Ruíz\u2010Baier", "Sechenov University", "s"),
        aff("1", "Ricardo Ruíz\u2010Baier", "Monash University", "m"),
        aff("2", "Ivan Other", "Sechenov University", "s"),
    ]
    institutions = [
        {
            "institution": n,
            "ror": r,
            "country": c,
            "type": "education",
            "city": "",
            "latitude": "",
            "longitude": "",
        }
        for n, r, c in [
            ("Sechenov University", "s", "RU"),
            ("Monash University", "m", "AU"),
        ]
    ]
    _, out = bpp.partner_data(
        affiliations,
        institutions,
        ["Ann A"],
        exclusions=[("Ricardo Ruiz-Baier", "Sechenov University")],
    )
    # Ruiz-Baier counts only for Monash; Sechenov stays for another co-author
    assert {i["name"]: i["coauthors"] for i in out} == {
        "Monash University": [[["Ricardo Ruíz\u2010Baier", "unclassified"]]],
        "Sechenov University": [[["Ivan Other", "unclassified"]]],
    }


def test_merged_institutions_are_counted_once():
    def aff(rid, institution, ror, author):
        return {
            "result_id": rid,
            "year": "2023",
            "institution": institution,
            "ror": ror,
            "investigators": "Ann A",
            "author": author,
            "investigator": "",
        }

    affiliations = [
        aff("1", "Sørlandet Hospital Arendal", "a", "Geir R"),
        aff("1", "Sørlandet Sykehus", "b", "Geir R"),
        aff("2", "Sørlandet Hospital Arendal", "a", "Per E"),
        # The investigator's own affiliation is not a collaborating institution
        {**aff("2", "University of Bergen", "c", "Ann A"), "investigator": "Ann A"},
    ]
    institutions = [
        {
            "institution": n,
            "ror": r,
            "country": "NO",
            "type": t,
            "city": c,
            "latitude": "58",
            "longitude": "8",
        }
        for n, r, t, c in [
            ("Sørlandet Hospital Arendal", "a", "healthcare", "Arendal"),
            ("Sørlandet Sykehus", "b", "healthcare", "Kristiansand"),
            ("University of Bergen", "c", "education", "Bergen"),
        ]
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
            [[["Geir R", "unclassified"]], [["Per E", "unclassified"]]],
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


def test_only_relevant_publications_are_used():
    affiliations = [
        {
            "result_id": rid,
            "year": "2023",
            "institution": "UiB",
            "ror": "u",
            "investigators": "Ann A",
            "author": "Co",
            "investigator": "",
            "affiliation": "Department of Mathematics",
        }
        for rid in ("1", "2")
    ]
    institutions = [
        {
            "institution": "UiB",
            "ror": "u",
            "country": "NO",
            "type": "education",
            "city": "",
            "latitude": "",
            "longitude": "",
        }
    ]
    publications, out = bpp.partner_data(
        affiliations,
        institutions,
        ["Ann A"],
        relevant={"2"},
        rules=bpp.read_field_rules(bpp.HERE / "field_rules.csv"),
    )
    assert len(publications) == 1
    assert out[0]["coauthors"] == [[["Co", "math"]]]
