# Centre overview

An overview page for the Centre for Digital Neurotechnology: the
investigators, key figures on publications and co-authors, and the projects.

**Page:** <https://simulaneurotech.github.io/>,
published from [`../site/index.html`](../site/index.html). You can also open
that file locally in a browser.

The page is built from the data in [`../nva/`](../nva/) and
[`../partners/`](../partners/), so update those first.

## Files

| File | Contents |
|---|---|
| `build_centre_page.py` | Builds `../site/index.html` |
| `centre_page_template.html` | Page template: layout, key figures, investigators and project timeline |
| `investigator_pages.csv` | **Checked by hand**: each investigator's page on simula.no, linked from their name |

## Usage

Requires Python 3 (standard library only). Run from this folder:

```sh
cd centre
python3 build_centre_page.py   # writes ../site/index.html
```

## Key figures

Given since 2024, 2021 and 2016 (`SINCE` in `build_centre_page.py`), each up
to today:

- **Publications:** the investigators' journal articles, conference papers,
  book chapters and books in NVA, with duplicates merged and each
  publication counted once.
- **Co-authors:** everyone other than the investigators on these
  publications, from OpenAlex (publications with a DOI only), each counted
  once. Colleagues whose main institution (below) is in the Simula Group are
  left out; co-authors with no known institution are counted.
- **Institutions:** each co-author's main institution, the one they are
  listed at most often on these publications, counted once. Simula Group
  institutions are not counted, and the merges and exclusions in
  `../partners/` (`institution_merges.csv`, `affiliation_exclusions.csv`)
  apply.
- **Countries:** the countries of these institutions.

On the page, each number can be selected to show the list behind it: the
publications, the co-authors (with their main institution and joint
publications), the institutions (with their co-authors and publications) or
the countries (with their institutions). `build_centre_page.py` works out the
lists together with the numbers, so they always agree.

All the investigators' publications are used, not only those marked
relevant in `../partners/publication_relevance.csv`. The partners page
counts institutions and countries the same way, with the same function
(`main_institutions` in `../partners/build_partners_page.py`), and a test
checks that the two pages agree.

The project timeline is hidden for now (`SHOW_PROJECTS = False` in
`build_centre_page.py`); set it to `True` to show it again. Projects are the
same as on the partners page: `../partners/centre_projects.csv`,
projects that started in 2016 or later, with Research Council funding from
`../partners/prosjektbanken_projects.csv`.

Under "More about the centre", the page links to the pages listed in
`LINKED_PAGES` in `build_centre_page.py`: currently the partners page
(`partners.html`) and the projects page (`projects.html`), but not yet the
co-authorship page (`coauthorship.html`).

## Tests

```sh
cd centre
python3 -m pytest
```

The tests use small made-up inputs and need no network access. One test also
checks that the template and `../site/index.html` load nothing from other
sites, only files in `../site/`. All of them run
daily on GitHub Actions with the tests in `../nva/` and `../partners/`.
