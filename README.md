# Centre for Digital Neurotechnology

Pages on the research of the
[Centre for Digital Neurotechnology](https://www.simula.no/research/research-centres/centre-digital-neurotechnology)
at Simula Research Laboratory and SimulaMet, built from public data with
the code in this repository and published at
<https://simulaneurotech.github.io/>.

## Pages

| Page | Shows |
|---|---|
| [Overview](https://simulaneurotech.github.io/) | The investigators, and key figures on publications, co-authors, institutions and countries since 2024, 2021 and 2016 |
| [Who we publish with](https://simulaneurotech.github.io/collaborators.html) | The institutions of the investigators' co-authors: a map, kinds of institution, clinical collaborators, and departments by research area |
| [Projects we lead](https://simulaneurotech.github.io/projects.html) | Projects since 2016 led by an investigator, or where an investigator leads Simula's part, on a timeline by funder |
| [Who publishes with whom](https://simulaneurotech.github.io/coauthorship.html) | How the investigators publish together, and the co-authors who link them |

Spotted an error? Please [open an issue](https://github.com/simulaneurotech/simulaneurotech.github.io/issues).

## How the pages are made

Publications are the investigators' records in
[NVA](https://nva.sikt.no/) (Nasjonalt vitenarkiv). Co-authors' institutions
and countries come from [OpenAlex](https://openalex.org), their departments
from public [ORCID](https://orcid.org) records, and the projects from
Simula's project pages, NVA, Prosjektbanken, CORDIS and the funders' own
pages, checked by hand. Each folder's README describes its part in detail.

| Folder | Contents |
|---|---|
| [`nva/`](nva/) | The investigators' publications, and how they publish together |
| [`partners/`](partners/) | Co-authors' institutions and research areas, and the projects |
| [`centre/`](centre/) | The overview page |
| [`site/`](site/) | The published pages, with their fonts, scripts and logos |
| [`tests/`](tests/) | A test that rebuilding reproduces the pages |

Everything runs with Python 3 and its standard library. The pages are
rebuilt with `./refresh.sh`. The tests in each folder run with
`python3 -m pytest`, and daily on GitHub.

The pages load nothing from other sites: fonts, scripts and logos are served
from `site/assets/`, so visitors' IP addresses are not passed on to third
parties.

## Data sources and licences

The code is under the MIT licence (see [LICENSE](LICENSE)). The data comes
from these sources, under their own terms:

| Source | Used for | Terms |
|---|---|---|
| [NVA](https://nva.sikt.no/) (Sikt) | Publications, author lists, project register | Public research information; reuse terms to be confirmed with Sikt |
| [OpenAlex](https://openalex.org) | Co-authors' institutions and countries, research fields | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) |
| [ORCID](https://orcid.org) | Co-authors' departments, from their public employment records | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) |
| [Prosjektbanken](https://prosjektbanken.forskningsradet.no) (Research Council of Norway) | Leaders, years, schemes and partner countries of Research Council projects | Public project information; reuse terms to be confirmed with the Research Council |
| [CORDIS](https://cordis.europa.eu) (European Commission) | Dates and beneficiaries of EU projects | © European Union; reuse allowed with attribution (Commission Decision 2011/833/EU) |
| [simula.no](https://www.simula.no/research/projects) | Project descriptions, durations and partners; investigators' pages | Content of Simula's website |
| The funders' and partners' own pages (K. G. Jebsen Foundation, Wellcome, Centre for Advanced Study, Chalmers) | Leaders, dates and collaborators of individual projects | Their own terms |
| Project and funder logos | The projects page | Belong to their owners; used to identify the projects and acknowledge funding (sources in `partners/logos.csv`) |
| [Public Sans](https://github.com/uswds/public-sans), [Spectral](https://github.com/productiontype/Spectral), [IBM Plex Mono](https://github.com/IBM/plex) | Fonts | [SIL Open Font License 1.1](site/assets/fonts/) |
| [d3](https://d3js.org) | Charts | [ISC licence](site/assets/d3-LICENSE.txt) |
| [topojson-client](https://github.com/topojson/topojson-client) | The map on "Who we publish with" | [ISC licence](site/assets/topojson-client-LICENSE.txt) |
| [world-atlas](https://github.com/topojson/world-atlas), built from [Natural Earth](https://www.naturalearthdata.com/) | Country outlines on the map | ISC licence; Natural Earth is in the public domain |

Publication abstracts are not stored, as they are usually copyrighted, and
email addresses only for the centre's investigators.
