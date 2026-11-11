"""Regression test for refresh.sh.

Rebuilding everything from the saved data (refresh.sh --no-fetch, in a copy
of this repository and of the co-author data) must reproduce the committed
files exactly, apart from the date the pages were generated. A difference
means that a change to the code changes the pages or the data, which should
then be rebuilt and committed together with it. Skipped without the
co-author data (see ../nva/coauthor_data.py).
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "nva"))
import coauthor_data

GENERATED = re.compile(r'"generated": "\d{4}-\d{2}-\d{2}"')


def tracked_files():
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [f for f in out.splitlines() if (ROOT / f).is_file()]


def normalised(path):
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_bytes()
    return GENERATED.sub('"generated": ""', text)


@pytest.mark.skipif(
    not coauthor_data.available(),
    reason="needs the co-author data (see nva/coauthor_data.py)",
)
def test_rebuild_from_saved_data_changes_nothing(tmp_path):
    repo, data = tmp_path / "repo", tmp_path / "data"
    files = tracked_files()
    for f in files:
        (repo / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, repo / f)
    shutil.copytree(coauthor_data.ROOT, data, ignore=shutil.ignore_patterns(".git"))
    saved = sorted(p.relative_to(data) for p in data.rglob("*.csv"))

    result = subprocess.run(
        ["bash", "refresh.sh", "--no-fetch"],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHON": sys.executable, "CENTRE_DATA": str(data)},
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Key figures" in result.stdout

    changed = [f for f in files if normalised(repo / f) != normalised(ROOT / f)]
    changed += [
        f"co-author data: {f}"
        for f in saved
        if normalised(data / f) != normalised(coauthor_data.ROOT / f)
    ]
    assert changed == []
