# trlib — Python wrapper for TASK/TR

`trlib` is a thin `ctypes`-based Python wrapper around
`tr/libtrapi.so`, the in-process shared-library version of the TASK/TR
transport code. It lets scripts drive TR simulations from Python
without shelling out to the standalone `tr` / `tr2` binary or going
through namelist files.

## Overview

TASK/TR has two user-facing deliverables:

| | Traditional CLI | Library (Phase L) |
|---|---|---|
| Binary | `tr/tr2` | `tr/libtrapi.so` |
| Entry | interactive menu | 5 C ABI functions |
| I/O | namelist + ASCII output | in-memory state struct |
| Graphics | PGPlot / Fortran 90 graphics | excluded |
| Python | — | `python/trlib` |

The C ABI is defined in `tr/tr_api.h`; the Fortran backend
(`tr/tr_api.f90`, `tr/tr_param_registry.f90`) is unchanged Fortran that
is also linked into `tr2`. `python/trlib` only wraps the 5 C entry
points and marshals a `tr_state_t` struct into the pure-Python
`TrState` dataclass.

No third-party dependencies — Python 3.8+ stdlib only (`ctypes`,
`dataclasses`, `pathlib`, `os`). `numpy` is optional.

## Installation

Build the shared library once:

```bash
cd /path/to/task
make -C tr libtrapi.so
```

This produces `tr/libtrapi.so` with 5 exported symbols (`tr_init`,
`tr_run`, `tr_set_param`, `tr_get_state`, `tr_finalize`) plus PIC
variants of the dependent libraries (`lib*_pic.a`). The pre-existing
non-PIC `*.a` archives and the `tr2` binary are unchanged.

Put the wrapper on `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

Optionally point at a library file outside the repository:

```bash
export TRLIB_PATH=/custom/path/libtrapi.so
```

Library lookup order (first match wins): `TRLIB_PATH` env var,
`<repo>/tr/libtrapi.so`, `<repo>/lib/libtrapi.so`.

## Quick start

```python
from trlib import Trlib

with Trlib() as tr:
    tr.set_params(RR=8.5, RA=2.0, BB=5.3,
                  NSMAX=2, DT=0.1, NTSTEP=10)
    tr.set_param("PN[1]", 1.0)   # array element (1-origin)
    tr.set_param("PN[2]", 1.0)
    tr.run(ntmax=50)
    state = tr.get_state()

