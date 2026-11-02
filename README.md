# Centre for Digital Neurotechnology

Tools and data related to the [Centre for Digital Neurotechnology](https://www.simula.no/about/news/simula-establishes-centre-digital-neurotechnology)
at Simula.

**Overview page:** [`centre/centre_page.html`](centre/centre_page.html) shows the investigators, key figures on publications, co-authors,
institutions and countries, and the centre's projects.

**Interactive page:** [`nva/collaboration_map.html`](nva/collaboration_map.html) shows how the centre investigators publish together, and how they are linked
through co-authors outside the centre.

**Draft page:** [`partners/partners_page.html`](partners/partners_page.html) shows the institutions the centre collaborates with in Norway and abroad, and its
projects by funder. It is a draft for review.

## Contents

| Folder | Contents |
|---|---|
| [`centre/`](centre/) | The centre's overview page, built from the data in `nva/` and `partners/`. See [`centre/README.md`](centre/README.md). |
| [`nva/`](nva/) | Investigators' publication lists from NVA (formerly Cristin), co-authorship analysis and the interactive page. See [`nva/README.md`](nva/README.md). |
| [`partners/`](partners/) | Projects, funding, project partners and collaborating institutions from Simula's website, NVA and OpenAlex. See [`partners/README.md`](partners/README.md). |

## Tests

Each folder has its own tests; see its README. A GitHub Actions workflow
(`.github/workflows/tests.yml`) runs them daily and can be started manually
from the Actions tab.

## Data sources and licences

The code is under the MIT licence (see [LICENSE](LICENSE)). The data comes
from these sources, under their own terms:

| Source | Used for | Terms |
|---|---|---|
| [NVA](https://nva.sikt.no/) (Nasjonalt vitenarkiv, Sikt) | Publications, author lists, projects | Public research information; reuse terms to be confirmed with Sikt |
| [OpenAlex](https://openalex.org) | Co-authors' institutions and countries, research fields | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) |
| [Prosjektbanken](https://prosjektbanken.forskningsradet.no) (Research Council of Norway) | Funding, programmes and summaries of NFR projects | Public project information; reuse terms to be confirmed with the Research Council |
| [simula.no](https://www.simula.no/research/projects) | Project durations, funding and partner text, investigators' pages | Content of Simula's website |
| [world-atlas](https://github.com/topojson/world-atlas), built from [Natural Earth](https://www.naturalearthdata.com/) | Country outlines on the map | ISC licence; Natural Earth is in the public domain |

Publication abstracts are not stored, as they are usually copyrighted. Email
addresses are stored only for the centre's investigators (to recognise them
on Simula's project pages); others are removed. Names of co-authors and their
institutions are public bibliographic information.
