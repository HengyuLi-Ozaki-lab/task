# FAQ — `wrx` specifics

## Q1. What does `wrx` do?

`wrx` (Wave Ray eXtended) is a **beam tracing** solver — an extended
version of `wr` (geometric optics). It attaches **beam-shape information**
(curvature tensor, width, phase) to each ray and develops the propagation
of focused beams **analytically**.

Typical applications:

- **Focused ECRH beams** (e.g. ITER's Upper / Equatorial Launcher)
- High-accuracy analysis of **LH beams**
- Focal-point tracking of **gyrotron beams**

## Q2. When do I use `wr` vs `wrx`?

| Goal | Recommended |
|---|---|
| Quick estimate for ECRH/ECCD (peak position only) | `wr` |
| ECRH with focused beams where absorption-profile accuracy matters | **`wrx`** |
| Approximate beam spread with many rays | `wr` (NRAYMAX=10–50) |
| Precisely trace a beam with a single ray | **`wrx`** |
| Minimize compute time | `wr` |
| Physically accurate beam tracing | **`wrx`** |

If unsure, **start with `wr`** — and only switch to `wrx` if the result is
too coarse.

## Q3. Are results good enough with `NRAYMAX=1`?

**Yes.** The whole point of `wrx` is that the beam shape is tracked along
a single ray. You only need multiple rays when:

- Multiple physically distinct beams (upper + lower launcher, etc.)
- Mixed frequencies
- Comparing wave modes (O-mode vs X-mode)

For a single focused beam, `NRAYMAX=1` is fine.

## Q4. How do I choose `RBRADAIN`, `RCURVAIN`?

- **`RBRADAIN[i]`**: 1/e² beam width in metres. Typical ECRH gyrotrons
  are 2–5 cm; LH couplers are roughly 10–30 cm.
- **`RCURVAIN[i]`**: radius of curvature in metres. Positive = diverging,
  negative = focusing. It corresponds to the focal length of the
  focusing optics. For a diverging beam, set a large positive value
  (e.g. 1000).

Refer to the optics specification of your launcher hardware for details.

## Q5. The result does not match `wr`

Because `wrx` performs beam tracing, it is a physically different model
from `wr`, so **disagreement is normal**. To compare with similar
parameters:

- In `wrx`, set `RBRADAIN=0.001` (essentially zero width) — the result
  will be close to `wr`.
- In `wr`, use `NRAYMAX=50` or so to approximate a beam — the result
  will approach `wrx`.

Exact agreement is not expected.

## Q6. The result does not match `wrx2` (CLI version)

Run the regression test `wrxlib_equivalence`:

```bash
bash test_run/run_tests.sh wrxlib_equivalence
```

Tolerance is `1e-10`. If the deviation exceeds the tolerance, look for an
unregistered parameter.

## Q7. Rays stop midway / power is zero

Many of the same root causes as `wr`:

- `NSTPMAX` too small
- Reaching a cutoff
- Launch conditions that never reach a resonance (absorption point)

In `wrx`, an additional case is **the beam diverges so much that the
calculation cannot continue**. Adjust `RCURVAIN` (curvature) to suppress
the divergence.

## Q8. Should I run both `wr` and `wrx` tests?

Each module has its own equivalence test (`wrlib_equivalence`,
`wrxlib_equivalence`), so run both. CI runs them in parallel, so the
total time barely changes.
