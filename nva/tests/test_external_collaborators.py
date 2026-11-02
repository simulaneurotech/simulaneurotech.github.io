import csv

import external_collaborators
from publication_data import load

INV = "Investigator"


def test_outside_coauthors_and_bridges(dataset, monkeypatch):
    publications, contributors = dataset(
        [("Ann A", "SRL", INV, "1", ""), ("Bo B", "SRL", INV, "2", "")],
        [
            {
                "id": "10",
                "year": "2020",
                "title": "P10",
                "authors": [
                    ("Ann", "A", "1"),
                    ("Carl", "Eng", "50"),
                    ("Dina", "Fox", ""),
                ],
            },
            {
                "id": "11",
                "year": "2021",
                "title": "P11",
                "authors": [("Ann", "A", "1"), ("Carl", "Eng", "50")],
            },
            {
                "id": "12",
                "year": "2022",
                "title": "P12",
                "authors": [("Bo", "B", "2"), ("C.", "Eng", "")],
            },
        ],
    )
    monkeypatch.setattr(
        "sys.argv", ["external_collaborators.py", str(publications), str(contributors)]
    )

    external_collaborators.main()

    with (contributors / "external_coauthors.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [(r["investigator"], r["coauthor"], r["shared"]) for r in rows] == [
        ("Ann A", "Carl Eng", "2"),
        ("Ann A", "Dina Fox", "1"),
        ("Bo B", "Carl Eng", "1"),
    ]
    # Carl Eng (also listed as "C. Eng") links Ann and Bo; Dina Fox does not
    with (contributors / "bridges.csv").open(encoding="utf-8") as f:
        bridges = list(csv.DictReader(f))
    assert bridges == [
        {
            "coauthor": "Carl Eng",
            "institution": "Simula",
            "n_investigators": "2",
            "total": "3",
            "investigators": "Ann A (2); Bo B (1)",
        }
    ]


def test_indirect_links_need_separate_papers(dataset):
    publications, contributors = dataset(
        [
            ("Ann A", "SRL", INV, "1", ""),
            ("Bo B", "SRL", INV, "2", ""),
            ("Cy C", "SRL", INV, "3", ""),
        ],
        [
            # Dina is only on Ann and Bo's joint paper: no indirect link
            {
                "id": "10",
                "year": "2020",
                "title": "P10",
                "authors": [("Ann", "A", "1"), ("Bo", "B", "2"), ("Dina", "Fox", "60")],
            },
            # Carl has separate papers with Ann and with Cy: indirect link
            {
                "id": "11",
                "year": "2021",
                "title": "P11",
                "authors": [("Ann", "A", "1"), ("Carl", "Eng", "50")],
            },
            {
                "id": "12",
                "year": "2022",
                "title": "P12",
                "authors": [("Cy", "C", "3"), ("Carl", "Eng", "50")],
            },
        ],
    )

    links = external_collaborators.indirect_links(load(publications, contributors))

    assert links == {("Ann A", "Cy C"): ["id:50"]}
