from publication_data import compatible, load, merge_duplicates, strip_editors

INV = "Investigator"


def record(year, title, journal="", doi=""):
    return {
        "year": year,
        "title": title,
        "category": "Academic article",
        "journal": journal,
        "doi": doi,
    }


def test_merge_duplicates():
    records = {
        # Same paper registered twice, one year apart: keep the one with a DOI
        "1": record("2020", "A robust method", "J. Num.", "https://doi.org/10.1/a"),
        "2": record("2021", "A Robust Method", "J. Num."),
        # Preprint three years before the journal version: keep the journal
        "3": record("2019", "Neural nets", "arXiv.org", "https://doi.org/10.48550/x"),
        "4": record("2022", "Neural Nets", "Sci. Rep.", "https://doi.org/10.1/b"),
        # Two editions of a book, eleven years apart: kept separate
        "5": record("1998", "Introduction to PDEs"),
        "6": record("2009", "Introduction to PDEs"),
        # Same DOI but a different paper (wrong DOI on one record): separate
        "7": record("2018", "Drug response maturation", doi="10.1/c"),
        "8": record("2020", "Translation of drug effects", doi="10.1/c"),
        # Same DOI, slightly different title: merged
        "9": record(
            "2018", "Self-powered IoT device for indoor applications", doi="10.1/d"
        ),
        "10": record(
            "2018",
            "Self-powered IoT device for indoor and outdoor applications",
            doi="https://doi.org/10.1/D",
        ),
        # No DOI, same year and journal, spelling variants: merged
        "11": record(
            "2002",
            "Einfuhrung in partielle differentalgleichungen, Ein numerischer zugang",
        ),
        "12": record(
            "2002",
            "Einführung in die Theorie der partiellen Differentialgleichungen; Ein numerischer Zugang",
        ),
        "13": record(
            "2002",
            "Multigrid block preconditioning for a coupled system of partial "
            "differential equations modeling the electrical activity in cardiac cells",
            "CMBBE",
        ),
        "14": record(
            "2002",
            "Multigrid block preconditioning for a coupled system of partial "
            "differential equations modeling the electrical activity in the heart",
            "CMBBE",
        ),
        # Part I and Part II of a paper: separate
        "15": record(
            "2010", "Splitting methods for the bidomain model, part I", "J. Comp."
        ),
        "16": record(
            "2010", "Splitting methods for the bidomain model, part II", "J. Comp."
        ),
        # Conference paper and its extended version a year later: separate
        "17": record(
            "2018", "Underlay device-to-device communications on multiple channels"
        ),
        "18": record(
            "2019",
            "Reliable underlay device-to-device communications on multiple channels",
        ),
    }

    canonical = merge_duplicates(records)

    assert canonical["2"] == canonical["1"] == "1"
    assert canonical["3"] == canonical["4"] == "4"
    assert canonical["5"] == "5" and canonical["6"] == "6"
    assert canonical["7"] == "7" and canonical["8"] == "8"
    assert canonical["9"] == canonical["10"]
    assert canonical["11"] == canonical["12"]
    assert canonical["13"] == canonical["14"]
    assert canonical["15"] != canonical["16"]
    assert canonical["17"] != canonical["18"]


def test_compatible_first_names():
    assert compatible("K.", "Kari")
    assert compatible("Jon", "Jon Erik")
    assert compatible("Ole-Martin", "Ole Martin")
    assert compatible("Bjorn S.", "Bjørn")
    assert compatible("OE", "Odd Einar")
    assert not compatible("Siri", "Sunniva P.")
    assert not compatible("Siv", "Sigrid")


