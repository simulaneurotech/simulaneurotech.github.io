# Centre overview

The **[overview page](https://simulaneurotech.github.io/)**: the
investigators, key figures on publications and co-authors, and links to the
centre's other pages. It is built from the data in [`../nva/`](../nva/) and
[`../partners/`](../partners/), so update those first.

## Usage

Python 3, standard library only. Run from this folder:

```sh
python3 build_centre_page.py   # writes ../site/index.html
python3 -m pytest              # tests
```

| File | Contents |
|---|---|
| `build_centre_page.py` | Builds the page; `SINCE` sets the periods and `LINKED_PAGES` the links under "More about the centre" |
| `centre_page_template.html` | Page template |
| `investigator_pages.csv` | Each investigator's page on simula.no, edited by hand |

## Key figures

For the periods since 2024, 2021 and 2016:

- **Publications:** the investigators' publications in NVA, each counted
  once.
- **Co-authors:** everyone else on these publications, from OpenAlex
  (publications with a DOI), each counted once; Simula Group colleagues are
  left out.
- **Institutions:** each co-author's main institution, the one they are
  listed at most often on these publications.
- **Countries:** the countries of these institutions.

Each number can be selected on the page to show the list behind it. "Who we
publish with" counts the same way, and tests check that the two pages agree.
