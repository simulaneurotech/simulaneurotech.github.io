# Collaborations and projects

The data and scripts behind two pages:

- **[Who we publish with](https://simulaneurotech.github.io/collaborators.html)**
  (`build_partners_page.py`): where the investigators' co-authors are, on a
  map and by kind of institution, clinical collaborators, the institutions
  with most joint publications, and departments by research area.
- **[Projects we lead](https://simulaneurotech.github.io/projects.html)**
  (`build_projects_page.py`): a timeline of the projects since 2016 led by an
  investigator, or where an investigator leads Simula's part, by funder.

The scripts read the publications from [`../nva/`](../nva/), so run that
first.

## Usage

Python 3, standard library only. Run from this folder:

```sh
python3 fetch_openalex.py          # co-authors' institutions and countries
python3 fetch_coauthor_details.py  # co-authors' departments
python3 build_partners_page.py     # writes ../site/collaborators.html
python3 build_projects_page.py     # writes ../site/projects.html
python3 -m pytest                  # tests
```

`../refresh.sh` runs these. Three more scripts help check the projects by
hand: `fetch_simula_projects.py` (Simula's project pages),
`fetch_nva_projects.py` (the NVA project register) and
`fetch_prosjektbanken.py` (Research Council projects).

## Files edited by hand

| File | Contents |
|---|---|
| `centre_projects.csv` | The projects (see below) |
| `logos.csv` | Project and funder logos (files in `../site/assets/logos/`) and where each came from |
| `institution_merges.csv` | Institutions to merge or rename, such as the hospitals of one health trust |
| `institution_kinds.csv` | Corrections to the kind of institution, and the research area of institutes and companies |
| `publication_relevance.csv` | Keep or drop decisions on the suggestions of `publication_relevance.py` (not used by the pages at present) |
| `investigator_emails.csv` | The investigators' Simula addresses, to recognise them on Simula's project pages |

The other CSV files are written by the fetch scripts, and `fetched.csv`
records when each source was fetched.

## How co-authors and institutions are counted

As on the overview page, with the same function (`main_institutions`): each
co-author counts once, at their main institution in the period, the one
they are listed at most often on the investigators' publications. Simula
Group colleagues and the investigators' own other affiliations are not
counted. Tests check that the two pages agree.

The kind of institution is its type in OpenAlex (university, hospital,
company, or research institute for the rest). The research area of a
co-author's department comes from keyword rules in `coauthor_fields.py`,
applied to the first of: their department on the joint papers, their
department in ORCID, their department on their other papers, the area of
their institute or company, other affiliation text, and their faculty or
main research field in OpenAlex. Areas from the last step are shown as
uncertain; corrections made by hand override all of these.

## Projects

`centre_projects.csv` is checked by hand against Simula's project pages,
the NVA project register, Prosjektbanken, CORDIS and the funders' own pages.
It gives each project's title, dates, leader and participants among the
investigators, funders and scheme, and the collaborating institutions named
by official sources. A project's status follows from its dates when the
pages are built; projects that started before 2016 are kept but not shown.
After checking, set `projects_checked` in `fetched.csv` to the date.

## Limitations

- OpenAlex covers publications with a DOI, about 70%; older publications
  often have none.
- Departments come from affiliation texts and public ORCID records, where
  co-authors have them.
- Collaborators on the projects page are only those listed by official
  sources; several projects list none.
