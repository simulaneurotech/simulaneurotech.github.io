"""Load the publication and author lists, merging duplicates.

Usage: python publication_data.py [publications_dir] [contributors_dir]

Used by coauthorship.py, collaboration_map.py and external_collaborators.py.
Run on its own, it writes two files for reviewing the merges:
publications_dir/duplicate_publications.csv, contributors_dir/merged_names.csv
and contributors_dir/removed_editors.csv.

Duplicate publications: records are the same paper when they share a DOI and
have similar titles (some records carry another paper's DOI), or when their
titles match and either their years are at most one apart or one of them is a
preprint (arXiv, bioRxiv, medRxiv), or when they have the same journal (or
none) and nearly the same title (at least 85% alike in the same year, 95% one
year apart, with the same numbers, so "Part I" and "Part II" stay apart). The
published version is kept.

People: authors are identified by Cristin person ID. Two IDs are the same
person when they appear with exactly the same full name. Authors without an
ID are matched by surname and a compatible first name ("A." matches "Andreas",
"Hans" matches "Hans Petter", "Aditya" does not match "Amrendra"), and only
when exactly one known person fits. Investigators are recognised by all of
their Cristin IDs (including extra_cristin_ids) and by name.

Book editors: some chapter records list the book's editors after the
authors. When a chapter's contributors include all of its book's editors, the
editors at the end of the list are removed (unless that would remove
everyone); each editor is removed at most once, since an editor can also be an
author of the chapter. A chapter record without a link to its book is ignored when a
duplicate of it has one. Investigators' publications are taken from these
cleaned author lists, so an editor does not get the chapters they only edited.
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from fetch_nva import ascii_fold, file_stem

PAPER_FIELDS = ["year", "title", "category", "journal", "doi", "nva_id", "venue"]
PREPRINT_SERVERS = ("arxiv", "biorxiv", "medrxiv")
PREPRINT_DOI_PREFIXES = ("10.48550/", "10.1101/")


@dataclass
class Data:
    # name -> {"aff": affiliation, "ids": Cristin person IDs}
    investigators: dict
    # canonical result ID -> paper fields plus "authors": set of person keys
    papers: dict
    # investigator name -> set of canonical result IDs
    papers_of: dict
    # person key -> Counter of name variants
    names: dict
    # person key -> Counter of institution names
    institutions: dict
    # canonical result ID -> all result IDs merged into it (only when > 1)
    duplicates: dict
    # (result ID, editor name, chapter title) of editors removed from chapters
    removed_editors: list

    def display(self, key):
        return self.names[key].most_common(1)[0][0]

    def institution(self, key):
        counts = self.institutions.get(key)
        return counts.most_common(1)[0][0] if counts else ""


def id_order(rid):
    """Sort key for result IDs: Cristin numbers first, then NVA identifiers."""
    return (0, int(rid), "") if rid.isdigit() else (1, 0, rid)


def investigator_key(name):
    return f"inv:{name}"


# Publications


def normalize_title(title):
    return re.sub(r"[^a-z0-9]", "", ascii_fold(title).lower())


def similar_titles(a, b):
    """True if two titles are at least 80% alike or one starts with the other."""
    a, b = normalize_title(a), normalize_title(b)
    return (
        a.startswith(b) or b.startswith(a) or SequenceMatcher(None, a, b).ratio() >= 0.8
    )


def part_numbers(title):
    """Numbers and roman numerals in a title, such as part or volume numbers."""
    return sorted(
        re.findall(r"\b(?:\d+|i{1,3}|iv|vi{0,3}|ix|x)\b", ascii_fold(title).lower())
    )


def near_duplicates(a, b):
    """True if two records without a shared DOI are likely the same paper."""
    years_apart = abs(year(a) - year(b))
    if years_apart > 1 or normalize_title(a["journal"]) != normalize_title(
        b["journal"]
    ):
        return False
    if part_numbers(a["title"]) != part_numbers(b["title"]):
        return False
    matcher = SequenceMatcher(
        None, normalize_title(a["title"]), normalize_title(b["title"])
    )
    threshold = 0.85 if years_apart == 0 else 0.95
    return matcher.quick_ratio() >= threshold and matcher.ratio() >= threshold


def doi_key(doi):
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip().lower())


def is_preprint(record):
    journal = record["journal"].lower()
    return any(s in journal for s in PREPRINT_SERVERS) or doi_key(
        record["doi"]
    ).startswith(PREPRINT_DOI_PREFIXES)


def year(record):
    return int(record["year"]) if record["year"].isdigit() else 0


def merge_duplicates(records):
    """Return {result ID: canonical result ID} for records {result ID: row}."""
    parent = {rid: rid for rid in records}

    def find(rid):
        while parent[rid] != rid:
            parent[rid] = parent[parent[rid]]
            rid = parent[rid]
        return rid

    def union(a, b):
        parent[find(a)] = find(b)

    by_doi, by_title = defaultdict(list), defaultdict(list)
    for rid, record in records.items():
        if record["doi"]:
            by_doi[doi_key(record["doi"])].append(rid)
        if normalize_title(record["title"]):
            by_title[normalize_title(record["title"])].append(rid)
    for rids in by_doi.values():
        for i, a in enumerate(rids):
            for b in rids[i + 1 :]:
                if similar_titles(records[a]["title"], records[b]["title"]):
                    union(a, b)
    for rids in by_title.values():
        for i, a in enumerate(rids):
            for b in rids[i + 1 :]:
                ra, rb = records[a], records[b]
                if abs(year(ra) - year(rb)) <= 1 or is_preprint(ra) or is_preprint(rb):
                    union(a, b)
    by_year = defaultdict(list)
    for rid, record in records.items():
        by_year[year(record)].append(rid)
    for y, rids in by_year.items():
        nearby = rids + by_year.get(y + 1, [])
        for i, a in enumerate(rids):
            for b in nearby[i + 1 :]:
                if find(a) != find(b) and near_duplicates(records[a], records[b]):
                    union(a, b)

    groups = defaultdict(list)
    for rid in records:
        groups[find(rid)].append(rid)

    def preference(rid):
        r = records[rid]
        return (is_preprint(r), not r["doi"], not r["journal"], -year(r), id_order(rid))

    canonical = {}
    for rids in groups.values():
        best = min(rids, key=preference)
        for rid in rids:
            canonical[rid] = best
    return canonical


# People


def surname_key(surname):
    return re.sub(r"[^a-z]", "", ascii_fold(surname).lower())


def first_name_tokens(first_name):
    """Split a first name into lowercase tokens; "AE" and "J.G." become initials."""
    tokens = []
    for token in re.split(r"[\s.\-]+", first_name.strip()):
        if not token:
            continue
        if token.isupper() and len(token) <= 3:
            tokens.extend(token.lower())
        else:
            tokens.append(ascii_fold(token).lower())
    return tokens


def compatible(first_a, first_b):
    """True if two first names can belong to the same person."""
    a, b = first_name_tokens(first_a), first_name_tokens(first_b)
    if not a or not b:
        return False
    if len(a[0]) == 1 or len(b[0]) == 1:
        return a[0][0] == b[0][0]
    return a[0] == b[0]


def full_name_key(first_name, surname):
    return (" ".join(first_name_tokens(first_name)), surname_key(surname))


def resolve_people(rows, investigators):
    """Return {Cristin person ID: key} and {(first, surname): key} for
    contributor rows without an ID."""
    # Group IDs that appear with exactly the same full name (first name not
    # just an initial), and IDs belonging to the same investigator
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for name, info in investigators.items():
        for pid in info["ids"]:
            union(pid, investigator_key(name))
    ids_by_full_name = defaultdict(set)
    for row in rows:
        if row["cristin_person_id"]:
            find(row["cristin_person_id"])
            first, surname = full_name_key(row["first_name"], row["surname"])
            if len(first.split(" ")[0]) > 1:
                ids_by_full_name[(first, surname)].add(row["cristin_person_id"])
    for ids in ids_by_full_name.values():
        ids = sorted(ids)
        for pid in ids[1:]:
            union(ids[0], pid)

    groups = defaultdict(list)
    for x in list(parent):
        if not x.startswith("inv:"):
            groups[find(x)].append(x)
    id_key = {}
    for root, pids in groups.items():
        k = root if root.startswith("inv:") else f"id:{min(pids, key=int)}"
        for pid in pids:
            id_key[pid] = k

    # Known people by surname, with the first names seen for each
    known = defaultdict(lambda: defaultdict(set))
    for row in rows:
        if row["cristin_person_id"]:
            k = id_key[row["cristin_person_id"]]
            known[surname_key(row["surname"])][k].add(row["first_name"])
    for name in investigators:
        *first, surname = name.split(" ")
        known[surname_key(surname)][investigator_key(name)].add(" ".join(first))

    # Match authors without an ID, full first names before initials
    name_key = {}
    no_id = {
        (row["first_name"], row["surname"])
        for row in rows
        if not row["cristin_person_id"]
    }

    def is_initial(name):
        tokens = first_name_tokens(name[0])
        return not tokens or len(tokens[0]) == 1

    for first, surname in sorted(no_id, key=lambda n: (is_initial(n), n)):
        people = known[surname_key(surname)]
        matches = [
            k
            for k, firsts in people.items()
            if all(compatible(first, f) for f in firsts)
        ]
        if len(matches) == 1:
            k = matches[0]
        else:
            k = f"name:{' '.join(first_name_tokens(first))}|{surname_key(surname)}"
            if not matches:
                people[k].add(first)
        name_key[(first, surname)] = k
    return id_key, name_key


# Loading


def read_csv(path, optional=False):
    if optional and not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def same_person(row, editor):
    """Same Cristin ID, or (for missing or second profiles) a compatible name."""
    if (
        row["cristin_person_id"]
        and row["cristin_person_id"] == editor["cristin_person_id"]
    ):
        return True
    return surname_key(row["surname"]) == surname_key(editor["surname"]) and compatible(
        row["first_name"], editor["first_name"]
    )


def strip_editors(rows, editors):
    """Remove book editors appended to the end of a chapter's author list.

    rows are the chapter's contributors in order. Only applies when every
    editor is among them. Each editor is removed at most once, and never all
    contributors. Returns (kept rows, removed rows).
    """
    if not editors or not all(any(same_person(r, e) for r in rows) for e in editors):
        return rows, []
    remaining = list(editors)
    end = len(rows)
    while end > 0:
        editor = next((e for e in remaining if same_person(rows[end - 1], e)), None)
        if editor is None:
            break
        remaining.remove(editor)
        end -= 1
    if not end:
        return rows, []
    return rows[:end], rows[end:]


def load(
    publications_dir=Path("publications"),
    contributors_dir=Path("contributors"),
    investigators_csv=Path("investigators.csv"),
):
    affiliation = {
        row["name"]: row["affiliation"]
        for row in read_csv(investigators_csv)
        if "Investigator" in row["role"]
    }
    investigators, records = {}, {}
    for row in read_csv(publications_dir / "cristin_ids.csv"):
        if row["name"] not in affiliation or not row["cristin_person_id"]:
            continue
        extra = [i for i in row.get("extra_cristin_ids", "").split(";") if i]
        investigators[row["name"]] = {
            "aff": affiliation[row["name"]],
            "ids": [row["cristin_person_id"], *extra],
        }
        rows = read_csv(publications_dir / f"{file_stem(row['name'])}.csv")
        for r in rows:
            records[r["cristin_result_id"]] = {k: r.get(k, "") for k in PAPER_FIELDS}

    canonical = merge_duplicates(records)
    papers = {
        rid: {**records[rid], "authors": set()} for rid in set(canonical.values())
    }
    papers_of = {name: set() for name in investigators}

    part_of = {
        row["cristin_result_id"]: row["part_of"]
        for row in read_csv(contributors_dir / "chapters.csv", optional=True)
    }
    editors = defaultdict(list)
    for row in read_csv(contributors_dir / "editors.csv", optional=True):
        if row["surname"]:
            editors[row["part_of"]].append(row)
    linked = {
        canonical[rid] for rid, url in part_of.items() if url and rid in canonical
    }

    by_result = defaultdict(list)
    for row in read_csv(contributors_dir / "contributors.csv"):
        if row["cristin_result_id"] in canonical:
            by_result[row["cristin_result_id"]].append(row)
    contributors, removed_editors = [], []
    for rid, rows in by_result.items():
        if rid in part_of and not part_of[rid] and canonical[rid] in linked:
            continue
        rows.sort(key=lambda r: int(r["order"] or 0))
        kept, removed = strip_editors(rows, editors.get(part_of.get(rid), []))
        contributors.extend(kept)
        removed_editors.extend(
            (rid, f"{r['first_name']} {r['surname']}".strip(), records[rid]["title"])
            for r in removed
        )
    institution_name = {
        row["cristin_institution_id"]: row["name"]
        for row in read_csv(contributors_dir / "institutions.csv")
    }
    id_key, name_key = resolve_people(contributors, investigators)

    names, institutions = defaultdict(Counter), defaultdict(Counter)
    for name in investigators:
        names[investigator_key(name)][name] += 1
    for row in contributors:
        pid = row["cristin_person_id"]
        k = id_key[pid] if pid else name_key[(row["first_name"], row["surname"])]
        rid = canonical[row["cristin_result_id"]]
        papers[rid]["authors"].add(k)
        if k.startswith("inv:"):
            papers_of[k.removeprefix("inv:")].add(rid)
        else:
            names[k][f"{row['first_name']} {row['surname']}".strip()] += 1
        for i in row["institutions"].split(";"):
            if i in institution_name:
                institutions[k][institution_name[i]] += 1

    duplicates = defaultdict(list)
    for rid, best in canonical.items():
        duplicates[best].append(rid)
    duplicates = {
        k: sorted(v, key=id_order) for k, v in duplicates.items() if len(v) > 1
    }

    return Data(
        investigators,
        papers,
        papers_of,
        names,
        institutions,
        duplicates,
        removed_editors,
    )


def main():
    publications_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "publications")
    contributors_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "contributors")
    data = load(publications_dir, contributors_dir)

    with (publications_dir / "duplicate_publications.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["kept_result_id", "merged_result_ids", "year", "title"])
        for best, rids in sorted(
            data.duplicates.items(), key=lambda kv: id_order(kv[0])
        ):
            paper = data.papers[best]
            merged = ";".join(r for r in rids if r != best)
            writer.writerow([best, merged, paper["year"], paper["title"]])

    with (contributors_dir / "merged_names.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["person", "variants"])
        for k in sorted(data.names, key=data.display):
            variants = data.names[k]
            if len(variants) > 1:
                writer.writerow(
                    [
                        data.display(k),
                        "; ".join(f"{v} ({n})" for v, n in variants.items()),
                    ]
                )

    with (contributors_dir / "removed_editors.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["cristin_result_id", "editor", "chapter"])
        for row in sorted(data.removed_editors, key=lambda r: id_order(r[0])):
            writer.writerow(row)

    merged = sum(len(v) - 1 for v in data.duplicates.values())
    print(f"{len(data.papers)} publications after merging {merged} duplicates")


if __name__ == "__main__":
    main()
