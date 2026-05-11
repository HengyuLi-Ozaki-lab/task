# The `with` Context Manager

`Tot` follows the same context-manager design as `tr` / `eq`. This page
focuses on the aspects that are specific to tot. For the general meaning
of the `with` statement and common pitfalls, see also the `tr` module's
context-manager page (`docs/sphinx/modules/tr/en/context-manager.md`).

## Minimal usage

```python
from totlib import Tot

with Tot() as tot:
    tot.set_param("eq:RR", 6.5)
    tot.set_param("tr:NSMAX", 2)
    tot.run(ntmax=10)
    state = tot.get_state()
# ← tot_finalize fires the moment the block exits
```

## tot-specific points to keep in mind

### All sub-modules are initialised together

Constructing `Tot()` **initialises eq / tr / ti / fp / wr / wrx all at
once** internally. As a consequence:

- You cannot run a stand-alone `Trlib()`, `Wrxlib()`, etc. in parallel
  with `Tot()` — tot already holds those resources, so it would clash
- Memory consumption is larger than the simple sum of the stand-alone
  modules

### Sequential finalize when leaving `with`

When `__exit__` triggers `tot_finalize`, each sub-module is finalised in
sequence. The order is:

```
wr/wrx → fp → ti → tr → eq → pl
```

(LIFO: most recently initialised, first finalised.)

### Sub-module presence flags

You can verify the sub-modules loaded by `Tot()` using the
`state.tr_present`, `state.fp_present`, etc. flags. If they are all 1,
every module was initialised correctly (see {doc}`state`).

## Behaviour on exceptions

If an exception is raised inside the `with` block, `__exit__` still
calls `tot_finalize`, **resetting the state of every sub-module**. This
means:

- Large memory allocations (especially fp's 5D grid) are released
- The SAVE flags of every sub-module are reset
- The next `Tot()` session is unaffected

## Without `with` (not recommended)

```python
tot = Tot()                         # initialise all modules
try:
    tot.set_param("eq:RR", 6.5)
    tot.run(ntmax=10)
    state = tot.get_state()
finally:
    tot.close()                      # finalize all modules
```

`tot` allocates a lot of memory, so using `with` is **especially
important** here.
