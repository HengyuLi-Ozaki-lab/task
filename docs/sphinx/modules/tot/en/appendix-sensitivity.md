# Appendix: Input ↔ Output Correspondence

Summary of `tot`'s input → output relationships. Limited to **(1)
algebraic relationships** and **(2) physics scaling**. Because `tot` is
an aggregation of other modules, refer to each module's
`appendix-sensitivity.md` for fine-grained sensitivity.

```{admonition} Legend
:class: note

- **↑**: increasing the input increases the output
- **↓**: increasing the input decreases the output
- **=**: equal to / directly determined by the input
- **~**: approximately holds
```

## 1. Algebraic / directly determined relationships

| Input | Affected output | Relation | Notes |
|---|---|---|---|
| `tr:DT × tr:NTMAX` | `state.scalars["T"]` | = | Final time |
| `tr:NSMAX` | `state.nsmax` | = | tr's species count |
| `Tot()` succeeds | `state.<mod>_present` | = 1 | Sub-module initialised correctly |
| Sub-module fails | `state.<mod>_present` | = 0 | Prefix is unusable |

## 2. Known physics scaling trends

`tot`'s outputs are basically obtained **via `tr`**, so `tr`'s
sensitivities apply directly. For details, see `tr`'s sensitivity
appendix (`docs/sphinx/modules/tr/en/appendix-sensitivity.md`).

### 2.1 Device parameters (`eq:RR`, `eq:BB`, ...)

Changing the device through `eq:` prefixes alters the equilibrium, which
in turn alters tr's flux-surface info, so eventually every entry in
`state.scalars` changes.

| Input | Affected output | Direction | Notes |
|---|---|---|---|
| `eq:RR` ↑ | `state.scalars["WPT"]` | ↑ | Volume-proportional (same as `tr`) |
| `eq:BB` ↑ | `state.scalars["BETAN"]` | ↓ | $\beta \propto 1/B^2$ |
| `eq:RIP` ↑ | `state.scalars["Q0"]`, `Q[surf]` | ↓ | $q \propto B/I$ |

### 2.2 Effect of integrated heating modules

`tot`'s defining feature is that **heating is integrated dynamically**.

| Input | Affected output | Direction | Physical basis |
|---|---|---|---|
| `tr:MDLNB = 1` (NBI ON) | `state.scalars["WPT"]` | ⊕↑ | Heating power added (computed inside tr) |
| `wr:RF`, `wr:RPI` set | `state.scalars["WPT"]` | ⊕↑ | Ray-tracing result is fed back to tr |
| `fp:MODEL_NBI = 1` (fp NBI analysis) | `state.scalars["AJT"]` (NB drive) | ⊕↑ | fp's Fokker–Planck result is fed back to tr |

### 2.3 Coupling presence/absence changes results

| Operating mode | Effect |
|---|---|
| **eq + tr only** (no wr/fp) | Same result as `tr` alone |
| **eq + tr + wr** | RF heating is reflected dynamically |
| **eq + tr + wr + fp** | RF heating + fast-ion distribution are both reflected |

Adding more sub-modules **improves physics fidelity but increases
compute cost**, so pick what you need for the goal at hand.

## Detailed sensitivities per module

`tot` does not change the underlying physics of the individual modules,
so refer to:

- `tr` input ↔ output: `docs/sphinx/modules/tr/en/appendix-sensitivity.md`
- `eq` input ↔ output: `docs/sphinx/modules/eq/en/appendix-sensitivity.md`
- `ti` input ↔ output: `docs/sphinx/modules/ti/en/appendix-sensitivity.md`
- `fp` input ↔ output: `docs/sphinx/modules/fp/en/appendix-sensitivity.md`
- `wr` input ↔ output: `docs/sphinx/modules/wr/en/appendix-sensitivity.md`
- `wrx` input ↔ output: `docs/sphinx/modules/wrx/en/appendix-sensitivity.md`

## Practical guidance

When you want to push a `tot` output toward a target value:

- **Increase BETAN** → raise `tr:` `PN`, `PT`, or lower `eq:BB` (see
  tr's sensitivity appendix for details)
- **Compare RF heating effects** → toggle the `wr:` ray tracing on/off
- **Add fast-ion analysis** → set `fp:` parameters and fp will be run
  automatically

For quantitative sensitivity, run a sweep — the `totlib_sweep`
(Layer 4) framework is available for this.
