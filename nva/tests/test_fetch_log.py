import fetch_log


def test_no_file_means_no_dates(tmp_path):
    assert fetch_log.read(tmp_path / "fetched.csv") == {}


def test_recording_one_source_keeps_the_others(tmp_path):
    path = tmp_path / "fetched.csv"
    fetch_log.record(path, "openalex", "2026-11-02")
    fetch_log.record(path, "simula_projects", "2026-10-30")
    fetch_log.record(path, "openalex", "2026-11-09")
    assert fetch_log.read(path) == {
        "openalex": "2026-11-09",
        "simula_projects": "2026-10-30",
    }
    # Sorted by source, so that the file changes only where a date does
    assert path.read_text(encoding="utf-8").splitlines() == [
        "source,fetched",
        "openalex,2026-11-09",
        "simula_projects,2026-10-30",
    ]


def test_records_today_by_default(tmp_path):
    path = tmp_path / "fetched.csv"
    fetch_log.record(path, "nva_publications")
    today = fetch_log.datetime.date.today().isoformat()
    assert fetch_log.read(path) == {"nva_publications": today}