print(f"T={state.scalars['T']:.3f}  WPT={state.scalars['WPT']:.3f}")
```

See `examples/` for runnable scripts:

- `examples/quickstart.py` — smallest complete run
- `examples/parameter_sweep.py` — RR / BB grid
- `examples/state_dump.py` — single run, full `TrState.to_dict()` as JSON

## API reference

### `Trlib(lib_path: str | None = None)`

Context manager. `__enter__` calls `tr_init`; `__exit__` / `close()`
calls `tr_finalize`. Only one live instance per process is meaningful
(TR backend holds global COMMON-block state).

### `Trlib.set_param(name, value) -> None`

Set a single parameter. Use `"NAME[i]"` (1-origin) for array elements;
Python keyword arguments cannot contain brackets so array elements
must use `set_param`, not `set_params`.

### `Trlib.set_params(**kwargs) -> None`

Bulk-set **scalar** parameters. Raises `TrlibError` on keys containing
`__` (common array-syntax mistake).

### `Trlib.run(ntmax: int) -> None`

Advance the simulation by `ntmax` steps. `ntmax=0` is a valid no-op
used by the smoke tests.

### `Trlib.get_state() -> TrState`

Snapshot current TRCOMM scalars and `[0:nrmax][0:nsmax]` profile
arrays into a `TrState` dataclass. Trailing padding (up to
`TR_MAX_NRMAX=500` / `TR_MAX_NSMAX=8`) is ignored.

### `Trlib.close() -> None`

Idempotent. The context manager calls this automatically.

## Supported parameters

The registry below reflects `tr/tr_param_registry.f90` at Phase L-3.
Add to it by extending that Fortran `SELECT CASE`; no Python change
is required — the wrapper forwards names verbatim.

| Group | Names | Notes |
|---|---|---|
| Geometry / device | `RR`, `RA`, `RKAP`, `RDLT`, `BB`, `PHIA` | scalar doubles |
| Plasma (arrays, 1..NSMM) | `PA[i]`, `PZ[i]`, `PN[i]`, `PNS[i]`, `PT[i]`, `PTS[i]` | 1-origin index |
| Plasma scalars | `NSMAX` | cast to INT |
| Current | `RIPS`, `RIPE` | |
| Time evolution | `DT`, `NTMAX`, `NTSTEP`, `EPSLTR`, `LMAXTR` | int-typed coerced |
| Transport switches | `MDLKAI`, `MDLETA`, `MDLAD`, `MDLAVK`, `CHP`, `CK0`, `CK1` | |
| Transport arrays | `CDW[i]` | |
| Module switches | `MDLNB`, `MDLEC`, `MDLLH`, `MDLIC`, `MDLPEL`, `MDLJBS`, `MDLST`, `MDLNF`, `MDLUF` | |

Unknown names return ierr=1 (raised as `TrlibParamError`).

## `TrState` fields

Matches `tr_state_t` in `tr/tr_api.h`. Full dict layout is available
via `state.to_dict()` (JSON-serialisable; matches the Phase 0 baseline
format so `compare_metrics.py` can diff wrapper vs `tr2` output).

| Attribute | Type | Meaning |
|---|---|---|
| `nt` | int | current time-step index |
| `nrmax` | int | radial points actually in use |
| `nsmax` | int | species actually in use |
| `scalars` | dict[str, float] | 13 plasma scalars (see below) |
| `RN` | list[list[float]] | `[nrmax][nsmax]` density profile |
| `RT` | list[list[float]] | `[nrmax][nsmax]` temperature profile |
| `AJ` | list[float] | `[nrmax]` current density profile |
| `QP` | list[float] | `[nrmax]` safety-factor profile |

Scalars (canonical order): `T`, `WPT`, `AJT`, `Q0`, `BETA0`,
`BETAP0`, `BETAA`, `BETAN`, `TAUE1`, `TAUE2`, `ZEFF0`, `ALI`, `RQ1`.

## Exceptions

Every `tr_*` return code maps to a concrete subclass of `TrlibError`:

| ierr | class | meaning |
|---|---|---|
| 0 | — | success |
| 1 | `TrlibParamError` | invalid parameter name / index / value |
| 2 | `TrlibStateError` | API call before `tr_init` or after `close` |
| 3 | `TrlibRunError` | calculation or `tr_get_state` failed |
| 4 | `TrlibNotImplementedError` | Phase L-2 stub return |

Spec-style aliases (`TrLibInvalidParam`, `TrLibNotInitialized`,
`TrLibCalculationFailed`, `TrLibNotImplemented`) are also exported.

## Migration: `tr` CLI → `trlib.Trlib`

| CLI step | `trlib` equivalent |
|---|---|
| edit `trparm` namelist | `tr.set_param(...)` / `tr.set_params(...)` |
| menu option `R` (run) | `tr.run(ntmax=...)` |
| inspect output file | `tr.get_state()` |
| menu `Q` (quit) | exit context manager / `tr.close()` |
| batch parameter sweep | Python `for` loop (see `examples/parameter_sweep.py`) |

The wrapper does **not** wrap graphics, file output, or the
interactive menu — those live in `tr/tr2` only.

## Known limitations

- **Single instance per process.** TR backend uses COMMON blocks.
  Two concurrent `Trlib()` instances share state; the second
  `tr_init` resets globals.
- **No PGPlot/GSAF graphics, no MPI, no OpenMP API.** Fortran-side
  graphics symbols exist but are not reachable from the 5 exported
  entry points; the loader uses `RTLD_LAZY` so dangling graphics
  references never resolve. Python-side visualization is provided
  separately via `trlib.plot` (matplotlib backend, optional dependency)
  — see the Plot section below.
- **String parameters not yet wired** (e.g. `KNAMEQ`, `KNAMTR`). See
  `docs/superpowers/specs/2026-04-17-tr-library-design.md` §4.3.
- **Unregistered namelist keys** — any name missing from
  `tr_param_registry.f90` returns `TrlibParamError`. Known gaps include
  geometry/profile tunables that the design spec deferred to later
  phases (string parameters, model-specific tuning coefficients beyond
  `CDW` / `CHP` / `CK0` / `CK1`).
- **`tr_m0904` baseline drift** — the `tr_m0904` regression fixture
  exhibited small (`~1e-8`) drift between `tr2` and the Layer 1 suite
  during Phase L-6 and is pinned to its Phase 0 baseline. Use `1e-10`
  tolerance for `tr_iter01` / `tr_tst2` but allow looser comparison for
  `tr_m0904` when diffing against freshly regenerated tr2 runs.

## Testing

```bash
cd python/trlib/tests
python3 -m unittest discover -v
```

Tests that require `libtrapi.so` are skipped when the shared library
is absent; pure-Python tests (ctypes layout, error wiring,
`TrState.from_c`, `to_dict` shape) always run.

The full 4-layer regression suite is wired into
`test_run/test_definitions.conf`:

- `trlib_c_abi` — Layer 2 C ABI (`make -C tr tr_api_check_all`)
- `trlib_ffi`, `trlib_wrapper` — Layer 3 Python wrapper
- `trlib_equivalence` — Layer 1 vs Phase 0 baselines (tol `1e-10`)
- `trlib_sweep` — Layer 4 3×3 RR×BB smoke

## License / contributions

`trlib` is part of the TASK code and distributed under the repository's
top-level license. Bug reports and PRs are welcome; please keep
wrapper changes minimal — the C ABI is the stable layer, so new
parameters should be added to the Fortran registry first.

## TOML config 実行方法

`python -m trlib <config.toml>` でパラメータ設定 + 計算 + プロットを 1
コマンドで実行できます。CLI 版の namelist 入力 (`./tr < tr_iter01.in`)
を Python 側に置き換えるための入口です。

サンプル config はリポジトリ内に同梱しています:

- `python/trlib/samples/iter01.toml` — `test_run/inputs/tr_iter01.in` を TOML 化したもの
- `python/trlib/samples/tst2.toml` — `test_run/inputs/tr_tst2.in` を TOML 化したもの

```bash
# 計算 + プロットを一気に実行 (libtrapi.so + matplotlib が必要)
python -m trlib python/trlib/samples/iter01.toml

