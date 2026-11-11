# Publications and co-authorships

The investigators' publications, fetched from [NVA](https://nva.sikt.no/)
(Nasjonalt vitenarkiv), and the page
**[Who publishes with whom](https://simulaneurotech.github.io/coauthorship.html)**:
how the investigators publish together, and the outside co-authors who link
them. NVA identifies people and older publications by their former Cristin
IDs.

## Usage

Python 3, standard library only. Run from this folder:

```sh
python3 fetch_nva.py               # publications and author lists from NVA
python3 publication_data.py        # review files: duplicates, names, book editors
python3 coauthorship.py            # shared publications per pair of investigators
python3 external_collaborators.py  # outside co-authors who link investigators
python3 collaboration_map.py       # writes ../site/coauthorship.html
python3 -m pytest                  # tests
```

`../refresh.sh` runs these. The node positions in
`collaboration_map_template.html` are set by hand for the current
investigators.

## Files

| File | Contents |
|---|---|
| `investigators.csv` | The investigators and leadership, edited by hand; `extra_person_ids` lists second profiles |
| `publications/<Name>.csv` | Each investigator's publications |
| `publications/person_ids.csv` | The NVA person ID found for each name |
| `publications/duplicate_publications.csv` | Publications registered more than once, and the record kept |
| `publications/coauthorship_*.csv` | Shared publications between investigators |
| `fetched.csv` | When the publications were fetched (shown on the pages) |

## How it works

- **People.** Each investigator is found in NVA by name and Simula
  affiliation. Authors are identified by person ID; those without one are
  matched by surname and a compatible first name ("K." matches "Kari").
- **Publications.** Journal articles, reviews, chapters and conference
  papers, books and working papers are kept (`CATEGORIES` in
  `fetch_nva.py`); talks, posters, theses, reports and similar are not.
- **Duplicates.** Records with the same DOI or nearly the same title and
  year count as one paper, and the published version is kept.
- **Book editors.** Editors listed among a chapter's authors are removed, so
  chapters someone only edited do not count.
- **Indirect links.** An outside co-author links two investigators when they
  have published with each of them on separate papers.

## Limitations

NVA only holds work registered through Norwegian institutions, so lists may
be incomplete, particularly for work from before joining Simula. Some
co-authors have two NVA profiles and count as two people.
