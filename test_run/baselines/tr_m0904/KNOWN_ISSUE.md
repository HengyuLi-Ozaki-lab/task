# tr_m0904 baseline note

This baseline was **regenerated 2026-04-19** on the current dev environment
because the previously-committed JSON (from a different machine/build) could
not be reproduced byte-for-byte here. Drift was 308 mismatches at
1e-10 tolerance, with TAUE rel_err ~1e-2 (amplified from per-cell ~3e-6).

The drift was empirically NOT caused by any tr/eq source commit since
`a361df2d` (the documented baseline-anchor) — full clean rebuild bisect on
2026-04-19 confirmed all candidate Phase 4-5 tr commits and Phase F-4 eq
commits (including the eqbpsd.f90 typo fixed in PR #109) reproduce the same
mismatches at every commit. External library state (gfortran build,
bpsd, lapack, etc.) is the suspected root cause. bpsd was verified
unchanged (HEAD `abdeb024`, libbpsd.a mtime Jan 7).

## Future work
Embed build-environment metadata (gfortran version, libbpsd commit hash,
LAPACK source, link map) into baseline JSON so regeneration is
auditable. Same recipe used by PR #105 (ti) and PR #107 (eq_jt60).