# 設定だけ確認 (ライブラリ未ビルドでも OK)
python -m trlib python/trlib/samples/iter01.toml --dry-run

# NTMAX を上書き
python -m trlib python/trlib/samples/tst2.toml --ntmax 5

# プロットだけスキップ (matplotlib が無い環境向け)
python -m trlib python/trlib/samples/iter01.toml --no-plots
```

### TOML スキーマ

```toml
[module]
name = "tr"
ntmax = 100              # NTMAX scalar への alias

[scalars]
RR = 3.0
NSMAX = 4

[arrays]
PN = [0.7, 0.315, 0.315, 0.035]   # 1-origin リスト
# PA = { 2 = 1.0 }                 # sparse dict 形式 (PA(1) は default)

[strings]
KNAMEQ = "eqdata.ITER"

[[plots]]                # 配列 of tables で複数プロット
variable = "RNT"
output   = "file"        # window | file | return
format   = "png"
path     = "./plots/rnt.png"
title    = "温度密度プロファイル"
```

### Exit code

| code | 意味 |
|---|---|
| 0 | 正常終了 |
| 1 | ライブラリ / 計算エラー |
| 2 | config エラー (未存在ファイル / TOML 構文エラー / matplotlib 不足) |

## プロット

`trlib.plot` は :mod:`matplotlib` をオプション依存とする可視化レイヤー
です。`trlib` 本体は matplotlib なしでも import できますが、`plot()` を
呼ぶと `ImportError` になります。

### 対話的に呼ぶ

```bash
python -c "from trlib import Trlib; \
  tr = Trlib(); tr.run(0); tr.plot('RNT'); tr.close()"
```

### 利用可能な変数を確認する

```python
from trlib import Trlib
print(Trlib.plot_available())   # ['AJ', 'ALI', 'BETA0', ..., 'WPT']
```

`VARIABLE_INFO` 辞書 (in `trlib/plot.py`) に登録された変数のみが描画でき
ます。新しい変数を追加するときはこの dict にエントリを足してください。

### 出力モード

| `output` | 用途 | 戻り値 |
|---|---|---|
| `"window"` (default) | CLI / インタラクティブ表示 | `None` |
| `"file"` | バッチ / CI で画像保存 | `pathlib.Path` |
| `"return"` | notebook embed / 後処理 | `matplotlib.figure.Figure` |

### サンプル

```python
from trlib import Trlib

with Trlib() as tr:
    tr.set_params(RR=8.5, RA=2.0, BB=5.3, NSMAX=2, DT=0.1)
    tr.run(50)
    tr.plot("RNT", output="file", path="./rnt.png")    # PNG 保存
    fig = tr.plot("AJ", output="return")               # Figure 受け取り
```

### matplotlib が無い環境での挙動

`pip install matplotlib` を行わずに `trlib.plot` を import / `.plot()` を
呼ぶと、明示的な `ImportError` が発生します。`__main__` では plot
セクションが無い限り matplotlib を import しないため、`--no-plots` を
付ければ matplotlib 未インストール環境でも `python -m trlib` を実行でき
ます。

## See also

- `docs/superpowers/specs/2026-04-17-tr-library-design.md` — full
  design spec (Phase L)
- `docs/tr-library/architecture.md` — system diagram and Phase
  completion matrix
- `tr/tr_api.h` — C ABI header
- `CHANGELOG.md` — per-phase history