def test_load_recognises_people(dataset):
    publications, contributors = dataset(
        [
            ("Ann A. Berg", "SRL", INV, "1", "9"),
            ("Bo Dahl", "SimulaMet", INV, "2", ""),
            ("Siri Lie", "", "Director", "3", ""),
        ],
        [
            # Ann under her second profile (9), Bo by ID
            {
                "id": "10",
                "year": "2020",
                "title": "P10",
                "authors": [("Ann", "Berg", "9"), ("Bo", "Dahl", "2")],
            },
            # Bo without an ID on Ann's paper; two outside authors without IDs
            {
                "id": "11",
                "year": "2021",
                "title": "P11",
                "authors": [
                    ("Ann", "Berg", "1"),
                    ("B.", "Dahl", ""),
                    ("Siv", "Holm", ""),
                    ("Sigrid", "Holm", ""),
                ],
            },
            # Outside author with an ID, and the same person as an initial elsewhere
            {
                "id": "12",
                "year": "2022",
                "title": "P12",
                "authors": [("Ann", "Berg", "1"), ("Carl", "Eng", "50")],
            },
            {
                "id": "13",
                "year": "2022",
                "title": "P13",
                "authors": [("Bo", "Dahl", "2"), ("C.", "Eng", "")],
            },
        ],
    )

    data = load(publications, contributors)

    # Siri Lie is not an investigator
    assert set(data.investigators) == {"Ann A. Berg", "Bo Dahl"}
    assert data.investigators["Ann A. Berg"]["ids"] == ["1", "9"]
    # Paper 11 counts for Bo, found by name; paper 10 for Ann, via ID 9
    assert data.papers_of["Ann A. Berg"] == {"10", "11", "12"}
    assert data.papers_of["Bo Dahl"] == {"10", "11", "13"}
    # Siv and Sigrid Holm stay separate; C. Eng is Carl Eng (ID 50)
    assert data.papers["11"]["authors"] == {
        "inv:Ann A. Berg",
        "inv:Bo Dahl",
        "name:siv|holm",
        "name:sigrid|holm",
    }
    assert data.papers["13"]["authors"] == {"inv:Bo Dahl", "id:50"}
    assert data.display("id:50") == "Carl Eng"
    assert data.institution("id:50") == "Simula"


def person(first, surname, pid=""):
    return {"first_name": first, "surname": surname, "person_id": pid}


def test_strip_editors():
    editors = [person("Tor", "Veit", "1"), person("Kai", "Mard", "2")]
    # Editors appended after the real authors are removed
    rows = [
        person("Ada", "Ell"),
        person("Tor", "Veit", "1"),
        person("Kai", "Mard", "2"),
    ]
    assert strip_editors(rows, editors) == (rows[:1], rows[1:])
    # An editor who is first author stays; matched by name across person IDs
    rows = [
        person("Kai", "Mard", "2"),
        person("Bo", "B"),
        person("T.", "Veit", "9"),
        person("Kai", "Mard"),
    ]
    assert strip_editors(rows, editors)[0] == rows[:2]
    # Each editor is removed at most once: an author-editor listed twice keeps one
    rows = [
        person("Ada", "Ell"),
        person("Kai", "Mard"),
        person("Kai", "Mard", "2"),
        person("Tor", "Veit", "1"),
    ]
    assert strip_editors(rows, editors)[0] == rows[:2]
    # Editors who wrote the chapter themselves are kept
    rows = [person("Tor", "Veit", "1"), person("Kai", "Mard", "2")]
    assert strip_editors(rows, editors) == (rows, [])
    # Not every editor is listed: nothing is removed
    rows = [person("Ada", "Ell"), person("Kai", "Mard", "2")]
    assert strip_editors(rows, editors) == (rows, [])


def test_load_removes_book_editors(dataset):
    book = "https://api.nva.unit.no/publication/book"
    publications, contributors = dataset(
        [("Ann Berg", "SRL", INV, "1", ""), ("Tor Veit", "SRL", INV, "2", "")],
        [
            # Chapter by Ann; editor Tor appended
            {
                "id": "20",
                "year": "2021",
                "title": "Chapter one",
                "authors": [("Ann", "Berg", "1"), ("Tor", "Veit", "2")],
            },
            # Bulk record of a chapter by Ann, with no book link; its linked
            # duplicate is clean, so the editor Tor is not counted
            {
                "id": "21",
                "year": "2021",
                "title": "Chapter two",
                "authors": [("Ann", "Berg", "1")],
            },
            {
                "id": "22",
                "year": "2021",
                "title": "Chapter Two",
                "doi": "10.1/x",
                "authors": [
                    ("Ann", "Berg", "1"),
                    ("Tor", "Veit", "2"),
                    ("Kim", "Lee", ""),
                ],
            },
        ],
        chapters={"20": book, "21": book, "22": ""},
        editors=[(book, "Tor", "Veit", "2")],
    )

    data = load(publications, contributors)

    assert data.papers_of["Tor Veit"] == set()
    assert len(data.papers_of["Ann Berg"]) == 2
    assert all(
        "inv:Tor Veit" not in p["authors"] and "name:kim|lee" not in p["authors"]
        for p in data.papers.values()
    )
    assert [r[:2] for r in data.removed_editors] == [("20", "Tor Veit")]
