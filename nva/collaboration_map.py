"""Build the interactive co-authorship page from the publication lists.

Usage: python collaboration_map.py [publications_dir] [contributors_dir] [output.html]

Writes ../site/coauthorship.html by default, a page on the website next to
the overview page, which loads its fonts from ../site/assets.

Uses the merged publication and author data from publication_data.py and
fills collaboration_map_template.html with the investigators, the pairs with
shared publications, the shared papers themselves, the number of co-authored
and of all publications per year, and the outside co-authors who link
investigators indirectly (see external_collaborators.py).

The node positions and the "What stands out" text in the template are written
by hand for the current investigators and data; update them if those change.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from external_collaborators import external_counts, indirect_links
from publication_data import PAPER_FIELDS, id_order, load

TEMPLATE = Path(__file__).with_name("collaboration_map_template.html")
OUTPUT = Path(__file__).resolve().parent.parent / "site" / "coauthorship.html"


def outside_data(data):
    """Outside co-authors who link investigators indirectly, and the pairs
    they link (see external_collaborators.indirect_links)."""
    links = indirect_links(data)
    shared = external_counts(data)
    keys = list(dict.fromkeys(k for ks in links.values() for k in ks))
    index = {k: i for i, k in enumerate(keys)}
    outside = []
    for k in keys:
        linked = {n for (a, b), ks in links.items() if k in ks for n in (a, b)}
        outside.append(
            {
                "name": data.display(k),
                "inst": data.institution(k),
                "links": {
                    n: shared[n][k] for n in data.investigators if k in shared[n]
                },
                "linked": [n for n in data.investigators if n in linked],
            }
        )
    return {
        "outside": outside,
        "indirect": [
            {"a": a, "b": b, "people": [index[k] for k in ks]}
            for (a, b), ks in links.items()
        ],
    }


def collect(data):
    authors = defaultdict(set)
    for name, rids in data.papers_of.items():
        for rid in sorted(rids, key=id_order):
            authors[rid].add(name)
    shared = {rid: sorted(names) for rid, names in authors.items() if len(names) > 1}
    people = [
        {
            "name": name,
            "aff": info["aff"],
            "total": len(data.papers_of[name]),
            "shared": len(data.papers_of[name] & shared.keys()),
            "cristin": info["ids"][0],
        }
        for name, info in data.investigators.items()
    ]

    def paper(rid):
        return {k: data.papers[rid][k] for k in PAPER_FIELDS}

    pairs = defaultdict(list)
    for rid, names in shared.items():
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                pairs[(a, b)].append(rid)

    by_year = Counter(data.papers[rid]["year"] for rid in shared)
    total_by_year = Counter(data.papers[rid]["year"] for rid in authors)
    return {
        "people": people,
        "papers": {
            rid: {**paper(rid), "authors": shared[rid]}
            for rid in sorted(shared, key=id_order)
        },
        "pairs": [
            {
                "a": a,
                "b": b,
                "ids": sorted(
                    ids,
                    key=lambda rid: (data.papers[rid]["year"], id_order(rid)),
                    reverse=True,
                ),
            }
            for (a, b), ids in sorted(
                pairs.items(), key=lambda kv: (-len(kv[1]), kv[0])
            )
        ],
        "byYear": dict(sorted(by_year.items())),
        "totalByYear": dict(sorted(total_by_year.items())),
        **outside_data(data),
    }


def main():
    publications_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "publications")
    contributors_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "contributors")
    output = Path(sys.argv[3]) if len(sys.argv) > 3 else OUTPUT

    data = collect(load(publications_dir, contributors_dir))
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "__DATA__", json.dumps(data, ensure_ascii=False)
    )
    output.write_text(html, encoding="utf-8")
    print(
        f"{output}: {len(data['papers'])} co-authored publications, "
        f"{len(data['pairs'])} pairs"
    )


if __name__ == "__main__":
    main()
