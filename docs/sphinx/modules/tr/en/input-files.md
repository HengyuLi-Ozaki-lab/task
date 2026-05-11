# Input files

```{admonition} What this page covers
:class: note

A map of the supporting data files that TR can consume —
eqdata files (EQDSK and friends), ufiles (experimental
profile data), and the path / placement constraints. The
canonical formats are documented elsewhere; this page just
points at where TR reads them and what flags control the
reading.
```

---

## eqdata files (EQDSK and friends)

`MODELG ∈ {3, 5, 8, 9}` triggers TR's BPSD-side equilibrium
pull (`tr/trbpsd.f90:213`). All four values also drive an
actual external load on the `eq` side, but via different
loader routines:

- `MODELG = 3` or `MODELG = 9` → `EQRTSK` (TASK/EQ binary
  format)
- `MODELG = 5` → `EQDSKR` (community EQDSK format)
- `MODELG = 8` → `EQJAEAR`

The dispatch table lives at `eq/eqfile.f90:108-115`. So
`MODELG = 9` is not a no-op alias — it actually loads via
the same `EQRTSK` reader as `MODELG = 3`.

The path is set via `KNAMEQ` (string parameter); see
{doc}`parameter-setting` for how to set string params from
Python. The file is read on the `eq` side; `tr` only pulls
the resulting equilibrium / metric data via the BPSD
broker (`tr/trbpsd.f90:213-245` — the geometry-aware pull
is conditional on `MODELG`).

The canonical EQDSK format documentation lives in the `eq`
chapter and external sources (EQDSK is a community format
predating TASK). This page does NOT redocument the format
itself.

A working example file ships under
`test_run/test_output/tot_demo2014_short/eqdata.demo2014`,
the demo2014 baseline used by the Layer 1 equivalence
tests.

---

## ufiles (`MDLUF`)

A "ufile" is a community format for time-series experimental
profile data — density, temperature, q-profile snapshots,
etc. TR can ingest these to drive interpretive runs.

Reading is controlled by `MDLUF` (default `0` — OFF; set
to non-zero to enable). The default is verified at
`tr/trinit.f90:641-648`. `MDLUF` is exposed in
`tr/tr_param_registry.f90` and can be set from
`tr.set_param("MDLUF", ...)` at runtime.

**The directory parameters `KUFDIR` / `KUFDEV` / `KUFDCG`
are namelist-only.** They appear in the legacy `&trn`
namelist input at `tr/trparm.f90:108-112`, but they are
NOT exposed in `tr/tr_param_registry.f90` (the registry
has a "future additions" comment at
`tr/tr_param_registry.f90:184-186`). Setting them via
`tr.set_param_str` will fail. Users who need to point TR
at a non-default ufile directory must either:

- run from the legacy namelist-driven `tr2` driver, or
- set up the directory via Fortran-side defaults / source
  edit until these get added to the registry.

The reader chain is:

- `tr/trufile.f90:70-77` — dispatch stub, picks one of
  the next-level routines based on `MDLUF` and the
  scenario kind.
- `tr/tr_ufile_task.f90:7` — `TR_TIME_UFILE` /
  `TR_STEADY_UFILE` entry points.
- `tr/tr_ufile_topics.f90:7` — `TR_TIME_UFILE_TOPICS`
  per-topic decoders.

For most users running prescribed-profile or analytic-
geometry scenarios, ufiles are NOT needed — the default
`MDLUF = 0` is correct. The entry exists to point readers
at the chain when they encounter a research workflow that
does need experimental input.

---

## `trmodels/` and other model-side data

Some transport models embed lookup tables or coefficient
data (e.g. NCLASS-style modules). The codebase carries
these inline in the source rather than as separate runtime
files: `tr/trmodels.f90` calls compiled-in driver routines
(`mbgb_driver`, `mmm95_driver`, `mmm71_driver`) directly,
with no `OPEN` / `READ` from a runtime model-side
directory.

In practice this means **runtime external data is currently
limited to eqdata + ufiles only**. There is no
`trmodels/`-style runtime directory the library reads at
start-up.

---

## File placement and path constraints

The `eq` C-string interface caps `KNAMEQ` (and similar
string parameters) at 80 bytes. The constant is defined at
`python/eqlib/eqlib.py:39-41`, and the actual length
rejection (`EqlibInvalidParamError` when
`len(encoded) > max_bytes`) is at `:66-70`. The Fortran side
reads into `CHARACTER(LEN=80)`. The docstring at `:47-50`
says "up to 79 bytes" — this is stale; Python permits the
full 80. Treat the limit as **byte** rather than
"character" because the limit applies to encoded bytes,
not codepoints.

Recommended pattern: `chdir` to a working directory that
holds the eqdata file(s) and pass the bare filename. This
is what the existing `python/totlib/tests/test_pipeline_*`
files do.

Absolute paths longer than 80 bytes will fail at
parameter-set time, before `run()` is called; users will
see the error immediately rather than at run time.

---

## See also

- {doc}`parameter-setting` — how to set string parameters
  via the Python `set_param_str` interface.
- {doc}`limitations-and-references` — comparison with other
  open transport codes that consume similar files.
- {doc}`design` — the BPSD broker plumbing TR uses to
  receive `eq`'s output.
- {doc}`numerical-stability-and-diagnostics` — what to
  check at runtime when an eqdata load behaves unexpectedly.
