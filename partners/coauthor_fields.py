"""Who the co-authors are: kind of institution, and field.

Used by build_partners_page.py. Each co-author is placed at their main
institution in the period, as on the other pages (main_institutions in
build_partners_page.py), and given

- a kind of institution: Universities, Hospitals, Research institutes or
  Companies, from the institution's type in OpenAlex (KINDS), unless
  institution_kinds.csv (curated by hand) says otherwise; or "Institution
  unknown";
- a field (GROUPS), from the first of these that names one (keyword rules,
  RULES, on the unit's name):
  1. a department, division, clinic or similar on their papers with the
     centre's investigators, or a faculty named after one discipline
  2. their department at the institution in ORCID
  3. a department on their other recent papers, where it names the
     institution
  4. for research institutes and companies, the institution's field
     (institution_kinds.csv, else its name)
  5. an institute, centre or lab on their papers, or other affiliation text
     on the papers with the centre
  6. a faculty covering several disciplines (such as a faculty of medicine),
     or the field most of their research is in according to OpenAlex

Fields from 6 are an uncertain classification. At hospitals, a department
or institute (1 to 5) decides, else clinical medicine. Co-authors with none
of these, and those whose institution is unknown, count as "Other", also
uncertain.
"""

import re
from collections import Counter, defaultdict

from build_partners_page import KINDS, main_institutions, name_key

GROUPS = [
    "Mathematics & statistics",
    "Computer science & engineering",
    "Physics & chemistry",
    "Biosciences",
    "Experimental & basic medicine",
    "Clinical medicine",
    "Other",
]
M, C, P, B, X, K, O = GROUPS
# Fields on the page, in order
FIELDS = GROUPS

# Keyword rules on a unit's name, in order: the first group with a match wins
RULES = [
    # Engineering first where the name also has a life-science word
    (
        C,
        (
            r"bioengineer|biomedical engineer|bioingenier|bioingegner|biomedical technolog|"
            r"medical technolog|health technolog"
        ),
    ),
    (
        X,
        r"cancer research|institute for medical research|experimental medical research",
    ),
    (
        K,
        (
            r"family medicine|general practice|preventive medicine|community health|"
            r"radiation scien|radiolog|neurolog|neurosurg|cardiolog|cardiac|cardiothorac|"
            r"cardiovascular med|psychiatr|pa?ediatric|oncolog|cancer|surg|an(a)?esthe|"
            r"intensive care|emergency|clinical|clinic|klinik|nuclear medicine|radiotherap|"
            r"radiation therap|internal medicine|gastro|nephrol|endocrin|obstetric|"
            r"gyn(a)?ecol|ophthalm|otolaryng|dermatol|patholog|geriatr|rehabilitat|stroke|"
            r"epilep|asthma|hospital|neuroradiol|vascular|public health|health science|"
            r"health service|global health|epidemiol|medical cent(er|re)|nursing|dentist|"
            r"odontol"
        ),
    ),
    (
        X,
        (
            r"physiolog|anatom|pharmac|basic medical|molecular medicine|biomedicine|"
            r"biomedical science|neuroscien|neurobiol|brain|neuroplasticity|neurophysiol|"
            r"neural circuit|medical school|faculty of medicine|school of medicine|medicine"
        ),
    ),
    (
        B,
        (
            r"bioscien|biolog|biochem|genetic|genomic|zoolog|botan|ecolog|evolution|plant|"
            r"microbio|veterinar|marine|life science|bioinformat|food|nutrition"
        ),
    ),
    (
        M,
        (
            r"mathemat|statistic|numerical|applied analysis|scientific computing|"
            r"computational science|actuar|matematik|matematica|mathématique|analysis and"
        ),
    ),
    (
        C,
        (
            r"informatic|computer|computing|\bict\b|information (and communication )?technolog|"
            r"electrical|electronic|mechanical|engineering|data science|artificial intelligence|"
            r"machine learning|robotic|signal processing|telecommun|cybernetic|fluid|aerospace|"
            r"civil|\b(eee|ece|eecs|ee)\b|ingenier|ingegneria|energy|materials|technical|"
            r"polytechn|informatique|informatica|engineering technolog"
        ),
    ),
    (
        P,
        (
            r"physics|physical|chemi|astronom|geoscien|earth science|geophys|optics|photonic|"
            r"fisica|physik"
        ),
    ),
    (
        O,
        (
            r"econom|business|management|social|psycholog|law|education|humanit|philosoph|"
            r"linguist|media|sport|history|political|finance"
        ),
    ),
]
RULES = [(g, re.compile(p, re.IGNORECASE)) for g, p in RULES]

