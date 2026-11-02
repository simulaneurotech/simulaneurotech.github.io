import json

import collaboration_map
from publication_data import load

INV = "Investigator"


def make_fixture(dataset):
    return dataset(
        [
            ("Ann A", "SRL", INV, "1", ""),
            ("Bø Bee", "SimulaMet", INV, "2", ""),
            ("Cee C", "SRL", INV, "3", ""),
            ("Rachel Thomas", "", "Director for Strategy and Development", "4", ""),
        ],
        [
            {
                "id": "10",
                "year": "2021",
                "title": "T10",
                "authors": [
                    ("Ann", "A", "1"),
                    ("Bø", "Bee", "2"),
                    ("Cee", "C", "3"),
                    ("Rachel", "Thomas", "4"),
                ],
            },
            {
                "id": "11",
                "year": "2020",
                "title": "T11",
                "authors": [("Ann", "A", "1"), ("Bø", "Bee", "2")],
            },
            {
                "id": "12",
                "year": "2019",
                "title": "T12",
                "authors": [("Ann", "A", "1"), ("Eve", "Out", "70")],
            },
            {
                "id": "13",
                "year": "2018",
                "title": "T13",
                "authors": [("Cee", "C", "3"), ("Eve", "Out", "70")],
            },
        ],
    )


def test_collect_finds_shared_papers_pairs_and_years(dataset):
    data = collaboration_map.collect(load(*make_fixture(dataset)))

    # Rachel Thomas is left out, even though she appears on paper 10
    assert data["people"] == [
        {"name": "Ann A", "aff": "SRL", "total": 3, "shared": 2, "cristin": "1"},
        {"name": "Bø Bee", "aff": "SimulaMet", "total": 2, "shared": 2, "cristin": "2"},
        {"name": "Cee C", "aff": "SRL", "total": 2, "shared": 1, "cristin": "3"},
    ]
    # Only papers with two or more investigators, with all of them listed
    assert set(data["papers"]) == {"10", "11"}
    assert data["papers"]["10"]["authors"] == ["Ann A", "Bø Bee", "Cee C"]
    assert data["papers"]["11"]["year"] == "2020"
    # A three-author paper links all three pairs; strongest pair first,
    # newest paper first within a pair
    assert data["pairs"][0] == {"a": "Ann A", "b": "Bø Bee", "ids": ["10", "11"]}
    assert {(p["a"], p["b"]): p["ids"] for p in data["pairs"][1:]} == {
        ("Ann A", "Cee C"): ["10"],
        ("Bø Bee", "Cee C"): ["10"],
    }
    # Each shared paper counts once per year, however many authors it has
    assert data["byYear"] == {"2020": 1, "2021": 1}
    # All publications per year, each counted once
    assert data["totalByYear"] == {"2018": 1, "2019": 1, "2020": 1, "2021": 1}
    # Eve, outside the centre, links Ann and Cee through separate papers
    assert data["outside"] == [
        {
            "name": "Eve Out",
            "inst": "Simula",
            "links": {"Ann A": 1, "Cee C": 1},
            "linked": ["Ann A", "Cee C"],
        }
    ]
    assert data["indirect"] == [{"a": "Ann A", "b": "Cee C", "people": [0]}]


def test_main_fills_template(dataset, tmp_path, monkeypatch):
    publications, contributors = make_fixture(dataset)
    output = tmp_path / "map.html"
    monkeypatch.setattr(
        "sys.argv",
        ["collaboration_map.py", str(publications), str(contributors), str(output)],
    )

    collaboration_map.main()

    html = output.read_text(encoding="utf-8")
    assert "__DATA__" not in html
    line = next(line for line in html.splitlines() if line.startswith("const DATA = "))
    data = json.loads(line.removeprefix("const DATA = ").removesuffix(";"))
    assert data == collaboration_map.collect(load(publications, contributors))
