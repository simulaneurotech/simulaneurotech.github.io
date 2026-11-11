"""Where the co-author data is kept, and who is left out.

Usage: python coauthor_data.py   (removes opted-out people from the saved data)

The data about individual co-authors is kept outside this repository, in the
folder CENTRE_DATA points to (by default ../centre-data next to it), with
the layout nva/contributors/ and partners/. People listed in its
opt_outs.csv are left out when data is fetched and when the pages are built.
"""

import csv
import io
import os
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("CENTRE_DATA") or REPO.parent / "centre-data")
CONTRIBUTORS = ROOT / "nva" / "contributors"
PARTNERS = ROOT / "partners"
OPT_OUTS = ROOT / "opt_outs.csv"
OPT_OUT_FIELDS = [
    "names",
    "cristin_person_id",
    "openalex_author_id",
    "orcid",
    "requested",
    "note",
]
# Columns that hold a person's name in the data files
NAME_COLUMNS = ("author", "name", "coauthor", "person", "editor")


def available():
    """True if the co-author data is where the scripts look for it."""
    return CONTRIBUTORS.is_dir() and PARTNERS.is_dir()


def name_key(name):
    """A name compared without accents, case, punctuation or spacing."""
    text = name.translate(str.maketrans({"æ": "ae", "ø": "o", "Æ": "Ae", "Ø": "O"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def orcid_key(orcid):
    return orcid.strip().rstrip("/").rsplit("/", 1)[-1].upper()


class OptOuts:
    """The people in opt_outs.csv, matched by any of their IDs or names."""

    def __init__(self, rows=()):
        rows = list(rows)

        def values(column):
            return [
                v.strip()
                for r in rows
                for v in (r.get(column) or "").split(";")
                if v.strip()
            ]

        self.cristin = set(values("cristin_person_id"))
        self.openalex = set(values("openalex_author_id"))
        self.orcid = {orcid_key(v) for v in values("orcid")}
        self.names = {name_key(v) for v in values("names")} - {""}

    def __bool__(self):
        return bool(self.cristin or self.openalex or self.orcid or self.names)

    def match(self, row):
        """True if a data row (a dict) is about someone who opted out."""
        if row.get("cristin_person_id") and row["cristin_person_id"] in self.cristin:
            return True
        if row.get("openalex_author_id") and row["openalex_author_id"] in self.openalex:
            return True
        if row.get("orcid") and orcid_key(row["orcid"]) in self.orcid:
            return True
        names = [row.get(c) or "" for c in NAME_COLUMNS]
        if "surname" in row:
            names.append(f"{row.get('first_name') or ''} {row['surname']}")
        return any(name_key(n) in self.names for n in names if name_key(n))

    def drop(self, rows):
        return [r for r in rows if not self.match(r)]


def read_opt_outs(path=None):
    path = OPT_OUTS if path is None else Path(path)
    if not path.exists():
        return OptOuts()
    with path.open(encoding="utf-8") as f:
        return OptOuts(csv.DictReader(f))


def drop_opted_out(rows, opt_outs=None):
    """rows without those about people in opt_outs.csv (or opt_outs)."""
    opt_outs = read_opt_outs() if opt_outs is None else opt_outs
    return opt_outs.drop(rows) if opt_outs else list(rows)


def purge(root=None, opt_outs=None):
    """Remove the rows about opted-out people from every data file under root,
    keeping each file's columns, quoting and line endings. Returns
    {file: rows removed} for the files that changed."""
    root = ROOT if root is None else Path(root)
    opt_outs = read_opt_outs(root / "opt_outs.csv") if opt_outs is None else opt_outs
    removed = {}
    if not opt_outs:
        return removed
    for path in sorted(root.rglob("*.csv")):
        if path.name == "opt_outs.csv" or ".git" in path.parts:
            continue
        data = path.read_bytes().decode("utf-8")
        newline = "\r\n" if "\r\n" in data else "\n"
        rows = list(csv.DictReader(io.StringIO(data, newline="")))
        kept = opt_outs.drop(rows)
        if len(kept) == len(rows):
            continue
        fields = next(csv.reader(io.StringIO(data, newline="")))
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=fields, lineterminator=newline)
        writer.writeheader()
        writer.writerows(kept)
        path.write_bytes(out.getvalue().encode("utf-8"))
        removed[path.relative_to(root)] = len(rows) - len(kept)
    return removed


def main():
    if not available():
        sys.exit(f"No co-author data at {ROOT}: set CENTRE_DATA to where it is")
    removed = purge()
    for path, n in removed.items():
        print(f"{path}: {n} rows removed")
    if not removed:
        print("Nothing to remove")
    else:
        print("Now rebuild the pages: ../refresh.sh --no-fetch")


if __name__ == "__main__":
    main()
