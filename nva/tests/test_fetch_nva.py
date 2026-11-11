import csv

import fetch_nva

BOOK = "https://api.nva.unit.no/publication/book-1"


def person(name, pid="", role="Creator", inst=""):
    identity = {"name": name}
    if pid:
        identity["id"] = f"https://api.nva.unit.no/cristin/person/{pid}"
    contributor = {"identity": identity, "role": {"type": role}}
    if inst:
        org = f"https://api.nva.unit.no/cristin/organization/{inst}.1.0.0"
        contributor["affiliations"] = [{"id": org}]
    return contributor


def hit(identifier, kind, title, contributors, old_id="", context=None):
    for i, c in enumerate(contributors, 1):
        c["sequence"] = str(i)
    ids = [{"type": "CristinIdentifier", "value": old_id}] if old_id else []
    return {
        "identifier": identifier,
        "additionalIdentifiers": ids,
        "entityDescription": {
            "mainTitle": title,
            "publicationDate": {"year": "2021"},
            "contributors": contributors,
            "reference": {
                "doi": "",
                "publicationInstance": {"type": kind},
                "publicationContext": context or {},
            },
        },
    }


def read(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_fetch_writes_publications_authors_and_editors(tmp_path, monkeypatch):
    journal = {"type": "Journal", "name": "J. Num."}
    results = {
        "1": [
            hit(
                "a",
                "AcademicArticle",
                "Article",
                [person("Ann Berg", "1", inst="7498"), person("Pieter van den Bosch")],
                "100",
                journal,
            ),
            # A talk: not kept
            hit("b", "Lecture", "Talk", [person("Ann Berg", "1")], "101"),
            # A chapter where the book's editor is listed as editor: not an author
            hit(
                "c",
                "AcademicChapter",
                "Chapter",
                [person("Ann Berg", "1"), person("Tor Veit", "2", role="Editor")],
                "102",
                {"id": BOOK},
            ),
        ],
        # Ann's second profile; record "d" is only in NVA, without an older ID
        "9": [hit("d", "Textbook", "Book", [person("Ann Berg", "9")])],
    }
    responses = {
        BOOK: {
            "entityDescription": {
                "contributors": [person("Tor Veit", "2", role="Editor")]
            }
        },
        f"{fetch_nva.API}/cristin/organization/7498.0.0.0": {
            "labels": {"en": "Simula"},
            "country": "NO",
        },
    }
    monkeypatch.setattr(fetch_nva, "find_person", lambda name: "1")
    monkeypatch.setattr(fetch_nva, "search_results", results.get)
    monkeypatch.setattr(fetch_nva, "get", lambda url, params=None: responses[url])
    monkeypatch.setattr(fetch_nva.time, "sleep", lambda s: None)

    investigators = tmp_path / "investigators.csv"
    investigators.write_text(
        "name,affiliation,role,extra_person_ids\nAnn Berg,SRL,Investigator,9\n",
        encoding="utf-8",
    )
    publications, contributors = tmp_path / "publications", tmp_path / "contributors"
    monkeypatch.setattr(
        "sys.argv",
        ["fetch_nva.py", str(investigators), str(publications), str(contributors)],
    )

    fetch_nva.main()

    rows = read(publications / "Ann_Berg.csv")
    assert {(r["result_id"], r["category"], r["nva_id"]) for r in rows} == {
        ("100", "Academic article", "a"),
        ("102", "Academic chapter/article/Conference paper", "c"),
        ("d", "Textbook", "d"),
    }
    assert next(r for r in rows if r["nva_id"] == "a")["journal"] == "J. Num."
    assert read(publications / "person_ids.csv")[0]["extra_person_ids"] == "9"

    authors = {
        (r["result_id"], r["first_name"], r["surname"], r["person_id"])
        for r in read(contributors / "contributors.csv")
    }
    assert authors == {
        ("100", "Ann", "Berg", "1"),
        ("100", "Pieter", "van den Bosch", ""),
        ("102", "Ann", "Berg", "1"),
        ("d", "Ann", "Berg", "9"),
    }
    assert read(contributors / "institutions.csv") == [
        {"institution_id": "7498", "name": "Simula", "country": "NO"}
    ]
    assert read(contributors / "chapters.csv") == [
        {"result_id": "102", "part_of": BOOK}
    ]
    assert read(contributors / "editors.csv") == [
        {
            "part_of": BOOK,
            "person_id": "2",
            "first_name": "Tor",
            "surname": "Veit",
        }
    ]


def test_split_name():
    assert fetch_nva.split_name("Per-Arne Lund") == ("Per-Arne", "Lund")
    assert fetch_nva.split_name("Anna de Vries") == ("Anna", "de Vries")
    assert fetch_nva.split_name("Pieter Jan van den Bosch") == (
        "Pieter Jan",
        "van den Bosch",
    )
    assert fetch_nva.split_name("Plato") == ("", "Plato")


def test_venue():
    assert fetch_nva.venue({"type": "Journal", "name": "J. Num."}) == "J. Num."
    anthology = {
        "type": "Anthology",
        "entityDescription": {
            "mainTitle": "Automated Solution of Differential Equations",
            "reference": {"publicationContext": {"series": {"name": "Lecture Notes"}}},
        },
    }
    assert (
        fetch_nva.venue(anthology)
        == "In: Automated Solution of Differential Equations (Lecture Notes)"
    )
    book = {
        "type": "Book",
        "publisher": {"name": "Springer"},
        "series": {"name": "Texts"},
    }
    assert fetch_nva.venue(book) == "Springer, Texts"
    assert fetch_nva.venue({}) == ""
