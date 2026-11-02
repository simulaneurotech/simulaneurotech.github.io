import publication_relevance as pr


def work(title, abstract="", field="Medicine", subfield=""):
    return {
        "title": title,
        "primary_field": field,
        "primary_subfield": subfield,
        **pr.text_flags(title, abstract),
    }


def test_suggestions():
    assert (
        pr.suggest(work("Design of a self-powered IoT device", field="Engineering"))[0]
        == "drop"
    )
    assert (
        pr.suggest(work("Two-compartment modeling of tracer transport in the brain"))[0]
        == "keep"
    )
    # A misleading subfield does not drop physiological methods work
    assert (
        pr.suggest(
            work(
                "Existence of excitation waves",
                "A model of cardiomyocytes",
                subfield="Computer Networks and Communications",
            )
        )[0]
        == "keep"
    )
    # Wireless only in the abstract: review
    assert (
        pr.suggest(
            work(
                "Fast graph filters",
                "applied to wireless sensor networks",
                field="Computer Science",
            )
        )[0]
        == "review"
    )
    # Core methods field, such as general data mining: keep
    assert (
        pr.suggest(
            work("Coupled matrix and tensor factorizations", field="Computer Science")
        )[0]
        == "keep"
    )
    assert (
        pr.suggest(
            work(
                "Biomarkers of individual foods using multiway models",
                field="Biochemistry",
            )
        )[0]
        == "review"
    )
    assert (
        pr.suggest(
            work(
                "Oscillatory line source for water waves",
                field="Earth and Planetary Sciences",
            )
        )[0]
        == "drop"
    )
    # "radio-cephalic" is anatomy, not radio
    assert (
        pr.suggest(
            work(
                "Wall vibrations in a radio-cephalic fistula",
                "simulations of blood flow",
            )
        )[0]
        == "keep"
    )


def test_decision_overrides_suggestion():
    assert pr.relevant({"suggestion": "keep", "decision": ""})
    assert not pr.relevant({"suggestion": "review", "decision": ""})
    assert pr.relevant({"suggestion": "review", "decision": "keep"})
    assert not pr.relevant({"suggestion": "keep", "decision": "drop"})
