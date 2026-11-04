# Collaborations and projects

The data and scripts behind two of the centre's pages: the institutions of
everyone the investigators publish with, and the projects the investigators
lead. The scripts read the investigators and their publications from
[`../nva/`](../nva/), so run the NVA pipeline there first.

## Pages

**Who we publish with:** <https://simulaneurotech.github.io/collaborators.html>,
built by `build_partners_page.py` into
[`../site/collaborators.html`](../site/collaborators.html). For a publication
period (since 2024, 2021 or 2016) it shows where the co-authors' institutions
are on a map (all, or only universities, hospitals, or institutes and others;
for the world, Europe, or the US and Canada), the kinds of institution,
clinical collaborators (hospitals with joint publications), the institutions
with most joint publications, and the co-authors' departments by research
area. Selecting an institution lists its joint publications, with the
investigators and the co-authors there. The banner gives the number of
publications, institutions, departments, countries, hospitals and active
projects.

**Projects we lead:** <https://simulaneurotech.github.io/projects.html>,
built by `build_projects_page.py` into
[`../site/projects.html`](../site/projects.html). A timeline of the projects
since 2016 that an investigator leads, or where an investigator leads
Simula's part, coloured by main funder, with each project's logo and its
leader (in bold) and participants. Selecting a project shows its leader,
host, participants, funder and scheme, and the institutions it collaborates
with, with their source. The funders' logos are shown under the timeline.
Funding amounts are not shown.

Both pages can also be opened locally in a browser.

## Usage

Requires Python 3 (standard library only). Run from this folder:

```sh
cd partners
python3 fetch_openalex.py          # writes openalex_*.csv, partner_institutions.csv
python3 fetch_coauthor_details.py  # writes coauthor_*.csv
python3 publication_relevance.py   # writes publication_relevance.csv (keeps decisions)
python3 build_partners_page.py     # writes ../site/collaborators.html
python3 fetch_simula_projects.py   # writes simula_projects.csv
python3 fetch_nva_projects.py      # writes nva_projects.csv, nva_project_participants.csv
python3 fetch_prosjektbanken.py    # writes prosjektbanken_projects.csv
python3 build_projects_page.py     # writes ../site/projects.html
```

`../refresh.sh` runs `fetch_openalex.py`, `fetch_coauthor_details.py` and
both builders. The project fetch scripts are for checking the projects by
hand (see Projects).

## Files

**Scripts and templates**

