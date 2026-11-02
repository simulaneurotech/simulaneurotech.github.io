"""Count shared publications between investigators.

Usage: python coauthorship.py [publications_dir] [contributors_dir]

Two investigators have co-authored a publication if both are among its
authors, after merging duplicate publications (see publication_data.py).
Writes coauthorship_edges.csv (one row per pair with at least one shared
publication) and coauthorship_matrix.csv (all pairs; diagonal is each
person's total) to publications_dir.
"""

import csv
import sys
from itertools import combinations
from pathlib import Path

from publication_data import load


def main():
    publications_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "publications")
    contributors_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "contributors")
    data = load(publications_dir, contributors_dir)
    papers_of = data.papers_of
    names = list(data.investigators)

    edges = []
    for a, b in combinations(names, 2):
        shared = papers_of[a] & papers_of[b]
        if shared:
            edges.append({"person_a": a, "person_b": b, "shared": len(shared)})
    edges.sort(key=lambda e: e["shared"], reverse=True)

    with (publications_dir / "coauthorship_edges.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=["person_a", "person_b", "shared"])
        writer.writeheader()
        writer.writerows(edges)

    with (publications_dir / "coauthorship_matrix.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow([""] + names)
        for a in names:
            writer.writerow([a] + [len(papers_of[a] & papers_of[b]) for b in names])

    for e in edges:
        print(f"{e['shared']:4d}  {e['person_a']} – {e['person_b']}")


if __name__ == "__main__":
    main()
