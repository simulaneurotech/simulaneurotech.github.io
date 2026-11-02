# Centre for Digital Neurotechnology

Infographics, accompanying tools and code related to the [Centre for Digital Neurotechnology](https://www.simula.no/about/news/simula-establishes-centre-digital-neurotechnology)
at Simula Research Laboratory.

**Overview page:** <https://simulaneurotech.github.io/>
shows the centre investigators and key figures on publications, co-authors,
institutions and countries. It is built from [`site/index.html`](site/index.html).

**Interactive page:** <https://simulaneurotech.github.io/coauthorship.html>
shows how the centre investigators publish together, and how they are linked
through co-authors outside the centre. It is built from [`site/coauthorship.html`](site/coauthorship.html).

**Draft page:** <https://simulaneurotech.github.io/partners.html>
shows the institutions the centre's co-authors are at, nationally and internationally:
where they are, what kinds of institutions they are, and the clinical
collaborators. Institutions and countries are counted as on the overview
page. It is a draft for review, and is built from
[`site/partners.html`](site/partners.html).


## Contents

| Folder | Contents |
|---|---|
| [`centre/`](centre/) | Builds the centre's overview page from the data in `nva/` and `partners/`. See [`centre/README.md`](centre/README.md). |
| [`site/`](site/) | The website published on GitHub Pages: the overview page (`index.html`), the co-authorship page (`coauthorship.html`) and the draft partners page (`partners.html`), all generated, and the fonts and scripts they use (`assets/`). |
| [`nva/`](nva/) | Investigators' publication lists from NVA (formerly Cristin), co-authorship analysis and the interactive page. See [`nva/README.md`](nva/README.md). |
| [`partners/`](partners/) | Projects, funding, project partners and collaborating institutions from Simula's website, NVA and OpenAlex. See [`partners/README.md`](partners/README.md). |

## Tests

Each folder has its own tests; see its README. A regression test in
`tests/` rebuilds everything from the data in the repository
(`./refresh.sh --no-fetch`, in a copy) and checks that this reproduces the
committed files, apart from the date the pages were generated:

```sh
python3 -m pytest tests
```

A GitHub Actions workflow (`.github/workflows/tests.yml`) runs all the tests
daily and can be started manually from the Actions tab.

## Refreshing the data

```sh
./refresh.sh
```

fetches the investigators' publications from NVA and their co-authors'
institutions from OpenAlex, rebuilds the three pages in `site/`, runs the
tests and prints the key figures before and after. `./refresh.sh --no-fetch`
rebuilds from the data already in the repository. Pages whose only change is
the date they were generated are left as they were. Nothing is committed:
check the changes first, in particular the review files written by
`nva/publication_data.py` (duplicates, names, book editors) and any new
institutions to merge or exclude (`partners/institution_merges.csv`,
`partners/affiliation_exclusions.csv`), then commit and push to publish.

A weekly workflow (`.github/workflows/refresh.yml`, Mondays at 04:00 UTC, or
started manually from the Actions tab) runs `refresh.sh` and, if anything
changed, opens a pull request with the key figures. Nothing is published
until the pull request is merged. It needs "Allow GitHub Actions to create
and approve pull requests" to be switched on in the repository's (and the
organisation's) Settings → Actions → General.

## Website

A second workflow (`.github/workflows/pages.yml`) publishes `site/` on GitHub
Pages whenever it changes on `main`. To update the pages, refresh the data
or rebuild them (see above), then commit and push `site/`.

The page makes no requests to other sites: the fonts and d3 are served from
`site/assets/` rather than from Google Fonts or a CDN, so visitors' IP
addresses are not passed on to third parties.

## Data sources and licences

The code is under the MIT licence (see [LICENSE](LICENSE)). The data comes
from these sources, under their own terms:

| Source | Used for | Terms |
|---|---|---|
| [NVA](https://nva.sikt.no/) (Nasjonalt vitenarkiv, Sikt) | Publications, author lists, projects | Public research information; reuse terms to be confirmed with Sikt |
| [OpenAlex](https://openalex.org) | Co-authors' institutions and countries, research fields | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) |
| [Prosjektbanken](https://prosjektbanken.forskningsradet.no) (Research Council of Norway) | Funding, programmes and summaries of NFR projects | Public project information; reuse terms to be confirmed with the Research Council |
| [simula.no](https://www.simula.no/research/projects) | Project durations, funding and partner text, investigators' pages | Content of Simula's website |
| [Public Sans](https://github.com/uswds/public-sans), [Spectral](https://github.com/productiontype/Spectral), [IBM Plex Mono](https://github.com/IBM/plex) | Fonts on the website | [SIL Open Font License 1.1](site/assets/fonts/) |
| [d3](https://d3js.org) | Charts on the website | [ISC licence](site/assets/d3-LICENSE.txt) |
| [topojson-client](https://github.com/topojson/topojson-client) | The map on the partners page | [ISC licence](site/assets/topojson-client-LICENSE.txt) |
| [world-atlas](https://github.com/topojson/world-atlas), built from [Natural Earth](https://www.naturalearthdata.com/) | Country outlines on the map | ISC licence; Natural Earth is in the public domain |

Publication abstracts are not stored, as they are usually copyrighted. Email
addresses are stored only for the centre's investigators (to recognise them
on Simula's project pages); others are removed. Names of co-authors and their
institutions are public bibliographic information.
