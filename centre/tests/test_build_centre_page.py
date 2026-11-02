import re

import build_centre_page as bcp


def aff(rid, year, author, institution, country="NO", investigator="", author_id=""):
    return {
        "result_id": rid,
        "year": year,
        "author": author,
        "openalex_author_id": author_id,
        "investigator": investigator,
        "institution": institution,
        "country": country,
    }


def test_key_figures():
    pub_years = {"1": 2025, "2": 2022, "3": 2017, "4": 2010}
    affiliations = [
        # Investigators are not co-authors
        aff("1", "2025", "Ann A", "University of Bergen", investigator="Ann A"),
        # Carl is at Charité twice and UiO once: main institution Charité
        aff("1", "2025", "Carl C", "Charité", "DE", author_id="A1"),
        aff("2", "2022", "Carl C", "Charité", "DE", author_id="A1"),
        aff("2", "2022", "Carl C", "University of Oslo", author_id="A1"),
        # A Simula colleague is neither a co-author nor a collaborating institution
        aff("2", "2022", "Sim S", "Simula Research Laboratory", author_id="A2"),
        # Merged and excluded affiliations
        aff("3", "2017", "Geir R", "Sørlandet Hospital Arendal", author_id="A3"),
        aff(
            "3",
            "2017",
            "Ricardo Ruíz‐Baier",
            "Sechenov University",
            "RU",
            author_id="A4",
        ),
        aff(
            "3", "2017", "Ricardo Ruíz‐Baier", "Monash University", "AU", author_id="A4"
        ),
    ]
    figures = bcp.key_figures(
        pub_years,
        affiliations,
        [2024, 2021, 2016],
        merges={"Sørlandet Hospital Arendal": "Sørlandet sykehus"},
        exclusions=[("Ricardo Ruiz-Baier", "Sechenov University")],
    )
    counts = {
        y: {k: v for k, v in f.items() if k != "lists"} for y, f in figures.items()
    }
    assert counts[2024] == {
        "publications": 1,
        "coauthors": 1,
        "institutions": 1,
        "countries": 1,
    }
    assert counts[2021] == {
        "publications": 2,
        "coauthors": 1,
        "institutions": 1,
        "countries": 1,
    }
    # Since 2016: Charité (DE), Sørlandet sykehus (NO), Monash (AU)
    assert counts[2016] == {
        "publications": 3,
        "coauthors": 3,
        "institutions": 3,
        "countries": 3,
    }

    # The lists behind the numbers, since 2021
    lists = figures[2021]["lists"]
    assert lists["publications"] == ["1", "2"]
    assert lists["coauthors"] == [
        ["Carl C", "Charité", "DE", ["1", "2"]],
    ]
    # Simula is not a collaborating institution
    assert lists["institutions"] == [["Charité", "DE", [0]]]


def test_author_lists_and_et_al():
    def c(rid, order, first, surname, pid=""):
        return {
            "cristin_result_id": rid,
            "order": str(order),
            "first_name": first,
            "surname": surname,
            "cristin_person_id": pid,
        }

    contributors = [c("1", 2, "Ann", "Berg", "11"), c("1", 1, "Carl", "Co")]
    contributors += [c("2", i, f"P{i}", "Person") for i in range(1, 8)]
    contributors += [c("3", 1, "Ann", "Berg", "11"), c("3", 2, "Tor", "Veit", "12")]
    authors = bcp.author_lists(contributors, {"11", "12"}, removed=[("3", "Tor Veit")])
    # In author order, investigators marked; a removed book editor is left out
    assert authors["1"] == [["Carl Co", False], ["Ann Berg", True]]
    assert authors["3"] == [["Ann Berg", True]]

    papers = {
        rid: {"year": "2022", "title": f"T{rid}", "doi": "", "nva_id": ""}
        for rid in "123"
    }
    records = bcp.publication_records(
        papers, {"Ann Berg": {"1", "2", "3"}}, 2016, authors
    )
    # All authors are kept in order; the page shows the first five and "et al."
    assert len(records["2"]["authors"]) == 7
    assert records["1"]["authors"] == [["Carl Co", False], ["Ann Berg", True]]


def test_surname_first_names_are_turned_round():
    contributors = [
        {
            "cristin_result_id": "1",
            "order": "1",
            "first_name": "Zikatanov,",
            "surname": "Ludmil T.",
            "cristin_person_id": "",
        }
    ]
    assert bcp.author_lists(contributors, set())["1"] == [
        ["Ludmil T. Zikatanov", False]
    ]


def test_page_loads_nothing_from_other_sites():
    # Fonts and scripts are served from ../site/assets, so that visitors'
    # browsers make no requests elsewhere (links the reader follows are fine)
    site = bcp.OUTPUT.parent
    for page in [bcp.TEMPLATE, bcp.OUTPUT]:
        html = page.read_text(encoding="utf-8")
        tags = [
            t for t in re.findall(r"<[a-z]+\b[^>]*>", html) if not t.startswith("<a ")
        ]
        loaded = [u for t in tags for u in re.findall(r'\b(?:src|href)="([^"]*)"', t)]
        assert "@import" not in html and "url(http" not in html, page.name
        for url in loaded:
            assert not re.match(r"[a-z]+:|//", url) or url.startswith("data:"), (
                page.name,
                url,
            )
            assert url.startswith("data:") or (site / url).exists(), (page.name, url)
    css = (site / "assets" / "fonts.css").read_text(encoding="utf-8")
    fonts = re.findall(r"url\(([^)]*)\)", css)
    assert fonts
    for url in fonts:
        assert (site / "assets" / url).exists(), url


def test_partners_page_counts_institutions_as_the_overview():
    import build_partners_page as bpp

    figures = bcp.collect()["figures"]
    partners = bpp.collect()
    assert sorted(bpp.SINCE) == sorted(bcp.SINCE)
    for start in bcp.SINCE:
        shown = [
            i
            for i in partners["institutions"]
            if any(start in ps for who in i["coauthors"] for _, ps in who)
        ]
        overview = figures[start]["lists"]["institutions"]
        assert sorted(i["name"] for i in shown) == sorted(r[0] for r in overview)
        assert len({i["country"] for i in shown}) == figures[start]["countries"]


def test_research_areas_count_coauthors_as_the_overview():
    import build_partners_page

    figures = bcp.collect()["figures"]
    data = build_partners_page.collect()
    for start in bcp.SINCE:
        institutions = data["areas"][start]["institutions"]
        assert sum(i[3] for i in institutions) == figures[start]["coauthors"]
        known = [i for i in institutions if i[0]]
        assert len(known) == figures[start]["institutions"]
