import csv

import coauthorship

INV = "Investigator"


def read_csv(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.reader(f))


def test_shared_publications_are_counted(dataset, monkeypatch):
    publications, contributors = dataset(
        [
            ("Ann A.", "SRL", INV, "1", ""),
            ("Bø Bee", "SRL", INV, "2", ""),
            ("Cee C", "SRL", INV, "3", ""),
        ],
        [
            {
                "id": "10",
                "year": "2020",
                "title": "P10",
                "authors": [("Ann", "A.", "1"), ("Bø", "Bee", "2")],
            },
            {
                "id": "11",
                "year": "2021",
                "title": "P11",
                "authors": [("Ann", "A.", "1"), ("Bø", "Bee", "2")],
            },
            # Duplicate record of paper 11: must not be counted twice
            {
                "id": "12",
                "year": "2021",
                "title": "p11",
                "authors": [("Ann", "A.", "1"), ("Bø", "Bee", "2")],
            },
            {
                "id": "99",
                "year": "2019",
                "title": "P99",
                "authors": [("Cee", "C", "3")],
            },
        ],
    )
    monkeypatch.setattr(
        "sys.argv", ["coauthorship.py", str(publications), str(contributors)]
    )

    coauthorship.main()

    # Only pairs with shared results appear, sorted by count
    assert read_csv(publications / "coauthorship_edges.csv") == [
        ["person_a", "person_b", "shared"],
        ["Ann A.", "Bø Bee", "2"],
    ]
    # Symmetric matrix with each person's total on the diagonal
    assert read_csv(publications / "coauthorship_matrix.csv") == [
        ["", "Ann A.", "Bø Bee", "Cee C"],
        ["Ann A.", "2", "2", "0"],
        ["Bø Bee", "2", "2", "0"],
        ["Cee C", "0", "0", "1"],
    ]
