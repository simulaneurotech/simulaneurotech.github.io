import csv

import pytest

from fetch_nva import FIELDS, file_stem


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    """Return a function that writes a fake dataset to tmp_path and changes
    into it.

    investigators: list of (name, affiliation, role, person ID, extra IDs)
    papers: list of dicts with result ID "id", "year", "title", optional
    "journal" and "doi", and "authors" as (first name, surname, person ID).
    Each investigator's own list holds the papers where one of their IDs is
    an author. chapters maps result ID to the URL of its book ("" for none);
    editors is a list of (book URL, first name, surname, person ID).
    """

    def write(investigators, papers, chapters=None, editors=None):
        write_csv(
            tmp_path / "investigators.csv",
            ["name", "affiliation", "role", "extra_person_ids"],
            [
                {"name": n, "affiliation": a, "role": r, "extra_person_ids": e}
                for n, a, r, _, e in investigators
            ],
        )
        publications = tmp_path / "publications"
        contributors = tmp_path / "contributors"
        publications.mkdir()
        contributors.mkdir()
        write_csv(
            publications / "person_ids.csv",
            ["name", "person_id", "extra_person_ids", "n_results"],
            [
                {
                    "name": n,
                    "person_id": pid,
                    "extra_person_ids": e,
                    "n_results": 0,
                }
                for n, _, _, pid, e in investigators
            ],
        )
        for name, _, _, pid, extra in investigators:
            ids = {pid, *extra.split(";")} - {""}
            rows = [
                {
                    "year": p["year"],
                    "title": p["title"],
                    "category": "Academic article",
                    "journal": p.get("journal", ""),
                    "doi": p.get("doi", ""),
                    "result_id": p["id"],
                }
                for p in papers
                if any(a[2] in ids for a in p["authors"])
            ]
            write_csv(publications / f"{file_stem(name)}.csv", FIELDS, rows)
        write_csv(
            contributors / "contributors.csv",
            [
                "result_id",
                "order",
                "person_id",
                "first_name",
                "surname",
                "institutions",
            ],
            [
                {
                    "result_id": p["id"],
                    "order": i,
                    "person_id": pid,
                    "first_name": first,
                    "surname": surname,
                    "institutions": "7498" if pid else "0",
                }
                for p in papers
                for i, (first, surname, pid) in enumerate(p["authors"], 1)
            ],
        )
        write_csv(
            contributors / "institutions.csv",
            ["institution_id", "name", "country"],
            [{"institution_id": "7498", "name": "Simula", "country": "NO"}],
        )
        if chapters is not None:
            write_csv(
                contributors / "chapters.csv",
                ["result_id", "part_of"],
                [{"result_id": r, "part_of": u} for r, u in chapters.items()],
            )
        if editors is not None:
            write_csv(
                contributors / "editors.csv",
                ["part_of", "person_id", "first_name", "surname"],
                [
                    {
                        "part_of": u,
                        "person_id": pid,
                        "first_name": first,
                        "surname": surname,
                    }
                    for u, first, surname, pid in editors
                ],
            )
        monkeypatch.chdir(tmp_path)
        return publications, contributors

    return write
