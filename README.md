# Centre for Digital Neurotechnology

Infographics for the
[Centre for Digital Neurotechnology](https://www.simula.no/research/research-centres/centre-digital-neurotechnology)
at Simula Research Laboratory, generated from publicly available data with
the code in this repository.

## Pages

| Page | Shows | Built in |
|---|---|---|
| [Overview](https://simulaneurotech.github.io/) | The investigators, and key figures on publications, co-authors, institutions and countries since 2024, 2021 and 2016 | [`centre/`](centre/) |
| [Who we publish with](https://simulaneurotech.github.io/collaborators.html) | The institutions of the investigators' co-authors, nationally and internationally: a map, kinds of institution, clinical collaborators, leading institutions and departments by research area | [`partners/`](partners/) |
| [Projects we lead](https://simulaneurotech.github.io/projects.html) | Projects since 2016 led by an investigator, or where an investigator leads Simula's part: a timeline by funder, with leaders, participants, collaborators and logos | [`partners/`](partners/) |
| [Who publishes with whom](https://simulaneurotech.github.io/coauthorship.html) | How the investigators publish together, and the co-authors outside the centre who link them (not yet linked from the overview) | [`nva/`](nva/) |

The pages are generated into [`site/`](site/) and published from there.
`site/partners.html` redirects the old address of "Who we publish with" to
`collaborators.html`.

## Contents

| Folder | Contents |
|---|---|
| [`nva/`](nva/) | The investigators' publications from NVA, with duplicates merged, and the co-authorship analysis. See [`nva/README.md`](nva/README.md). |
| [`partners/`](partners/) | The co-authors' institutions and research areas (OpenAlex, ORCID), and the centre's projects (Simula's project pages, NVA, Prosjektbanken, CORDIS). See [`partners/README.md`](partners/README.md). |
| [`centre/`](centre/) | The overview page, built from the data in `nva/` and `partners/`. See [`centre/README.md`](centre/README.md). |
| [`site/`](site/) | The generated pages, and the fonts, scripts and logos they use (`assets/`) |
| [`tests/`](tests/) | The regression test for the whole pipeline (see Tests) |

Everything runs with Python 3 and its standard library.

## Refreshing the publication data

```sh
./refresh.sh             # fetch, rebuild the pages and run the tests
./refresh.sh --no-fetch  # rebuild from the data already in the repository
```

`refresh.sh` fetches the investigators' publications from NVA, their
co-authors' institutions from OpenAlex and details about new co-authors from
OpenAlex and ORCID, rebuilds the pages in `site/`, runs the tests and prints
the key figures before and after. Pages whose only change is the date they
were generated are left as they were. Nothing is committed. Before
committing, check:

- the review files written by `nva/publication_data.py`: duplicates, merged
  names and removed book editors;
- new institutions to merge or leave out
  (`partners/institution_merges.csv`, `partners/affiliation_exclusions.csv`);
- co-authors who appear as several people (`partners/person_merges.csv`),
  Simula colleagues counted as co-authors (`partners/simula_colleagues.csv`),
  and co-authors whose institution or department is missing or wrong
  (`partners/coauthor_corrections.csv`).

A weekly workflow (`.github/workflows/refresh.yml`, Mondays at 04:00 UTC, or
started by hand from the Actions tab) first tags `main` as it is
(`before-refresh-YYYY-MM-DD`, pushed to GitHub, so the state before the
refresh can always be recovered), then runs `refresh.sh` and, if anything
changed, opens a pull request with the key figures. Nothing is published
until the pull request is merged. The workflow needs "Allow GitHub Actions
to create and approve pull requests" switched on in the repository's (and
the organisation's) Settings → Actions → General.

## Updating the projects

The projects are curated by hand in `partners/centre_projects.csv`, checked
against Simula's project pages, the NVA project register, Prosjektbanken,
CORDIS and the funders' own pages; `refresh.sh` does not change them. After
editing the file, set `projects_checked` in `partners/fetched.csv` to the
date and rebuild with `./refresh.sh --no-fetch`. A project's status
(upcoming, active, ended) follows from its dates when the pages are built.
See [`partners/README.md`](partners/README.md).

## Website

A workflow (`.github/workflows/pages.yml`) publishes `site/` on GitHub Pages
whenever it changes on `main`: rebuild the pages, then commit and push.

The pages make no requests to other sites: fonts, scripts and logos are
served from `site/assets/` rather than from Google Fonts or a CDN, so
visitors' IP addresses are not passed on to third parties. Tests check this
for the overview, "Who we publish with" and "Who publishes with whom"; the
projects page is not yet covered.

## Tests

Each folder has its own tests; see its README. The regression test in
`tests/` rebuilds everything from the data in the repository
(`./refresh.sh --no-fetch`, in a copy) and checks that this reproduces the
committed files, apart from the date the pages were generated:

```sh
python3 -m pytest tests
```

Because project statuses follow the date, this test fails on a day a project
starts or ends, until the pages are rebuilt. A workflow
(`.github/workflows/tests.yml`) runs all the tests daily, and can be started
by hand from the Actions tab.

## Data sources and licences

The code is under the MIT licence (see [LICENSE](LICENSE)). The data comes
from these sources, under their own terms:

| Source | Used for | Terms |
|---|---|---|
| [NVA](https://nva.sikt.no/) (Nasjonalt vitenarkiv, Sikt) | Publications, author lists, project register | Public research information; reuse terms to be confirmed with Sikt |
| [OpenAlex](https://openalex.org) | Co-authors' institutions and countries, research fields | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) |
| [ORCID](https://orcid.org) | Co-authors' departments, from their public employment records | Public data, [CC0](https://creativecommons.org/publicdomain/zero/1.0/) |
| [Prosjektbanken](https://prosjektbanken.forskningsradet.no) (Research Council of Norway) | Leaders, years, funding, schemes and partner countries of Research Council projects | Public project information; reuse terms to be confirmed with the Research Council |
| [CORDIS](https://cordis.europa.eu) (European Commission) | Dates, funding and beneficiaries of EU projects | © European Union; reuse allowed with attribution (Commission Decision 2011/833/EU) |
| [simula.no](https://www.simula.no/research/projects) | Project descriptions, durations, partners and contacts; investigators' pages | Content of Simula's website |
| The funders' and partners' own pages (K. G. Jebsen Foundation, Wellcome, Centre for Advanced Study, Chalmers) | Leaders, dates and collaborators of individual projects, as recorded in `partners/centre_projects.csv` | Their own terms |
| Project and funder logos | The projects page | Belong to their owners; used to identify the projects and acknowledge funding. Where each came from is in `partners/logos.csv` |
| [Public Sans](https://github.com/uswds/public-sans), [Spectral](https://github.com/productiontype/Spectral), [IBM Plex Mono](https://github.com/IBM/plex) | Fonts | [SIL Open Font License 1.1](site/assets/fonts/) |
| [d3](https://d3js.org) | Charts | [ISC licence](site/assets/d3-LICENSE.txt) |
| [topojson-client](https://github.com/topojson/topojson-client) | The map on "Who we publish with" | [ISC licence](site/assets/topojson-client-LICENSE.txt) |
| [world-atlas](https://github.com/topojson/world-atlas), built from [Natural Earth](https://www.naturalearthdata.com/) | Country outlines on the map | ISC licence; Natural Earth is in the public domain |

Publication abstracts are not stored, as they are usually copyrighted. Email
addresses are stored only for the centre's investigators (to recognise them
on Simula's project pages); others are removed. Names of
co-authors and their institutions are public bibliographic information.
