import coauthor_fields as cf


def row(rid, author, institution, affiliation, type_="education", author_id=""):
    """An openalex_affiliations.csv row for a co-author."""
    return {
        "result_id": rid,
        "year": "2023",
        "author": author,
        "openalex_author_id": author_id,
        "investigator": "",
        "investigators": "Ann A",
        "institution": institution,
        "ror": "",
        "country": "NO",
        "type": type_,
        "affiliation": affiliation,
    }


def test_rules():
    assert cf.classify("Department of Mathematics") == cf.M
    assert cf.classify("Division of Physiology") == cf.X
    assert cf.classify("Department of Neurosurgery") == cf.K
    assert cf.classify("Department of Family Medicine") == cf.K
    assert cf.classify("Department of Biosciences") == cf.B
    assert cf.classify("Department of Physics") == cf.P
    assert cf.classify("Department of Psychology") == cf.O
    # Engineering wins over the life-science word in its name
    assert (
        cf.classify("Department of Bioengineering and Quantitative Biosciences") == cf.C
    )
    assert cf.classify("Department of ICT") == cf.C
    assert cf.classify("Department of EEE") == cf.C
    assert cf.classify("Rectorate") == ""


def test_faculties():
    # A faculty named after one discipline is as good as a department
    assert cf.confidence("Faculty of Mathematics") == "high"
    assert cf.confidence("Faculty of Electrical Engineering") == "high"
    # Several disciplines, or medicine (clinical or basic), are uncertain
    assert cf.confidence("Faculty of Mathematics and Natural Sciences") == "low"
    assert cf.confidence("Faculty of Medicine") == "low"
    assert cf.confidence("Kirksville College of Osteopathic Medicine") == "low"
    assert cf.confidence("Department of Physics") == "high"
    assert cf.confidence("Center for Integrative Neuroplasticity") == "medium"


def test_affiliation_parts_at_the_institution():
    text = (
        "Department of Physics, University of Oslo; Department of Radiology, Haukeland"
    )
    assert cf.own_parts(text, "University of Oslo") == [
        "Department of Physics, University of Oslo"
    ]
    # A single part counts on the joint papers, not on the person's own papers
    assert cf.own_parts(
        "Neurology, Cleveland Clinic Ohio", "A.T. Still University"
    ) == ["Neurology, Cleveland Clinic Ohio"]
    assert (
        cf.own_parts("Neurology, Cleveland Clinic Ohio", "A.T. Still University", True)
        == []
    )
    assert cf.units(
        "Department of Physics, University of Oslo", "University of Oslo"
    ) == [(0, "Department of Physics")]


def test_discipline_sources_in_order():
    uio = "University of Oslo"
    orcid = [
        {
            "organisation": uio,
            "department": "Department of Mathematics",
            "start": "2015",
            "end": "",
        }
    ]
    # A department on the joint papers comes first
    assert cf.discipline(
        ["Department of Physics, University of Oslo"], orcid, [], "Medicine", uio, 2016
    ) == (cf.P, "Department of Physics", "publications with the centre", False)
    # Then ORCID, then the person's own papers
    assert cf.discipline(["University of Oslo"], orcid, [], "", uio, 2016)[:3] == (
        cf.M,
        "Department of Mathematics",
        "ORCID",
    )
    own = ["Department of Informatics, University of Oslo"]
    assert cf.discipline(["University of Oslo"], [], own, "", uio, 2016)[:3] == (
        cf.C,
        "Department of Informatics",
        "their other publications",
    )
    # An ORCID employment that ended before the period does not count; with
    # nothing else, the co-author counts as other, uncertain
    ended = [{**orcid[0], "end": "2014"}]
    assert cf.discipline(["University of Oslo"], ended, [], "", uio, 2016) == (
        cf.O,
        "",
        "",
        True,
    )
    # At a research institute, the institution's field comes after a named
    # department but before an institute or centre
    negri = "Mario Negri"
    assert cf.discipline(["Mario Negri"], [], [], "", negri, 2016, cf.X)[:3] == (
        cf.X,
        "",
        "the institution",
    )
    assert cf.discipline(
        ["Department of Biomedical Engineering, Mario Negri"],
        [],
        [],
        "",
        negri,
        2016,
        cf.X,
    )[:3] == (
        cf.C,
        "Department of Biomedical Engineering",
        "publications with the centre",
    )
    # The field of their research in OpenAlex only as a last, uncertain resort
    assert cf.discipline(["University of Oslo"], [], [], "Engineering", uio, 2016) == (
        cf.C,
        "Engineering",
        "OpenAlex research field",
        True,
    )


