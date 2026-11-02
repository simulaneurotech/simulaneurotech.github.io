"""Regression test for refresh.sh.

Rebuilding everything from the data in the repository (refresh.sh
--no-fetch, in a copy of the repository) must reproduce the committed files
exactly, apart from the date the pages were generated. A difference means
that a change to the code changes the pages or the data, which should then
be rebuilt and committed together with it.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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


def test_rebuild_from_saved_data_changes_nothing(tmp_path):
    files = tracked_files()
    for f in files:
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, tmp_path / f)

    result = subprocess.run(
        ["bash", "refresh.sh", "--no-fetch"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHON": sys.executable},
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Key figures" in result.stdout

    changed = [f for f in files if normalised(tmp_path / f) != normalised(ROOT / f)]
    assert changed == []
