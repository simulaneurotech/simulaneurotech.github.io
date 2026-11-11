# Publications and co-authorships

Publication lists for the investigators of the
[Centre for Digital Neurotechnology](https://www.simula.no/research/research-centres/centre-digital-neurotechnology),
fetched from [NVA](https://nva.sikt.no/) (Nasjonalt vitenarkiv, which
replaced Cristin), with shared publications between investigators and their
co-authors outside the centre. The data keeps its Cristin person and result
IDs, which NVA carries over.

**Page:** "Who publishes with whom",
<https://simulaneurotech.github.io/coauthorship.html>, built into
[`../site/coauthorship.html`](../site/coauthorship.html), shows the
co-authorship network with the outside co-authors who link investigators,
direct and indirect links between all pairs, and co-authored against total
publications over time. It is published but not yet linked from the
overview page. You can also open the file locally in a browser.

## Files

| File | Contents |
|---|---|
| `investigators.csv` | Centre investigators and leadership, from the [announcement](https://www.simula.no/about/news/simula-establishes-centre-digital-neurotechnology); `extra_cristin_ids` lists second Cristin profiles |
| `fetch_nva.py` | Fetches each person's results, author lists, institutions and book editors from the NVA API |
| `fetch_log.py`, `fetched.csv` | When each source was last fetched: the fetch scripts here and in `../partners/` record the date with `fetch_log.py`, and the pages show it |
| `publication_data.py` | Merges duplicate publications and name variants; used by the scripts below |
| `coauthorship.py` | Counts shared publications between each pair of investigators |
| `external_collaborators.py` | Finds co-authors outside the centre, and those shared by several investigators |
| `collaboration_map.py` | Builds `../site/coauthorship.html` from the publication lists |
| `collaboration_map_template.html` | Page template: layout and node positions |
| `publications/<Name>.csv` | One file per person: year, title, category, journal, DOI, result ID (Cristin result ID, or NVA identifier for records without one), NVA identifier, venue (journal; book or proceedings for chapters and conference papers; publisher for books) |
| `publications/cristin_ids.csv` | The Cristin person IDs used for each name, and number of results |
| `publications/duplicate_publications.csv` | Publications registered more than once, and which record was kept |
| `publications/coauthorship_edges.csv` | Pairs with at least one shared publication |
| `publications/coauthorship_matrix.csv` | Shared publications for all pairs; the diagonal is each person's total |

## Usage

Requires Python 3 (standard library only). Run from this folder:

```sh
cd nva
python3 fetch_nva.py               # writes publications/ and the author lists
python3 publication_data.py        # writes the duplicate, name and editor review files
python3 coauthorship.py            # writes publications/coauthorship_*.csv
python3 external_collaborators.py  # finds the outside co-authors who link investigators
python3 collaboration_map.py       # writes ../site/coauthorship.html
```

The node positions in `collaboration_map_template.html` are written by hand
for the current investigators. Update them if the investigators change.

Each script takes optional paths; see the docstring at the top of each file.

## How it works

- **Source.** NVA replaced Cristin. It holds the same records, with the
  same person IDs and the old Cristin result IDs. Fetching from NVA gives the
  same results as the earlier Cristin data, except that people listed as
  editors of a whole book (role "Editor" in NVA) are not counted as its
  authors.
- **Matching people.** Each name is searched in NVA, and the person with a
  Simula, SimulaMet or Simula UiB affiliation is chosen. Check
  `publications/cristin_ids.csv` if a result looks wrong.
- **What counts as a publication.** Only these NVA types are kept, under the
  category names used in Cristin: academic articles, literature reviews,
  academic chapters (including conference papers), chapters, academic
  monographs, textbooks, non-fiction books and working papers (Cristin's
  compendia). Talks, posters, edited volumes, theses, reports, abstracts and
  popular science pieces are dropped. The list is `CATEGORIES` in
  `fetch_nva.py`.
- **Duplicate publications.** Records are the same paper when they share a DOI
  and have similar titles, or when their titles match and either their years
  are at most one apart or one is a preprint (arXiv, bioRxiv, medRxiv), or
  when they have the same journal (or none) and nearly the same title: at least
  85% alike in the same year or 95% one year apart, with the same numbers, so
  "Part I" and "Part II" stay apart. The published version is kept, and
  preprints and published versions count as one paper. Check
  `publications/duplicate_publications.csv`.
- **People.** Authors are identified by Cristin person ID. Authors without an
  ID, usually from outside Norway, are matched by surname and a compatible
  first name ("A." matches "Andreas", "Aditya" does not match "Amrendra"),
  only when exactly one known person fits. Investigators are recognised by all
  their Cristin IDs and by name, so papers where they are listed without an ID
  still count.
- **Book editors.** Some records list a book's editors after the
  authors of every chapter. When a chapter lists all of its book's editors,
  the editors at the end of its author list are removed, each at most once and
  never all contributors, so editors who wrote the chapter stay. A chapter
  record without a link to its book is ignored when a duplicate of it has one.
  Each investigator's publications come from these cleaned author lists, so
  chapters someone only edited do not count.
- **Co-authorship.** Two investigators share a publication when both are among
  its authors.
- **Indirect links.** An outside co-author links two investigators when they
  have published with each of them on separate papers: one with A that B is
  not on, and one with B that A is not on. Co-authors who only appear on the
  pair's joint papers, such as the 55 authors of a multi-group challenge
  paper, do not count.

## Limitations

NVA, like Cristin, only holds work registered through Norwegian institutions,
so lists may be incomplete, particularly for work done before joining Simula. Shared
publication counts inherit the same gaps.

Some outside co-authors have two person profiles under slightly different
names (for example "Morten Dæhlen" and "M. Dæhlen") and are counted as two
people. Authors outside Norway usually have no institution in NVA. Large
multi-group papers add many outside co-authors at once.

## Tests

```sh
cd nva
python3 -m pytest
```

The tests use fake NVA data and need no network access. They run daily on GitHub Actions
(`../.github/workflows/tests.yml`), and can be started by hand from the
Actions tab.
