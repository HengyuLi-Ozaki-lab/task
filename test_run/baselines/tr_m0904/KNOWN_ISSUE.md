# tr_m0904 known issue: environment-dependent drift

The committed baseline `metrics.json` cannot be reproduced byte-for-byte on
the current dev environment. The drift is **NOT** caused by any tr/eq source
commit since `a361df2d` (the documented baseline-generation commit) — verified
by full-tree bisect 2026-04-19.

## Symptoms
- 308 mismatches at 1e-10 tolerance
- rel_err ~3e-6 to 8e-6 in AJ/QP/RT (per-cell)
- rel_err ~7e-5 in volume integrals (BETA0/ALI/BETAA/WPT)
- rel_err ~1e-2 in TAUE (amplified via WPT/(PINT-WPDOT) cancellation)
- RN (density) is bit-exact identical → particle solver fine

## What was ruled OUT (with full clean rebuild bisect)
- tr Phase 4 (0909933d trexec.f90 GOTO cleanup)
- tr Phase 5 (TRCFDW/TRCFNC/TRCFET/TRCFAD module extracts)
- eq Phase F-4 (.f → .f90 conversion; eqbpsd.f90 typo fixed in PR #109)
- NCLASS path (MDNCLS=0 still drifts identically)
- NBI path (PNBR0=0 still drifts; in fact worse — NBI heating partially
  cancels the underlying drift)

## Suspected cause
External library state (bpsd / libgrf / lapack / gfortran) differs between
the machine where baseline was generated and the current dev machine.
Verified 2026-04-19:
- bpsd: HEAD = abdeb024 (2025-09-14), libbpsd.a mtime Jan 7 — unchanged this session
- task/lib/: only PIC variants added recently, no numerics change
- gfortran: 13.3.0
- lapack: project-internal `nolapack.f` shim

## Recommended action (deferred)
Re-generate the baseline on a known-good build environment and embed
build-environment metadata (gfortran version, libbpsd commit hash,
lapack source hash) in the baseline JSON so future drift can be diagnosed.
This was the same approach used for PR #105 (ti) and PR #107 (eq_jt60).

Until then, `tr_m0904` is a known FAIL.