# Units, most specific first: a part of an affiliation is a unit if it has one
# of these words
UNIT_RANK = [
    re.compile(
        (
            r"\b(department|dept|division|section|clinic|klinik|dipartimento|departamento|"
            r"département|abteilung|laboratory of|unit)\b"
        ),
        re.IGNORECASE,
    ),
    re.compile(
        (
            r"\b(institute|institut|instituto|istituto|school|faculty|fakultät|facultad|"
            r"college of)\b"
        ),
        re.IGNORECASE,
    ),
    re.compile(
        (
            r"\b(cent(er|re)|centro|zentrum|lab|laboratory|group|program|programme|chair)\b"
        ),
        re.IGNORECASE,
    ),
]
FACULTY = re.compile(r"faculty|fakultät|facultad|college", re.IGNORECASE)
# Words that do not tell institutions apart
STOP = {
    "university",
    "of",
    "the",
    "and",
    "hospital",
    "institute",
    "college",
    "de",
    "di",
    "la",
    "universitet",
    "universität",
    "universidad",
    "università",
    "school",
    "center",
    "centre",
    "medical",
    "national",
    "at",
    "for",
    "in",
    "technology",
    "research",
    "sciences",
    "science",
}

# A co-author's own main research field in OpenAlex to discipline
AUTHOR_FIELDS = {
    "Mathematics": M,
    "Computer Science": C,
    "Engineering": C,
    "Decision Sciences": C,
    "Physics and Astronomy": P,
    "Chemistry": P,
    "Materials Science": P,
    "Earth and Planetary Sciences": P,
    "Environmental Science": P,
    "Biochemistry, Genetics and Molecular Biology": B,
    "Agricultural and Biological Sciences": B,
    "Immunology and Microbiology": B,
    "Neuroscience": X,
    "Pharmacology, Toxicology and Pharmaceutics": X,
    "Medicine": K,
    "Nursing": K,
    "Health Professions": K,
    "Dentistry": K,
    "Psychology": O,
    "Social Sciences": O,
    "Economics, Econometrics and Finance": O,
    "Business, Management and Accounting": O,
    "Arts and Humanities": O,
}

KIND_ORDER = [
    "Universities",
    "Hospitals",
    "Research institutes",
    "Companies",
    "Institution unknown",
]


def tokens(text):
    """The words that tell an institution apart, for matching names."""
    return {
        t
        for t in re.findall(r"[a-zà-ÿ]+", name_key(text))
        if t not in STOP and len(t) > 2
    }


