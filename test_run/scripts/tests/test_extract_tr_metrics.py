import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "extract_tr_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_tr_regress.dat"


def run_extract(dump_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_extracts_scalars():
    data = run_extract(FIXTURE)
    assert data["NT"] == 100
    assert data["NRMAX"] == 2
    assert data["NSMAX"] == 2
    assert data["scalars"]["T"] == 2.0
    assert data["scalars"]["WPT"] == 41.13
    assert data["scalars"]["Q0"] == 0.579
    assert "BETA0" in data["scalars"]
    assert "ALI" in data["scalars"]


def test_extracts_profile_rows():
    data = run_extract(FIXTURE)
    prof = data["profile"]
    assert len(prof) == 2
    row = prof[0]
    assert row["NR"] == 1
    assert len(row["RN"]) == 2
    assert len(row["RT"]) == 2
    assert row["RN"][0] == 0.7
    assert row["AJ"] == 15.451
    assert row["QP"] == 0.579


def test_rejects_incomplete_dump(tmp_path):
    incomplete = tmp_path / "bad.dat"
    incomplete.write_text("# TASK/TR regression dump (format v1)\nNT=1\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(incomplete)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