| File | Contents |
|---|---|
| `fetch_openalex.py` | Looks up the institution and country of every author of the investigators' publications in [OpenAlex](https://openalex.org), by DOI, with each publication's research field. Abstracts are only scanned for terms, not stored, and email addresses are removed from affiliation texts |
| `fetch_coauthor_details.py` | For the co-authors at universities, research institutes and companies: their ORCID iD and main research field from OpenAlex, their public ORCID employment records (organisation, department, years only) and, where those name no department, the affiliation texts naming their institution on their other papers since 2016. Only co-authors not fetched before are looked up (`--all` fetches everyone again); when OpenAlex's daily quota is used up, it saves what it has and leaves the rest for the next run |
| `publication_relevance.py` | Suggests which publications are relevant to the centre (see Relevant publications) |
| `coauthor_fields.py` | Each co-author's kind of institution and research area (see Kinds of institution and research areas) |
| `build_partners_page.py` | Builds `../site/collaborators.html`; also has the functions shared with the other builders, such as `main_institutions` and `projects` |
| `partners_page_template.html` | Template for "Who we publish with" |
| `fetch_simula_projects.py` | Fetches all projects on [simula.no/research/projects](https://www.simula.no/research/projects) from Simula's public content API |
| `fetch_nva_projects.py` | Fetches the investigators' projects from the NVA project register |
| `fetch_prosjektbanken.py` | Looks up the Research Council of Norway projects in `centre_projects.csv` in [Prosjektbanken](https://prosjektbanken.forskningsradet.no), by grant number |
| `build_projects_page.py` | Builds `../site/projects.html` from `centre_projects.csv` and `logos.csv` |
| `projects_page_template.html` | Template for "Projects we lead" |

**Curated or checked by hand**

| File | Contents |
|---|---|
| `centre_projects.csv` | The projects (see Projects) |
| `logos.csv` | The project and funder logos on the projects page: their files in `../site/assets/logos/` (resized copies), a version for dark backgrounds (`file_dark`: a file, `same` when the logo works on dark as it is, or empty for a white tile), alt text, and where each came from |
| `institution_merges.csv` | Institutions to merge or rename (`institution` as in OpenAlex, `use_name` to show), such as the Sørlandet sykehus hospitals, and Gentofte Hospital as part of Copenhagen University Hospital |
| `affiliation_exclusions.csv` | Affiliations OpenAlex has wrong for individual co-authors (`author`, `institution`), left out |
| `person_merges.csv` | OpenAlex records of the same person (`author`, `openalex_author_id`, empty when a paper has no author ID), counted as the record with OpenAlex author ID `same_as` |
| `simula_colleagues.csv` | Co-authors who are Simula colleagues although OpenAlex does not give a Simula Group institution as their main one (`author`, `openalex_author_id`); left out like other colleagues |
| `coauthor_corrections.csv` | A co-author's institution, department and research area where OpenAlex has none or the wrong one (`author`, `openalex_author_id`, `institution`, `department`, `discipline`) |
| `institution_kinds.csv` | Kinds of institution that override the institution's type in OpenAlex (`kind`, such as QB3 as a university), and the research area of research institutes and companies (`discipline`) |
| `publication_relevance.csv` | Written by `publication_relevance.py`, with a `decision` column (keep or drop) set by hand that overrides the suggestion; re-running the script keeps the decisions and notes |
| `investigator_emails.csv` | Each investigator's Simula email address, used to recognise them on Simula's project pages; `confirmed` says whether the address has been checked |

The merges, exclusions and corrections apply on all the pages, including the
overview.

**Fetched data** (written by the fetch scripts)

| File | Contents |
|---|---|
| `openalex_affiliations.csv` | One row per author per institution per publication, with the affiliation text on the paper |
| `openalex_works.csv` | One row per publication: research field and subfield, title, and whether the title or abstract has methods, physiological or wireless terms |
| `partner_institutions.csv` | Institutions where the investigators' co-authors are (not the investigators' own affiliations): country, type (education, healthcare, company, ...), ROR ID, city and coordinates, number of joint publications and which investigators |
| `coauthor_profiles.csv`, `coauthor_employments.csv`, `coauthor_affiliations.csv` | Written by `fetch_coauthor_details.py` (see above) |
| `simula_projects.csv` | All Simula projects: duration, research areas, centre investigators, and the funding and partner sections of the description as text (contact emails are not stored) |
| `nva_projects.csv` | NVA projects with a centre investigator: dates, funder and grant number, coordinating institution, participants |
| `nva_project_participants.csv` | Everyone taking part in those projects, with their unit (department) and the institution it belongs to |
| `prosjektbanken_projects.csv` | Research Council of Norway projects: titles, project leader and lead institution, years, total funding of the whole project (NOK), programmes, scheme, funding ministries, summary and reported results |
| `fetched.csv` | When each source here was last fetched, written by the fetch scripts with `../nva/fetch_log.py` and shown on the pages; and `projects_checked`, set by hand, when `centre_projects.csv` was last checked against its sources |
| `world-110m.json` | Country outlines for the map, from the [world-atlas](https://github.com/topojson/world-atlas) package (ISC licence, built from Natural Earth) |

## How institutions are counted

As on the overview page (`../centre/`), with the same function
(`main_institutions` in `build_partners_page.py`): each co-author counts
once, at their main institution in the period, the one they are listed at
most often on the investigators' publications. An institution's joint
publications are all those of the co-authors who are mainly there.
Colleagues whose main institution is in the Simula Group (institutions with
"Simula" in their name) are not counted, and neither are the investigators'
own other affiliations on their papers, such as a university position.
Investigators are recognised among a paper's OpenAlex authors by name
(column `investigator` in `openalex_affiliations.csv`). All the
investigators' publications found in OpenAlex are used, and tests check
that the two pages give the same institutions, countries and publication
counts.

Clinical collaborators need at least `MIN_CLINICAL` joint publications in the
period (currently 1, set in the page template).

## Kinds of institution and research areas

The kind of an institution is its type in OpenAlex: education is
Universities, healthcare Hospitals, company Companies, and facility,
non-profit, government and similar are Research institutes (`KINDS` in
`build_partners_page.py`); `institution_kinds.csv` corrects a few by hand.

The section "By research area" shows for each period the departments where
the co-authors work, by research area, with the number of co-authors at
each; an institution taken as a whole (such as a company, or a hospital with
no department named) counts as one. It names institutions and departments,
not people. Co-authors are counted as on the overview page, at their main
institution; spellings of the same department at an institution are counted
together.

The areas are mathematics & statistics, computer science & engineering,
physics & chemistry, biosciences, experimental & basic medicine, clinical
medicine and other. `coauthor_fields.py` decides the area by keyword rules
(`RULES`) on the name of the co-author's unit, taking the first of these
that names one:

1. a department, division, clinic or similar, or a faculty named after one
   discipline, in their affiliation on the publications with the centre;
2. their department at that institution in ORCID;
3. a department in their affiliation on their other papers since 2016;
4. at research institutes and companies, the institution's area
   (`discipline` in `institution_kinds.csv`, else its name);
5. an institute, centre or lab, or other affiliation text on the
   publications with the centre;
6. a faculty covering several disciplines (including any faculty of
   medicine), or their main research field in OpenAlex.

Areas from 6 are shown as an uncertain classification. At hospitals, a
department or institute (1 to 5) decides, and otherwise clinical medicine.
Co-authors with none of these, and those whose institution is unknown, count
as other, also uncertain. `coauthor_corrections.csv` overrides all of these
for the co-authors it lists. In hand checks of samples, 1 to 3 were nearly
always right, 5 about three times in four, and 6 about half the time;
OpenAlex's research field labels people by topic rather than department (its
"Medicine" was mostly biomedical engineers). The area is that of the
department a person belongs to, not necessarily their research.

## Projects

`centre_projects.csv` lists the projects since 2016 led by a centre
investigator, or where an investigator leads Simula's part of a project led
elsewhere. Each row is checked by hand against Simula's project pages, the
NVA project register, Prosjektbanken, CORDIS and the funders' own pages; the
fetched project files above help with that. After checking, set
`projects_checked` in `fetched.csv` to the date: the projects page shows it.

| Column | Contents |
|---|---|
| `title`, `short`, `url` | Full title, short name for the timeline (else taken from the title), and the project's page |
| `duration` | Dates as free text ("2024-2029", "01.10.2021-30.06.2025", "April 2026 - December 2029"); a start only ("2022–") is an ongoing project. Dates are the funder's where the sources differ |
| `status` | Empty: worked out from the dates on the day the pages are built (upcoming, active, ended). Set it to `ended` only for a project that ended before its dates say |
| `include`, `relevance` | `no` leaves a project out, with the reason in `note`; `relevance` is core or related (not shown) |
| `leader`, `leader_role`, `host` | The investigator leading the project, as `lead`, `Simula lead` (the project is led elsewhere, by the `host`) or `contact` |
| `participants` | The other centre investigators on the project |
| `funders`, `scheme`, `grants` | Funders, as named in `FUNDER_GROUPS` in `build_partners_page.py` for the colours (Research Council of Norway, ERC and EU, the foundations); others show as Other |
| `funding`, `funding_source` | The amount and where it comes from; not shown on the pages |
| `collaborators`, `collaborator_countries`, `collaborator_source` | The institutions (or only countries) the project collaborates with, only as listed by official sources, and which |
| `nva_project_id`, `simula_id`, `found_by`, `note` | Links to the sources, and notes on decisions |

Projects that started before 2016 (`FIRST_PROJECT_YEAR` in
`build_partners_page.py`) are kept in the file but not shown. The banner on
"Who we publish with" counts the active projects.

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

## Sources and limitations

- **OpenAlex.** Covers publications with a DOI (about 70%; older
  publications often have none). Institutions are as OpenAlex matched them
  from the papers. An investigator listed under an unusual form of their
  name may not be recognised, and their affiliation would then count as a
  collaborator's.
- **ORCID.** Departments come from co-authors' public employment records,
  where they have them.
- **Simula's project pages.** Title, duration, completion and research area
  are structured fields. Partners, funding and contacts are only in the
  description text, extracted from sections headed "Partners", "Funding"
  and similar, so they need checking by hand. A project is linked to an
  investigator when their name or email address appears on the page; most
  pages give a contact email rather than names, and some investigators are
  not listed as contacts on any page.
- **NVA project register.** Structured, with grant numbers, coordinating
  institution and all participants, but incomplete: many projects are not
  registered.
- **Prosjektbanken.** The Research Council of Norway's project database,
  read from the data embedded in its pages (not a documented API, so it may
  change). Very new projects may be missing or have no amount yet. Funding
  is the Research Council's, for the whole project including partners'
  shares. It names no partner institutions, only partner countries for some
  projects.
- **CORDIS.** The EU's project database: dates, EU contribution and
  beneficiaries of EU projects. For ERC grants, Simula is the only
  beneficiary.
- **Collaborators** on the projects page are only as complete as these
  sources and the funders' own pages; several projects list none. Formal
  agreements with hospitals, industry or other centres beyond the projects
  are in none of them.

## Tests

```sh
cd partners
python3 -m pytest
```

The tests use small made-up inputs and need no network access. They run
daily on GitHub Actions together with the other tests.
