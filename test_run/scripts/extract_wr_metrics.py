#!/usr/bin/env python3
"""Convert wr_regress.dat into a JSON for regression comparison.

Output schema:
    NRAYMAX, NSTPMAX, NRSMAX, NRLMAX, MODELG, MDLWRI, MDLWRQ, mode_beam (ints),
    scalars (dict[str,float]),
    rays    (list[dict] one per ray with NRAY, NSTP_END, pos_pwrmax_rs_nray,
             RAYS_END[9]),
    profile_rs (list[dict] one per minor-radius bin: NRS, pos_nrs, pwr_nrs),
    profile_rl (list[dict] one per major-radius bin: NRL, pos_nrl, pwr_nrl).

Note: per-ray pwrmax_rs_nray / pos_pwrmax_rl_nray / pwrmax_rl_nray are
intentionally *not* exposed; their initialization is incomplete in
wr/wrexecr.f90 (pre-existing). Will be added back in WR L-6.
"""
import argparse
import json
import re
import sys
from pathlib import Path


INT_KEYS = {
    "NRAYMAX", "NSTPMAX", "NRSMAX", "NRLMAX",
    "MODELG", "MDLWRI", "MDLWRQ", "mode_beam",
}
SCALAR_KEYS = {
    "RF", "RPI", "ZPI", "PHII", "RNZI", "RNPHII", "RKR0", "UUI",
    "pos_pwrmax_rs", "pwrmax_rs", "pos_pwrmax_rl", "pwrmax_rl",
}

RE_HDR_RAYS = re.compile(r"^#\s*rays:")
RE_HDR_RS   = re.compile(r"^#\s*minor radius profile:")
RE_HDR_RL   = re.compile(r"^#\s*major radius profile:")


def parse(path: Path) -> dict:
    lines = path.read_text().splitlines()
    out = {"scalars": {}, "rays": [], "profile_rs": [], "profile_rl": []}
    section = "header"
    for raw in lines:
        # Section-header lines (start with "#") are matched against the
        # original raw text BEFORE Fortran-comment stripping, since they
        # legitimately begin with "#". Data lines, however, may carry a
        # trailing Fortran "!" comment (e.g., wrregress.f90 emits
        # "1  -1   ! NSTP_END out of range" when NSTPMAX_NRAY is OOB);
        # strip those before tokenizing so int()/float() don't choke.
        line = raw.strip()
        if not line:
            continue
        if RE_HDR_RAYS.match(line):
            section = "rays"
            continue
        if RE_HDR_RS.match(line):
            section = "profile_rs"
            continue
        if RE_HDR_RL.match(line):
            section = "profile_rl"
            continue
        if line.startswith("#"):
            continue
        # Strip trailing Fortran "!" comment from data rows.
        line = line.split("!", 1)[0].strip()
        if not line:
            continue
        if section == "header":
            if "=" not in line:
                continue
            key, val = (s.strip() for s in line.split("=", 1))
            if key in INT_KEYS:
                out[key] = int(val)
            elif key in SCALAR_KEYS:
                out["scalars"][key] = float(val)
        elif section == "rays":
            parts = line.split()
            # Defensive: rows for rays whose NSTP_END is out of range carry
            # only "NRAY NSTP_END" (the Fortran writer omits the 9 RAYS_END
            # cols and emits a "! NSTP_END out of range" comment, already
            # stripped above). Record the partial row with an empty
            # RAYS_END so length checks still hold downstream.
            if len(parts) == 2:
                # Out-of-range row: record only the two ints and let the
                # comparator's "missing on both sides" branch handle the
                # absent terminal-sample fields symmetrically.
                out["rays"].append({
                    "NRAY": int(parts[0]),
                    "NSTP_END": int(parts[1]),
                })
                continue
            # Normal row: 2 ints (NRAY, NSTP_END) + 1 float
            # (pos_pwrmax_rs_nray) + 9 RAYS values
            # (RAYS(0:NEQ,end), NEQ=8 => 9 elements) = 12 cols.
            if len(parts) < 12:
                raise SystemExit(f"malformed ray row: {raw}")
            out["rays"].append({
                "NRAY": int(parts[0]),
                "NSTP_END": int(parts[1]),
                "pos_pwrmax_rs_nray": float(parts[2]),
                "RAYS_END": [float(x) for x in parts[3:12]],
            })
        elif section == "profile_rs":
            parts = line.split()
            if len(parts) != 3:
                raise SystemExit(f"malformed minor profile row: {raw}")
            out["profile_rs"].append({
                "NRS": int(parts[0]),
                "pos_nrs": float(parts[1]),
                "pwr_nrs": float(parts[2]),
            })
        elif section == "profile_rl":
            parts = line.split()
            if len(parts) != 3:
                raise SystemExit(f"malformed major profile row: {raw}")
            out["profile_rl"].append({
                "NRL": int(parts[0]),
                "pos_nrl": float(parts[1]),
                "pwr_nrl": float(parts[2]),
            })
    for k in ("NRAYMAX", "NSTPMAX", "NRSMAX", "NRLMAX"):
        if k not in out:
            raise SystemExit(f"missing header field: {k}")
    if len(out["rays"]) != out["NRAYMAX"]:
        raise SystemExit(
            f"ray count {len(out['rays'])} != NRAYMAX {out['NRAYMAX']}"
        )
    if len(out["profile_rs"]) != out["NRSMAX"]:
        raise SystemExit(
            f"profile_rs count {len(out['profile_rs'])} != NRSMAX {out['NRSMAX']}"
        )
    if len(out["profile_rl"]) != out["NRLMAX"]:
        raise SystemExit(
            f"profile_rl count {len(out['profile_rl'])} != NRLMAX {out['NRLMAX']}"
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", type=Path)
    args = ap.parse_args()
    json.dump(parse(args.dump), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
