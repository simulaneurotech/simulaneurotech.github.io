import fetch_openalex


def test_affiliations_and_partner_institutions():
    work = {
        "authorships": [
            {
                "author": {"display_name": "Ann A", "id": "https://openalex.org/A1"},
                "institutions": [
                    {
                        "display_name": "UiO",
                        "ror": "r1",
                        "country_code": "NO",
                        "type": "education",
                    }
                ],
            },
            {
                "author": {"display_name": "Carl C"},
                "institutions": [
                    {
                        "display_name": "UiO",
                        "ror": "r1",
                        "country_code": "NO",
                        "type": "education",
                    },
                    {
                        "display_name": "Charité",
                        "ror": "r2",
                        "country_code": "DE",
                        "type": "healthcare",
                    },
                ],
            },
        ]
    }
    rows = fetch_openalex.affiliation_rows("10", "2022", "10.1/x", work, ["Ann A"])
    assert [(r["author_position"], r["institution"]) for r in rows] == [
        (1, "UiO"),
        (2, "UiO"),
        (2, "Charité"),
    ]
    rows += fetch_openalex.affiliation_rows(
        "11", "2023", "10.1/y", work, ["Ann A", "Bo B"]
    )
    places = {"r1": ("Oslo", 59.9, 10.7)}
    out = fetch_openalex.partner_institutions(rows, places)
    # Each publication counts once per institution, however many authors are there
    assert [(r["institution"], r["publications"], r["city"]) for r in out] == [
        ("Charité", 2, ""),
        ("UiO", 2, "Oslo"),
    ]
    assert out[1]["investigators"] == "Ann A (2); Bo B (1)"


def test_which_investigator():
    on_paper = ["Jon-Andre Lund", "Kari T. Lunde", "Selin Kaya Demir"]
    assert (
        fetch_openalex.which_investigator("Jon\u2010André Lund", on_paper)
        == "Jon-Andre Lund"
    )
    assert (
        fetch_openalex.which_investigator("Lunde, Kari T.", on_paper) == "Kari T. Lunde"
    )
    assert fetch_openalex.which_investigator("K. T. Lunde", on_paper) == "Kari T. Lunde"
    assert (
        fetch_openalex.which_investigator("Selin Kaya", on_paper) == "Selin Kaya Demir"
    )
    # Same surname, different first name, or not on the paper: not an investigator
    assert fetch_openalex.which_investigator("Torbjørn Lunde", on_paper) == ""
    assert fetch_openalex.which_investigator("Odd Vik", on_paper) == ""


def test_investigators_own_affiliations_are_not_partners():
    work = {
        "authorships": [
            {
                "author": {"display_name": "Kari T. Lunde"},
                "institutions": [
                    {
                        "display_name": "University of Bergen",
                        "ror": "r1",
                        "country_code": "NO",
                        "type": "education",
                    }
                ],
            },
            {
                "author": {"display_name": "Carl Co"},
                "institutions": [
                    {
                        "display_name": "Charité",
                        "ror": "r2",
                        "country_code": "DE",
                        "type": "healthcare",
                    }
                ],
            },
        ]
    }
    rows = fetch_openalex.affiliation_rows(
        "10", "2022", "10.1/x", work, ["Kari T. Lunde"]
    )
    assert [r["investigator"] for r in rows] == ["Kari T. Lunde", ""]
    out = fetch_openalex.partner_institutions(rows, {})
    assert [r["institution"] for r in out] == ["Charité"]


def test_emails_are_removed_from_affiliations():
    text = "Department of Neurosurgery, Oslo University Hospital, Oslo, Norway. Electronic address: someone@ous-hf.no"
    assert (
        fetch_openalex.without_emails(text)
        == "Department of Neurosurgery, Oslo University Hospital, Oslo, Norway"
    )
    assert (
        fetch_openalex.without_emails("Dept. of Mathematics; a.b@uio.no")
        == "Dept. of Mathematics"
    )
