import csv

import coauthor_data
from coauthor_data import OptOuts, drop_opted_out, purge, read_opt_outs
from publication_data import load


def write_csv(path, fieldnames, rows, newline="\r\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator=newline)
        writer.writeheader()
        writer.writerows(rows)


def opt_out(**fields):
    return {f: fields.get(f, "") for f in coauthor_data.OPT_OUT_FIELDS}


def test_matches_by_any_id():
    opted = OptOuts(
        [
            opt_out(nva_person_id="11"),
            opt_out(openalex_author_id="A22; A23"),
            opt_out(orcid="https://orcid.org/0000-0001-2345-6789"),
        ]
    )
    assert opted.match({"person_id": "11"})
    assert opted.match({"openalex_author_id": "A22"})
    assert opted.match({"openalex_author_id": "A23"})
    assert opted.match({"orcid": "0000-0001-2345-6789"})
    assert not opted.match({"person_id": "12", "openalex_author_id": "A2"})
    # Empty IDs never match
    assert not opted.match({"person_id": "", "openalex_author_id": ""})


def test_matches_name_variants_without_accents_or_punctuation():
    opted = OptOuts([opt_out(names="Åse Øvrebø; A. Ovrebo")])
    assert opted.match({"author": "Ase Ovrebo"})
    assert opted.match({"first_name": "A.", "surname": "Øvrebø"})
    assert opted.match({"coauthor": "ÅSE  ØVREBØ"})
    assert not opted.match({"author": "Åse Øvrebø-Berg"})
    assert not opted.match({"author": "", "openalex_author_id": ""})


def test_drop_without_a_list_keeps_everything(tmp_path, monkeypatch):
    monkeypatch.setattr(coauthor_data, "OPT_OUTS", tmp_path / "missing.csv")
    rows = [{"author": "Ann Berg"}]
    assert not read_opt_outs()
    assert drop_opted_out(rows) == rows


def test_purge_removes_rows_and_keeps_the_files_format(tmp_path):
    write_csv(
        tmp_path / "opt_outs.csv",
        coauthor_data.OPT_OUT_FIELDS,
        [opt_out(names="Ola Nordmann", openalex_author_id="A1")],
    )
    affiliations = tmp_path / "partners" / "openalex_affiliations.csv"
    write_csv(
        affiliations,
        ["author", "openalex_author_id", "affiliation"],
        [
            {"author": "Ola Nordmann", "openalex_author_id": "A1", "affiliation": "x"},
            {"author": "O. Nordmann", "openalex_author_id": "A1", "affiliation": "y"},
            {
                "author": "Kari Nordmann",
                "openalex_author_id": "A2",
                "affiliation": "z, w",
            },
        ],
    )
    contributors = tmp_path / "nva" / "contributors" / "contributors.csv"
    write_csv(
        contributors,
        ["person_id", "first_name", "surname"],
        [{"person_id": "", "first_name": "Ola", "surname": "Nordmann"}],
        newline="\n",
    )
    untouched = tmp_path / "partners" / "person_merges.csv"
    write_csv(
        untouched,
        ["author", "openalex_author_id"],
        [{"author": "Kari", "openalex_author_id": "A2"}],
    )
    before = untouched.read_bytes()

    removed = purge(tmp_path)

    assert {str(p): n for p, n in removed.items()} == {
        "nva/contributors/contributors.csv": 1,
        "partners/openalex_affiliations.csv": 2,
    }
    assert affiliations.read_bytes() == (
        b'author,openalex_author_id,affiliation\r\nKari Nordmann,A2,"z, w"\r\n'
    )
    assert contributors.read_bytes() == b"person_id,first_name,surname\n"
    assert untouched.read_bytes() == before
    # A second run finds nothing more to remove
    assert purge(tmp_path) == {}


def test_load_leaves_out_opted_out_coauthors(dataset, tmp_path, monkeypatch):
    publications, contributors = dataset(
        [("Ann Berg", "SRL", "Investigator", "1", "")],
        [
            {
                "id": "100",
                "year": "2020",
                "title": "A paper",
                "authors": [
                    ("Ann", "Berg", "1"),
                    ("Ola", "Nordmann", "7"),
                    ("Kari", "Hansen", "8"),
                ],
            },
            # The same person under a name variant without an ID
            {
                "id": "101",
                "year": "2021",
                "title": "Another paper",
                "authors": [("Ann", "Berg", "1"), ("O.", "Nordmann", "")],
            },
        ],
    )
    everyone = load(publications, contributors)
    assert len(everyone.papers["100"]["authors"]) == 3
    assert everyone.papers["101"]["authors"] < everyone.papers["100"]["authors"]

    opt_outs = tmp_path / "opt_outs.csv"
    write_csv(opt_outs, coauthor_data.OPT_OUT_FIELDS, [opt_out(nva_person_id="7")])
    monkeypatch.setattr(coauthor_data, "OPT_OUTS", opt_outs)
    data = load(publications, contributors)
    assert len(data.papers["100"]["authors"]) == 2
    assert len(data.papers["101"]["authors"]) == 1
    shown = {data.display(k) for p in data.papers.values() for k in p["authors"]}
    assert not any("Nordmann" in name for name in shown)
    # The publication itself still counts
    assert set(data.papers) == set(everyone.papers)
