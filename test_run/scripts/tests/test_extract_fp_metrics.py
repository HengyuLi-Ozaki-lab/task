import json
import subprocess
import sys
from pathlib import Path

SCRIPT  = Path(__file__).parent.parent / "extract_fp_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_fp_regress.dat"


def run_extract(dump_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_extracts_scalars():
    data = run_extract(FIXTURE)
    assert data["NRMAX"] == 2
    assert data["NSAMAX"] == 2
    assert data["NPMAX"] == 10
    assert data["NTHMAX"] == 10
    assert data["NTG2"] == 3
    assert data["scalars"]["TIMEFP"] == 2.0e-3


def test_extracts_profile_rows():
    data = run_extract(FIXTURE)
    prof = data["profile"]
    # NRMAX * NSAMAX = 4 rows
    assert len(prof) == 4
    row = prof[0]
    assert row["NR"] == 1 and row["NSA"] == 1
    assert abs(row["RNT"] - 0.7) < 1e-15
    assert abs(row["RJT"] - 15.451) < 1e-13
    last = prof[-1]
    assert last["NR"] == 2 and last["NSA"] == 2
    assert abs(last["RWT"] - 1.8) < 1e-15


def test_rejects_incomplete_dump(tmp_path):
    incomplete = tmp_path / "bad.dat"
    incomplete.write_text("# TASK/FP regression dump (format v1)\nNRMAX=1\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(incomplete)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_rejects_row_count_mismatch(tmp_path):
    bad = tmp_path / "bad.dat"
    bad.write_text(
        "# TASK/FP regression dump (format v1)\n"
        "NRMAX=2\nNSAMAX=2\nNPMAX=10\nNTHMAX=10\nNTG2=1\n"
        "TIMEFP=1.0000000000000000E-03\n"
        "# profile columns: NR NSA RNT RWT RTT RJT RPCT RPWT (at NTG=NTG2)\n"
        "    1   1  1.0E+00  1.0E+00  1.0E+00  1.0E+00  1.0E+00  1.0E+00\n"
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(bad)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
