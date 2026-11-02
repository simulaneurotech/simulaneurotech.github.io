# Partners, projects and funding

Data on the centre's collaborations and partnerships beyond co-authorship
between investigators: research projects, funders, and the institutions and
countries of everyone the investigators publish with. Collected to illustrate
the centre for external stakeholders. Projects, merges and exclusions have
been curated by hand; the investigators should still check their own
projects and collaborators before the page is published.

**Draft page:** [`../site/partners.html`](../site/partners.html) shows where the centre's co-authors are, what kinds of institutions they
work at, and clinical collaborators (hospitals with joint publications), with
a switch for the publication period (since 2024, 2021 or 2016). Selecting an
institution on the map or in a table lists its joint publications, with the
investigators and the co-authors at that institution. Co-authors are grouped
into mathematics and technology, experimental and basic medicine, and
clinical medicine, with a switch to show one field. The centre's projects by
funder and the formal project partners are hidden for now
(`SHOW_PROJECTS = False` in `build_partners_page.py`). Open it
locally in a browser.

The scripts read the investigators and their publications from
[`../nva/`](../nva/), so run the NVA pipeline there first.

## Files

| File | Contents |
|---|---|
| `investigator_emails.csv` | Simula email address of each investigator, used to link Simula's project pages to investigators; `confirmed` says whether the address has been checked |
| `fetch_simula_projects.py` | Fetches all projects on [simula.no/research/projects](https://www.simula.no/research/projects) from Simula's public content API |
| `fetch_nva_projects.py` | Fetches the investigators' projects from the NVA project register |
| `fetch_prosjektbanken.py` | Looks up the Research Council of Norway projects in `centre_projects.csv` in [Prosjektbanken](https://prosjektbanken.forskningsradet.no), by grant number |
| `fetch_openalex.py` | Looks up the institution and country of every author of the centre's publications in [OpenAlex](https://openalex.org), by DOI, with each publication's research field and each co-author's own main field. Abstracts are only scanned for terms, not stored, and email addresses are removed from affiliation text |
| `publication_relevance.py` | Suggests which publications are relevant to the centre (keep, review or drop, with the reason), keeping decisions made by hand |
| `build_partners_page.py` | Builds `../site/partners.html` from the curated projects and the OpenAlex data |
| `partners_page_template.html` | Page template: layout, map, tables and timeline |
| `world-110m.json` | Country outlines for the map, from the [world-atlas](https://github.com/topojson/world-atlas) package (ISC license, built from Natural Earth) |
| `institution_merges.csv` | **Curated by hand**: institutions to merge or rename on the page (`institution` as in OpenAlex, `use_name` to show), such as the Sørlandet sykehus hospitals, and Gentofte Hospital as part of Copenhagen University Hospital |
| `publication_relevance.csv` | **Checked by hand**: the suggestion for each publication, and a `decision` column (keep or drop) that overrides it. Re-running `publication_relevance.py` keeps the decisions and notes |
| `field_rules.csv` | **Curated by hand**: rules that put co-authors in a field (`math`, `basic` or `clinical`) by their affiliation text; the first matching pattern wins |
| `affiliation_exclusions.csv` | **Curated by hand**: affiliations OpenAlex has wrong for individual co-authors (`author`, `institution`), left out on the page |
| `centre_projects.csv` | **Curated by hand**, not written by any script: the projects to show as centre projects (`include`), with investigators, funders, grants and partners checked. Seeded from `simula_projects.csv` with the projects naming an investigator and those about the brain, heart or neuroscience. `nva_project_id` links a project to the NVA project register; `partners` combines the partners on Simula's page with the institutions of NVA participants who are not centre investigators (Simula Group left out) |
| `simula_projects.csv` | All Simula projects: duration, research areas, centre investigators, and the funding and partner sections of the description as text (contact emails are not stored) |
| `nva_projects.csv` | NVA projects with a centre investigator: dates, funder and grant number, coordinating institution, participants |
| `nva_project_participants.csv` | Everyone taking part in those projects, with their unit (department) and the institution it belongs to |
| `prosjektbanken_projects.csv` | Research Council of Norway projects: titles, project leader and lead institution, years, total funding of the whole project (NOK), programmes, scheme, funding ministries, summary and reported results |
| `openalex_affiliations.csv` | One row per author per institution per publication, with the affiliation text on the paper |
| `openalex_works.csv` | One row per publication: research field and subfield, title, and whether the title or abstract has methods, physiological or wireless terms |
| `openalex_authors.csv` | The field most of each co-author's own work is in |
| `partner_institutions.csv` | Institutions where the investigators' co-authors are (not the investigators' own affiliations): country, type (education, healthcare, company, ...), ROR ID, city and coordinates, number of joint publications and which investigators |

## Usage

Requires Python 3 (standard library only). Run from this folder:

```sh
cd partners
python3 fetch_simula_projects.py   # writes simula_projects.csv
python3 fetch_nva_projects.py      # writes nva_projects.csv, nva_project_participants.csv
python3 fetch_prosjektbanken.py    # writes prosjektbanken_projects.csv
python3 fetch_openalex.py          # writes openalex_*.csv, partner_institutions.csv
python3 publication_relevance.py   # writes publication_relevance.csv (keeps decisions)
python3 build_partners_page.py     # writes ../site/partners.html
```

Institutions are counted as on the overview page (`../centre/`), with the
same function (`main_institutions` in `build_partners_page.py`): each
co-author once, at their main institution in the period, the one they are
listed at most often on the investigators' publications. An institution's
joint publications are all those of the co-authors who are mainly there.
Colleagues whose main institution is in the Simula Group (institutions with
"Simula" in their name) are not counted, and neither are the investigators'
own other affiliations on their papers, such as a university position. All
the investigators' publications found in OpenAlex are used, as on the
overview page; a test checks that the two pages give the same institutions
and countries. Investigators are recognised among a
paper's OpenAlex authors by name (column `investigator` in
`openalex_affiliations.csv`). Projects come from `centre_projects.csv`;
rows with `include` set to `no` are left out, and so are projects that
started before 2016 (`FIRST_PROJECT_YEAR` in `build_partners_page.py`), and the `status` column
(active, upcoming, ended) decides which projects show as active. A duration
with only a start ("2022–") is an ongoing project. Funders are grouped for
colour as `FUNDER_GROUPS` in `build_partners_page.py` says; others show as
"Other". Project partners on the page are the `partners` column. Clinical
collaborators need at least `MIN_CLINICAL` joint publications in the period
(currently 1), set in the page template.

## Relevant publications

The pages currently use all the investigators' publications. To limit them
to publications relevant to the centre (core mathematical, computational and
technological research, including general data mining, and methods work with
a physiological application), `publication_relevance.py` suggests a decision
for each publication, in this order:

1. Wireless networks or the Internet of Things in the title: drop.
2. Methods terms (model, simulation, computational, ...) and a physiological
   subject (brain, cells, heart, ...) in the title or abstract: keep.
3. Wireless networks or IoT only in the abstract, or OpenAlex's subfield
   "Computer Networks and Communications": review.
4. Main research field Mathematics, Computer Science, Engineering, Physics or
   Decision Sciences: keep.
5. Only methods terms, or only a physiological subject: review.
6. Neither: drop.

A publication counts as relevant when its `decision` is `keep`, or when it
has no decision and the suggestion is `keep` (`relevant` in
`publication_relevance.py`). Fill in `decision` in
`publication_relevance.csv` for the reviews and for any suggestion you
disagree with. The pages do not use this at present.

## Fields of collaboration

Each co-author on each publication is put in one field: mathematics and
technology, experimental and basic medicine, or clinical medicine. The first
rule in `field_rules.csv` whose pattern matches the affiliation text on the
paper decides (the institution's own name is removed first, so "University
of Life Sciences" does not count as life sciences). Without a match, a
co-author at a hospital counts as clinical, and otherwise the field of their
own research in OpenAlex decides (`AUTHOR_GROUPS` in
`build_partners_page.py`). Those still undecided are "unclassified". An
institution can have co-authors in several fields.

## Sources and limitations

- **Simula's project pages.** 161 projects. Title, duration, completion and
  research area are structured fields. Partners, funding and contacts are
  only in the description text and are extracted from sections headed
  "Partners", "Funding" and similar, so they need checking by hand. A project
  is linked to an investigator when their name or email address appears on
  the page; most pages give a contact email rather than names, and some
  investigators are not listed as contacts on any page.
- **NVA projects.** Structured, with grant numbers, coordinating institution
  and all participants, but incomplete: many projects are not registered,
  and some investigators have none.
- **Prosjektbanken.** The Research Council of Norway's project database,
  read from the data embedded in its project pages (not a documented API,
  so it may change). Projects are looked up by grant number, so projects
  without one in `centre_projects.csv` are not covered, and very new
  projects may be missing or have no amount yet. Funding is for the whole
  project, including partners' shares; the total on the page counts only
  projects led at Simula. There are no partner institutions.
- **OpenAlex.** Covers publications with a DOI (about 70%; older
  publications often have none). Institutions are as OpenAlex matched them
  from the papers. An investigator listed under an unusual form of their
  name may not be recognised, and their affiliation would then count as a
  partner.
- **Formal partners** beyond projects (agreements with hospitals, industry or
  other centres) are not in any of these sources and need to come from the
  centre. Project partners are only as complete as Simula's pages and the
  NVA project register; several projects list none.

## Tests

```sh
cd partners
python3 -m pytest
```

The tests use small made-up inputs and need no network access. They run
daily on GitHub Actions together with the tests in `../nva/`.
