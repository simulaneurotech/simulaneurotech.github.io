import json

import fetch_prosjektbanken as fp


def page(state):
    data = {"props": {"pageProps": {"initialState": {"PROJECT": state}}}}
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script></html>'


PROJECT = {
    "title": "The Numerical Waterscape of the Brain",
    "alternativeTitle": "Beregninger av hjernens vannveier",
    "leadName": "Kari Lunde",
    "organisation": [
        [
            "Instituttsektor",
            "Øvrige forskningsinstitutter",
            "SIMULA RESEARCH LABORATORY AS",
        ]
    ],
    "duration": {"startYear": 2016, "endYear": 2020},
    "totalFunding": 7000992,
    "pastActivities": [{"activity": "FRINATEK-Fri prosjektstøtte", "year": 2016}],
    "currentActivity": {"activity": "FRINATEK-Fri prosjektstøtte", "year": 2020},
    "applicationTypes": [["Forskerprosjekt", "Unge forskertalenter"]],
    "fundingBodies": ["Kunnskapsdepartementet"],
    "summary": "Summary.",
    "achievedEffects": "Effects.",
}


def test_grants_of_research_council_projects():
    rows = [
        {"funders": "Research Council of Norway", "grants": "250731"},
        {"funders": "ERC; EU", "grants": "714892"},
        {"funders": "Research Council of Norway", "grants": ""},
        {
            "funders": "Research Council of Norway; Novo Nordisk Foundation",
            "grants": "324239; 250731",
        },
    ]
    assert fp.grants(rows) == ["250731", "324239"]


def test_page_project_and_row():
    project = fp.page_project(page({"httpStatus": 200, "project": PROJECT}))
    row = fp.to_row("250731", project)
    assert row["found"] == "yes"
    assert (row["lead"], row["lead_institution"]) == (
        "Kari Lunde",
        "Simula Research Laboratory AS",
    )
    assert (row["start"], row["end"], row["total_funding_nok"]) == (2016, 2020, 7000992)
    assert row["programmes"] == "FRINATEK"
    assert row["application_type"] == "Forskerprosjekt – Unge forskertalenter"
    # A project the page does not find
    assert fp.page_project(page({"httpStatus": 404})) is None
    assert fp.to_row("360005", None) == {"grant": "360005", "found": "no"}


def test_institution_name():
    assert (
        fp.institution(
            ["UoH-sektor", "Universiteter", "UNIVERSITETET I OSLO", "MN", "IBV"]
        )
        == "Universitetet i Oslo"
    )
    assert (
        fp.institution(["Instituttsektor", "Øvrige", "SIMULA RESEARCH LABORATORY AS"])
        == "Simula Research Laboratory AS"
    )