def test_kinds_of_institution():
    affiliations = [
        row(
            "1",
            "Uni Person",
            "University of Oslo",
            "Department of Physics, University of Oslo",
        ),
        row(
            "1",
            "Hospital Person",
            "Oslo University Hospital",
            "Oslo University Hospital",
            "healthcare",
        ),
        row("1", "Non Profit", "Mario Negri", "Mario Negri", "nonprofit"),
        row("1", "In Company", "Philips", "Philips Research", "company"),
        row("1", "Q B", "QB3", "Department of Bioengineering, QB3", "nonprofit"),
        {**row("1", "No Place", "", ""), "type": ""},
    ]
    found = cf.coauthors(
        affiliations,
        2016,
        kinds={"QB3": "Universities"},
        fields={"Philips": cf.C},
    )
    by_name = {c["name"]: (c["kind"], c["discipline"], c["uncertain"]) for c in found}
    assert by_name == {
        "Uni Person": ("Universities", cf.P, False),
        "Q B": ("Universities", cf.C, False),
        # At a hospital with no department named: clinical medicine
        "Hospital Person": ("Hospitals", cf.K, False),
        # From the institution's name, and from its field set by hand
        "Non Profit": ("Research institutes", cf.O, True),
        "In Company": ("Companies", cf.C, False),
        "No Place": ("Institution unknown", cf.O, True),
    }


def test_corrections_set_institution_department_and_discipline():
    affiliations = [
        row(
            "1",
            "Somebody Else",
            "University of Oslo",
            "Department of Physics, University of Oslo",
        ),
        {**row("2", "Jensenius, Alexander Refsum", "", ""), "type": ""},
    ]
    corrections = {
        "jensenius, alexander refsum": {
            "institution": "University of Oslo",
            "department": "Department of Musicology, RITMO",
            "discipline": "Other",
        }
    }
    found = {
        c["name"]: c for c in cf.coauthors(affiliations, 2016, corrections=corrections)
    }
    j = found["Jensenius, Alexander Refsum"]
    # At the University of Oslo (a university, from the other row naming it)
    assert (j["institution"], j["country"], j["kind"]) == (
        "University of Oslo",
        "NO",
        "Universities",
    )
    assert (j["discipline"], j["evidence"], j["source"], j["uncertain"]) == (
        "Other",
        "Department of Musicology, RITMO",
        "set by hand",
        False,
    )


def test_people_are_grouped_into_institutions_and_departments():
    def person(
        institution, kind, evidence="", discipline="", source="", uncertain=False
    ):
        return {
            "institution": institution,
            "country": "NO",
            "kind": kind,
            "evidence": evidence,
            "discipline": discipline,
            "source": source,
            "uncertain": uncertain,
        }

    uio = "University of Oslo"
    people = [
        person(
            uio,
            "Universities",
            "Department of Mathematics",
            cf.M,
            "publications with the centre",
        ),
        person(uio, "Universities", "b Dept. of Mathematics", cf.M, "ORCID"),
        person(
            uio,
            "Universities",
            "Department of Mathematics University of Oslo Oslo Norway",
            cf.M,
            "ORCID",
        ),
        person(
            uio, "Universities", "Engineering", cf.C, "OpenAlex research field", True
        ),
        person(
            "Oslo University Hospital",
            "Hospitals",
            "Department of Radiology",
            "Hospitals",
        ),
        person("", "Institution unknown", "", cf.O, "", True),
    ]
    institutions, departments = cf.group(people)
    assert institutions == [
        [uio, "NO", "Universities", 4],
        ["", "NO", "Institution unknown", 1],
        ["Oslo University Hospital", "NO", "Hospitals", 1],
    ]
    # Spellings of one department count together; a field from OpenAlex is
    # no department, and its classification is uncertain
    assert departments == [
        [uio, "NO", "Department of Mathematics", cf.M, 3, False, "ORCID"],
        ["", "NO", "", cf.O, 1, True, ""],
        [
            "Oslo University Hospital",
            "NO",
            "Department of Radiology",
            "Hospitals",
            1,
            False,
            "",
        ],
        [uio, "NO", "", cf.C, 1, True, "OpenAlex research field"],
    ]


def test_hospital_departments_decide_their_field():
    affiliations = [
        row("1", "Clinician", "OUH", "Department of Neurosurgery, OUH", "healthcare"),
        row("1", "Geneticist", "OUH", "Department of Genetics, OUH", "healthcare"),
        row(
            "1",
            "Researcher",
            "OUH",
            "Institute for Experimental Medical Research, OUH",
            "healthcare",
        ),
        row("1", "Somebody", "OUH", "OUH", "healthcare"),
    ]
    found = {
        c["name"]: (c["discipline"], c["uncertain"])
        for c in cf.coauthors(affiliations, 2016)
    }
    assert found == {
        "Clinician": (cf.K, False),
        "Geneticist": (cf.B, False),
        "Researcher": (cf.X, False),
        "Somebody": (cf.K, False),
    }
