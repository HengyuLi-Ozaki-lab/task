# Known limitations and references

```{admonition} What this page covers
:class: note

A summary of what the `tr` library cannot do, plus pointers to
related transport codes and the upstream TASK group. The
limitations listed here are stable contracts of the current
implementation; the reference table summarises public
documentation for context.
```

---

## Known limitations

### Single instance per process

`Trlib` enforces one live instance per process — instantiating a
second `Trlib()` while another is still alive raises
`TrlibError`. The constraint exists because TR uses module-level
COMMON-block state that cannot be safely partitioned. For
parallelism, spawn separate processes (see {doc}`applications`).

For the user-facing details and the underlying weakref guard
(introduced in #171), see {ref}`faq-singleton`.

### Module-level state reset

After `tr_finalize` followed by another `tr_init` in the same
process, parts of the module-level Fortran state are not fully
reset. Tests that re-initialise should isolate by process
(`pytest --forked`) or use `multiprocessing` to spawn a fresh
worker. For details see {ref}`reinit-constraints`.

### Thread safety

`tr` is not thread-safe. Module-level COMMON-block state is
shared by every call to the library in the same process, so
concurrent calls from `threading.Thread` (or any other in-process
threading mechanism) race on that state. For parallel sweeps,
spawn separate processes — `multiprocessing.Pool` is the
recommended pattern, demonstrated by `sweep()` in
{doc}`applications`.

### Compile-time bounds (state buffer)

`TR_MAX_NRMAX = 500` and `TR_MAX_NSMAX = 8`, defined in
`tr/tr_api.h`, bound the dimensions of the **exported**
`tr_state_t` buffer that `tr_get_state` populates — i.e. the
`RN`, `RT`, `AJ`, `QP` arrays in {doc}`state`. They do *not*
bound the total resident set size of a TR process: TRCOMM
allocates many additional internal arrays at run time, and the
dynamically-linked libraries (BPSD, the matrix solver, etc.) add
further memory not captured by these constants. No RSS ceiling
is asserted here — measure for your own deployment if you need
it.

---

## References

### Original TASK publications

The TASK code suite (including `tr`) is developed by Prof.
A. Fukuyama's group (Kyoto University). The upstream sources
are at <https://github.com/ats-fukuyama>. For publications,
consult that group's bibliography directly — this page does not
list specific paper citations.

### Related transport codes

The table below summarises a few transport codes alongside
TASK/tr to help orient new users. The codes have varying access
models — some are open-source, some are collaboration-based, and
some are consortium-restricted. Non-TASK rows reflect public
documentation as of the page's date; for the authoritative scope
and access policy of each code, consult the linked sources.

| Code | Spatial | Time mode | Heating coverage | Access / URL |
|---|---|---|---|---|
| **TASK/tr** (this) | 1D radial | Predictive (time-evolving) | NB / EC / LH / ICRF source selectors registered via `MDLNB` / `MDLEC` / `MDLLH` / `MDLIC` | Open — <https://github.com/ats-fukuyama> |
| ASTRA | 1.5D | Predictive + interpretive | Modular | Collaboration-based — see upstream documentation |
| JETTO-SANCO | 1D transport + impurity | Predictive + interpretive | NB / EC / ICRH | EUROfusion-restricted — see upstream documentation |
| TRANSP | 1.5D | Interpretive primary; predictive available | NUBEAM, TORAY, etc. | Documentation: <https://transp.pppl.gov/>; source via PPPL collaboration |

The table is informative, not authoritative. For per-code
detail (e.g. specific transport-model libraries supported, exact
heating-module coverage, version histories), follow the linked
sources.