def names_institution(text, institution):
    inst = tokens(institution)
    return bool(inst) and len(inst & tokens(text)) >= max(1, len(inst) // 2)


def own_parts(affiliation, institution, strict=False):
    """The parts of an affiliation string (separated by ";") at the
    institution. Unless strict, a single part counts even if it does not name
    it (on the joint papers, OpenAlex has already tied it to the
    institution)."""
    parts = [p.strip() for p in affiliation.split(";") if p.strip()]
    mine = [p for p in parts if names_institution(p, institution)]
    return mine or (parts if len(parts) == 1 and not strict else [])


def units(part, institution):
    """(rank, unit name) for the units named in one part of an affiliation,
    leaving out the institution's own name."""
    inst = tokens(institution)
    out = []
    for seg in (s.strip() for s in part.split(",")):
        seg_tokens = tokens(seg)
        if not seg_tokens or (inst and seg_tokens <= inst | {"oslo", "copenhagen"}):
            continue
        for rank, pattern in enumerate(UNIT_RANK):
            if pattern.search(seg):
                out.append((rank, seg))
                break
    return out


def classify(text):
    """The discipline a unit's name points to, or ""."""
    for group, pattern in RULES:
        if pattern.search(text):
            return group
    return ""


def broad_faculty(name):
    """True for a whole faculty or college covering more than one discipline,
    such as "Faculty of Mathematics and Natural Sciences" or a faculty of
    medicine (clinical and basic); a faculty named after one discipline, such
    as "Faculty of Mathematics", is as good as a department."""
    if not FACULTY.search(name):
        return False
    groups = {g for g, pattern in RULES if pattern.search(name)}
    mixed = re.search(r"\band\b|,|&|\bund\b|\by\b|\be\b", name, re.IGNORECASE)
    medical = re.search(r"medicine|medical|health", name, re.IGNORECASE)
    return len(groups) != 1 or bool(mixed) or bool(medical)


def confidence(name):
    """high, medium or low for a unit's name."""
    if FACULTY.search(name):
        return "low" if broad_faculty(name) else "high"
    return "high" if UNIT_RANK[0].search(name) else "medium"


def best_unit(texts, institution, strict=False):
    """(unit, discipline, confidence) for the most frequent unit of the most
    specific kind with a discipline, in affiliation texts at the
    institution."""
    candidates = Counter()
    for text in texts:
        for part in own_parts(text, institution, strict):
            found = units(part, institution)
            if found:
                best = min(rank for rank, _ in found)
                for rank, name in found:
                    if rank == best:
                        candidates[name] += 1
    for name, _ in candidates.most_common():
        group = classify(name)
        if group:
            return name, group, confidence(name)
    return "", "", ""


def orcid_unit(employments, institution, since):
    """(department, discipline, confidence) from ORCID employments at the
    institution that lasted into the year since or later, most recent
    first."""
    at = [
        e
        for e in employments
        if names_institution(e["organisation"], institution)
        and (not e["end"] or int(e["end"]) >= since)
    ]
    at.sort(key=lambda e: e["start"] or "9999", reverse=True)
    for e in at:
        group = classify(e["department"]) if e["department"] else ""
        if group:
            return e["department"], group, confidence(e["department"])
    return "", "", ""


def discipline(
    joint, employments, own, author_field, institution, since, institution_field=""
):
    """(discipline, evidence, source, uncertain) for a co-author. joint are
    the affiliation texts on their papers with the centre at the institution,
    employments their ORCID employments, own the affiliation texts on their
    other papers, author_field their main research field in OpenAlex and
    institution_field the field of the whole institution, if it has one."""
    paper = best_unit(joint, institution)
    if not paper[1] and joint:
        group = classify(" ; ".join(joint))
        if group:
            # No unit: show the most frequent affiliation text instead
            paper = (Counter(joint).most_common(1)[0][0], group, "medium")
    orcid = orcid_unit(employments, institution, since)
    papers = best_unit(own, institution, strict=True)
    # In order of preference: (source, (unit, discipline, confidence))
    for source, (unit, group, conf), wanted in [
        ("publications with the centre", paper, "high"),
        ("ORCID", orcid, "high"),
        ("their other publications", papers, "high"),
        ("the institution", ("", institution_field, "high"), "high"),
        ("publications with the centre", paper, "medium"),
        ("their other publications", papers, "medium"),
        ("ORCID", orcid, "low"),
        ("publications with the centre", paper, "low"),
        ("their other publications", papers, "low"),
    ]:
        if group and conf == wanted:
            return group, unit, source, conf == "low"
    if author_field in AUTHOR_FIELDS:
        return (
            AUTHOR_FIELDS[author_field],
            author_field,
            "OpenAlex research field",
            True,
        )
    return O, "", "", True


def coauthors(
    affiliations,
    start,
    merges=None,
    exclusions=(),
    people=None,
    colleagues=(),
    kinds=None,
    profiles=None,
    employments=None,
    own=None,
    corrections=None,
    fields=None,
):
    """The co-authors from start on with their kind of institution and, at
    universities, discipline: [{"id", "name", "institution", "country",
    "kind", "discipline", "evidence", "source", "uncertain", "publications",
    "needs_other_papers"}], where id is the OpenAlex author ID (after person
    merges), else the name, and needs_other_papers says whether their other
    papers could help: neither their papers with the centre nor ORCID name a
    department.

    kinds is {institution: kind} (institution_kinds.csv); profiles is
    {OpenAlex author ID: {"orcid", "main_field"}}; employments and own are
    {OpenAlex author ID: [ORCID employments]} and {OpenAlex author ID:
    [affiliation texts on their own papers]}; corrections is {co-author:
    row} from coauthor_corrections.csv, with the institution, department and
    discipline set by hand; fields is {institution: field} for research
    institutes and companies (institution_kinds.csv)."""
    merges, kinds, corrections = merges or {}, kinds or {}, corrections or {}
    fields = fields or {}
    profiles, employments, own = profiles or {}, employments or {}, own or {}
    fixed = {c: r["institution"] for c, r in corrections.items() if r["institution"]}
    found, country_of = main_institutions(
        affiliations, start, merges, exclusions, people, colleagues, fixed
    )
    # Each institution's type in OpenAlex, from all rows that name it
    types = defaultdict(Counter)
    for r in affiliations:
        if r["institution"]:
            types[merges.get(r["institution"], r["institution"])][r["type"]] += 1
    out = []
    for c, v in found.items():
        main = v["main"]
        at = [
            r
            for r in v["rows"]
            if r["institution"]
            and merges.get(r["institution"], r["institution"]) == main
        ]
        if not main:
            kind = "Institution unknown"
        else:
            typ = types[main].most_common(1)[0][0] if types[main] else ""
            kind = kinds.get(main) or KINDS.get(typ, "Research institutes")
        row = {
            "id": c,
            "name": v["name"],
            "institution": main,
            "country": country_of.get(main, ""),
            "kind": kind,
            "discipline": "",
            "evidence": "",
            "source": "",
            "uncertain": False,
            "publications": len({r["result_id"] for r in v["rows"]}),
            "needs_other_papers": False,
        }
        joint = [r["affiliation"] for r in at]
        if kind == "Hospitals":
            # A department or institute decides; else clinical medicine
            group, evidence, source, uncertain = discipline(
                joint, [], [], "", main, start
            )
            if uncertain:
                group, evidence, source, uncertain = K, "", "the institution", False
        elif kind == "Institution unknown":
            group, evidence, source, uncertain = O, "", "", True
        else:
            row["needs_other_papers"] = (
                best_unit(joint, main)[2] != "high"
                and orcid_unit(employments.get(c, []), main, start)[2] != "high"
            )
            # c is the OpenAlex author ID (after person merges), else a name
            group, evidence, source, uncertain = discipline(
                joint,
                employments.get(c, []),
                own.get(c, []),
                profiles.get(c, {}).get("main_field", ""),
                main,
                start,
                fields.get(main) or (classify(main) if kind != "Universities" else ""),
            )
        fix = corrections.get(c, {})
        if fix.get("discipline"):
            group, source, uncertain = fix["discipline"], "set by hand", False
            evidence = fix.get("department") or evidence
        elif fix.get("department"):
            found_group = classify(fix["department"])
            if found_group:
                group, evidence = found_group, fix["department"]
                source, uncertain = "set by hand", False
        row.update(
            discipline=group, evidence=evidence, source=source, uncertain=uncertain
        )
        out.append(row)
    out.sort(key=lambda r: (KIND_ORDER.index(r["kind"]), r["discipline"], r["name"]))
    return out


def clean_department(name, institution):
    """A department's name without a leading footnote letter, anything after
    a ";" (such as an Oxford college) or the institution's name and what
    follows it (as in "Department of Mathematics University of Oslo Oslo")."""
    name = re.sub(r"^[a-z0-9]\s+(?=[A-Z])", "", name.strip()).split(";")[0]
    if institution:
        name = re.split(re.escape(institution), name, flags=re.IGNORECASE)[0]
    return name.strip(" ,")


def department_key(name):
    """Department names compared without case, punctuation, a leading
    footnote letter or the abbreviation "Dept."."""
    name = re.sub(r"^[a-z0-9]\s+(?=[A-Z])", "", name.strip())
    name = re.sub(r"\bdept\b\.?", "department", name, flags=re.IGNORECASE)
    return " ".join(re.findall(r"\w+", name_key(name)))


def group(people):
    """Institutions [name, country, kind, co-authors] and units by field
    [institution, country, department, field, co-authors, uncertain, source],
    most co-authors first. A unit is a department ("" when not known) at an
    institution; it is uncertain when all its co-authors' fields are."""
    institutions = {}
    for p in people:
        key = p["institution"] or "Institution unknown"
        i = institutions.setdefault(key, [p["institution"], p["country"], p["kind"], 0])
        i[3] += 1
    departments = {}
    for p in people:
        unit = p["evidence"] if p["source"] != "OpenAlex research field" else ""
        unit = clean_department(unit, p["institution"])
        key = (p["institution"], department_key(unit), p["discipline"])
        d = departments.setdefault(
            key, {"names": Counter(), "n": 0, "uncertain": True, "sources": Counter()}
        )
        d["names"][unit] += 1
        d["n"] += 1
        d["uncertain"] &= p["uncertain"]
        d["sources"][p["source"]] += 1
    return (
        sorted(institutions.values(), key=lambda i: (-i[3], i[0])),
        sorted(
            (
                [
                    inst,
                    next(
                        (p["country"] for p in people if p["institution"] == inst), ""
                    ),
                    d["names"].most_common(1)[0][0],
                    discipline,
                    d["n"],
                    d["uncertain"],
                    d["sources"].most_common(1)[0][0],
                ]
                for (inst, _, discipline), d in departments.items()
            ),
            key=lambda d: (-d[4], d[0], d[2]),
        ),
    )
