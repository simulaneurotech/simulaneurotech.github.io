"""Find the investigators' co-authors outside the centre.

Usage: python external_collaborators.py [publications_dir] [contributors_dir]

Uses the merged publication and author data from publication_data.py and
writes, to contributors_dir:

- external_coauthors.csv: per investigator, each outside co-author and the
  number of shared publications
- bridges.csv: outside co-authors shared by two or more investigators
- indirect_links.csv: pairs of investigators linked through an outside
  co-author, who has published with each of them on separate papers (a paper
  with A that B is not on, and one with B that A is not on). Co-authors who
  only appear on the pair's joint papers do not count.
"""

import csv
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from publication_data import id_order, load


def external_counts(data):
    """Return {investigator: Counter(outside person key: shared publications)}."""
    shared = defaultdict(Counter)
    for name, rids in data.papers_of.items():
        for rid in sorted(rids, key=id_order):
            for k in sorted(data.papers[rid]["authors"]):
                if not k.startswith("inv:"):
                    shared[name][k] += 1
    return shared


def indirect_links(data):
    """Return {(a, b): [outside person keys]} for pairs of investigators (in
    data.investigators order) linked through separate papers with an outside
    co-author, strongest link first."""
    papers_with = defaultdict(lambda: defaultdict(set))
    for name, rids in data.papers_of.items():
        for rid in sorted(rids, key=id_order):
            for k in sorted(data.papers[rid]["authors"]):
                if not k.startswith("inv:"):
                    papers_with[k][name].add(rid)
    order = list(data.investigators)
    links = defaultdict(list)
    for k, by_investigator in papers_with.items():
        names = sorted(by_investigator, key=order.index)
        for a, b in combinations(names, 2):
            pa, pb = by_investigator[a], by_investigator[b]
            if pa - pb and pb - pa:
                links[(a, b)].append(k)

    def strength(pair, k):
        a, b = pair
        na, nb = len(papers_with[k][a]), len(papers_with[k][b])
        return (-min(na, nb), -(na + nb), data.display(k))

    return {
        pair: sorted(keys, key=lambda k: strength(pair, k))
        for pair, keys in links.items()
    }


def bridges(shared):
    """Return {outside person key: {investigator: count}} for people shared by
    two or more investigators, most investigators first."""
    by_person = defaultdict(dict)
    for name, counts in shared.items():
        for k, n in counts.items():
            by_person[k][name] = n
    found = {k: v for k, v in by_person.items() if len(v) > 1}
    return dict(
        sorted(found.items(), key=lambda kv: (-len(kv[1]), -sum(kv[1].values()), kv[0]))
    )


def main():
    publications_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "publications")
    contributors_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "contributors")
    data = load(publications_dir, contributors_dir)
    shared = external_counts(data)

    with (contributors_dir / "external_coauthors.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(
            ["investigator", "coauthor", "cristin_person_id", "institution", "shared"]
        )
        for name in data.investigators:
            for k, n in shared[name].most_common():
                pid = k.removeprefix("id:") if k.startswith("id:") else ""
                writer.writerow([name, data.display(k), pid, data.institution(k), n])

    found = bridges(shared)
    with (contributors_dir / "bridges.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(
            ["coauthor", "institution", "n_investigators", "total", "investigators"]
        )
        for k, v in found.items():
            writer.writerow(
                [
                    data.display(k),
                    data.institution(k),
                    len(v),
                    sum(v.values()),
                    "; ".join(f"{i} ({n})" for i, n in sorted(v.items())),
                ]
            )

    links = indirect_links(data)
    with (contributors_dir / "indirect_links.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["person_a", "person_b", "shared_outside", "coauthors"])
        for (a, b), keys in sorted(links.items(), key=lambda kv: -len(kv[1])):
            writer.writerow(
                [
                    a,
                    b,
                    len(keys),
                    "; ".join(
                        f"{data.display(k)} ({shared[a][k]}/{shared[b][k]})"
                        for k in keys
                    ),
                ]
            )

    for name in data.investigators:
        print(f"{name}: {len(shared[name])} outside co-authors")
    print(f"{len(links)} pairs linked through outside co-authors")
    print(f"{len(found)} outside co-authors shared by 2+ investigators")


if __name__ == "__main__":
    main()
