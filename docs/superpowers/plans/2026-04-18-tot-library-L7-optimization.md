# TOT Library Phase L-7: パラメータ最適化ワークフロー 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** tot ライブラリ化の **end-goal** である「結合物理（TR + TI + FP + WR + EQ）に対する Python 駆動のパラメータ最適化」を実装する。`Totlib` を内部で叩く `python/totlib/optimize.py` を構築し、(a) scipy.optimize による勾配法 / Nelder-Mead、(b) optuna による Bayesian 最適化、(c) 単純な grid sweep の 3 つを統一インタフェースから使えるようにする。結果は JSON + 可視化用 notebook で残す。

**Architecture:** 中核は `OptimizationProblem` dataclass（探索パラメータ・目的関数・制約・初期値・bound）と `run_optimization(problem, backend)` 関数。`backend` は `"scipy"` / `"optuna"` / `"grid"` を受け取り、内部で対応する optimizer を呼び出す。各 trial は単一の `Totlib` セッションで `set_params → run → get_state → compute_objective` を実行。結果は `OptimizationResult` dataclass + JSON 永続化。可視化は Jupyter notebook で「最適化履歴」「パラメータ分布」「目的関数の変化」を描画。

**Tech Stack:**
- Python 3.8+, numpy（既出）
- scipy.optimize（最適化のデファクト、SLSQP/COBYLA/Nelder-Mead 等）
- optuna（オプション依存、Bayesian / TPE / NSGA-II 等。L-7 では `try: import optuna` で graceful degrade）
- matplotlib（notebook 用、`requirements-optimize.txt` に分離）
- Jupyter（notebook 用、`requirements-optimize.txt` に分離）

**出典設計書:** TR Phase L 設計（`docs/superpowers/specs/2026-04-17-tr-library-design.md`）の 2.1「網羅計算の性能」を実用的な最適化ワークフローに具体化する。**ユーザ最終目標** であり、ここまでの L-0..L-6 全てが本フェーズのための基盤。

**前提条件:** L-0..L-6 完了。`libtotapi.so` が安定動作。Layer 4 sweep test が PASS（NaN/Inf 検出なし）。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/totlib/optimize.py` | 新規 | `OptimizationProblem`, `OptimizationResult`, `run_optimization` の本体 |
| `python/totlib/objectives.py` | 新規 | プリセット目的関数（`maximize_q0`, `match_target_betap`, `multi_objective_q_taue`, etc.） |
| `python/totlib/results.py` | 新規 | `OptimizationResult` dataclass + JSON 入出力 + 履歴 (trials list) |
| `python/totlib/tests/test_optimize.py` | 新規 | 最適化 backend の動作検証（scipy / grid 必須、optuna は skipif） |
| `python/totlib/tests/test_objectives.py` | 新規 | 目的関数の単体テスト（state を mock した数値検証） |
| `python/totlib/notebooks/01_quickstart_optimize.ipynb` | 新規 | quickstart notebook（grid sweep + scipy + 結果可視化） |
| `python/totlib/notebooks/02_q0_maximization.ipynb` | 新規 | 「Q0 最大化」最小実例 |
| `python/totlib/notebooks/03_pareto_q_taue.ipynb` | 新規 | optuna による多目的 Pareto front 例（optional） |
| `python/totlib/requirements-optimize.txt` | 新規 | scipy, optuna, matplotlib, jupyter 依存 |
| `python/totlib/README.md` | 修正 | 「パラメータ最適化」セクション追記 |
| `docs/superpowers/specs/2026-04-18-tot-optimization-results-format.md` | 新規 | 結果 JSON スキーマの正規化ドキュメント |
| `test_run/test_definitions.conf` | 修正 | `totlib_optimize_smoke` カテゴリ追加 |

**方針:**
- 最適化対象パラメータは L-3 の prefix 名 (`TR.RR`, `EQ.BB`, `TR.PN[1]`) で指定。
- 目的関数は `f(state: TotState) -> float` の規約。`objectives.py` に共用例を 5-6 個用意。
- scipy backend が **必須**、optuna は optional dependency。grid backend は外部依存ゼロ。
- 各 trial の入力 / 結果 / Q0 / WPT などのスカラーを JSON 1 行で append（NDJSON 形式）し、長時間実行でも resume 可能にする。

---

## Task 1: ブランチ作成 + 前提確認

**Files:** なし

- [ ] **Step 1: ブランチ**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop && git pull
git checkout -b feature/tot-library-l7-optimization
```

- [ ] **Step 2: L-6 までのテスト全 PASS 確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh
```
Expected: 全 PASS。

- [ ] **Step 3: scipy が利用できるか確認**

Run:
```bash
python3 -c "import scipy.optimize; print(scipy.__version__)"
```
Expected: scipy バージョンが表示される。無ければ `pip install --user scipy` を実行 or 諦めて grid backend のみで進める旨を README に明記。

- [ ] **Step 4: 初期コミット**

Run:
```bash
git commit --allow-empty -m "chore(tot): start L-7 parameter optimization workflow"
```

---

## Task 2: 結果 JSON スキーマの仕様策定

**Files:**
- Create: `docs/superpowers/specs/2026-04-18-tot-optimization-results-format.md`

- [ ] **Step 1: スキーマ仕様書作成**

作成: `docs/superpowers/specs/2026-04-18-tot-optimization-results-format.md`

```markdown
# TOT Optimization Results Format

**Date:** 2026-04-18
**Scope:** Output JSON / NDJSON schema for `python/totlib/optimize.py`.

## File layout

```
results_dir/
├── problem.json        # OptimizationProblem snapshot
├── trials.ndjson       # one trial per line, append-only
└── result.json         # final OptimizationResult (best trial + summary)
```

## problem.json

```json
{
  "name": "q0_maximize_demo2014",
  "backend": "scipy",
  "method": "Nelder-Mead",
  "params": [
    {"name": "EQ.RR", "lower": 6.0, "upper": 7.5, "init": 6.5},
    {"name": "EQ.BB", "lower": 4.5, "upper": 6.5, "init": 5.3}
  ],
  "fixed_params": {"EQ.RA": 2.0, "TR.NTMAX": 10},
  "objective": "maximize_q0",
  "minimize": false,
  "ntmax": 10,
  "max_iterations": 100,
  "seed": 42
}
```

## trials.ndjson

One JSON object per line:

```json
{"trial_id": 0, "params": {"EQ.RR": 6.5, "EQ.BB": 5.3}, "objective": 1.42, "scalars": {"WPT": 41.13, "Q0": 0.579, "TAUE1": 2.265}, "wall_time_s": 12.3, "error": null}
```

`error` is null on success, otherwise a string with the exception class name.

## result.json

```json
{
  "best_trial_id": 17,
  "best_params": {"EQ.RR": 6.21, "EQ.BB": 5.34},
  "best_objective": 1.612,
  "n_trials": 100,
  "n_failed": 3,
  "wall_time_s": 1234.5,
  "convergence": {"final_step_norm": 1e-3}
}
```

## Determinism

The optimization is reproducible iff the same `seed` and `params` are used.
Per-trial Totlib runs are reproducible (see L-0 dump reproducibility).
```

- [ ] **Step 2: コミット**

Run:
```bash
git add docs/superpowers/specs/2026-04-18-tot-optimization-results-format.md
git commit -m "docs(tot): specify optimization results JSON/NDJSON format"
```

---

## Task 3: `requirements-optimize.txt` を作成

**Files:**
- Create: `python/totlib/requirements-optimize.txt`

- [ ] **Step 1: 依存リスト**

作成: `python/totlib/requirements-optimize.txt`

```
# Optional dependencies for L-7 parameter optimization.
# Install with: pip install -r python/totlib/requirements-optimize.txt
scipy>=1.7
optuna>=3.0  # optional; backend-specific
matplotlib>=3.4  # for notebooks
jupyter>=1.0
notebook>=6.4
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/requirements-optimize.txt
git commit -m "chore(totlib): pin optimization-only deps in requirements-optimize.txt"
```

---

## Task 4: `results.py` を作成（OptimizationResult + JSON I/O）

**Files:**
- Create: `python/totlib/results.py`

- [ ] **Step 1: 新規作成**

作成: `python/totlib/results.py`

```python
"""OptimizationResult dataclass and persistence helpers."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TrialRecord:
    trial_id: int
    params: dict[str, float]
    objective: float | None
    scalars: dict[str, float]
    wall_time_s: float
    error: str | None = None


@dataclass
class OptimizationResult:
    best_trial_id: int
    best_params: dict[str, float]
    best_objective: float
    n_trials: int
    n_failed: int
    wall_time_s: float
    convergence: dict[str, Any] = field(default_factory=dict)

    def to_json(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n")

    @classmethod
    def from_json(cls, path: Path) -> "OptimizationResult":
        data = json.loads(path.read_text())
        return cls(**data)


def append_trial(path: Path, trial: TrialRecord) -> None:
    """Append a single trial as one NDJSON line (atomic-ish)."""
    line = json.dumps(asdict(trial), sort_keys=True)
    with path.open("a") as f:
        f.write(line + "\n")


def read_trials(path: Path) -> list[TrialRecord]:
    """Read all trials from an NDJSON file."""
    if not path.exists():
        return []
    trials: list[TrialRecord] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        trials.append(TrialRecord(**json.loads(line)))
    return trials
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/results.py
git commit -m "feat(totlib): add OptimizationResult and TrialRecord with JSON/NDJSON I/O"
```

---

## Task 5: `objectives.py` を作成（プリセット目的関数）

**Files:**
- Create: `python/totlib/objectives.py`

- [ ] **Step 1: 新規作成**

作成: `python/totlib/objectives.py`

```python
"""Preset objective functions operating on TotState.

Each function returns a single float (the value to maximize OR minimize,
depending on Problem.minimize). Functions are intentionally simple — wrap
them or write your own when you need composite objectives.
"""
from __future__ import annotations

import math
from typing import Callable

from .state import TotState


def maximize_q0(state: TotState) -> float:
    """Return Q0 (axial safety factor). Caller sets minimize=False."""
    return float(state.tr.Q0) if state.tr is not None else float("nan")


def maximize_wpt(state: TotState) -> float:
    """Return WPT (stored energy in MJ)."""
    return float(state.tr.WPT) if state.tr is not None else float("nan")


def maximize_taue(state: TotState) -> float:
    """Return TAUE1 (energy confinement time)."""
    return float(state.tr.TAUE1) if state.tr is not None else float("nan")


def match_target(target_attr: str, target_value: float) -> Callable[[TotState], float]:
    """Return |state.tr.<attr> - target| for use with minimize=True."""
    def _obj(state: TotState) -> float:
        if state.tr is None:
            return float("inf")
        actual = getattr(state.tr, target_attr)
        return abs(float(actual) - float(target_value))
    return _obj


def weighted_sum(weights: dict[str, float]) -> Callable[[TotState], float]:
    """Linear combination of TR scalars: sum(w_k * state.tr.<k>).

    Example: weighted_sum({"WPT": 1.0, "TAUE1": -0.5}) maximizes WPT
    while penalizing high TAUE1 (caller sets minimize=False).
    """
    def _obj(state: TotState) -> float:
        if state.tr is None:
            return float("nan")
        total = 0.0
        for k, w in weights.items():
            total += w * float(getattr(state.tr, k))
        return total
    return _obj


def safe_or_inf(fn: Callable[[TotState], float]) -> Callable[[TotState], float]:
    """Wrap fn so that NaN/Inf result becomes a fixed sentinel (+inf).

    Useful when minimizing and you want failed trials to be ignored
    automatically by gradient-free optimizers like Nelder-Mead.
    """
    def _wrapped(state: TotState) -> float:
        v = fn(state)
        if not math.isfinite(v):
            return float("inf")
        return v
    return _wrapped
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/objectives.py
git commit -m "feat(totlib): add preset objective functions (Q0, WPT, TAUE, match, weighted_sum)"
```

---

## Task 6: `optimize.py` 中核を作成

**Files:**
- Create: `python/totlib/optimize.py`

- [ ] **Step 1: 新規作成**

作成: `python/totlib/optimize.py`

```python
"""Parameter optimization driver for TOT integrated simulator.

Supported backends:
    - "grid"   : exhaustive cartesian product (no external deps)
    - "scipy"  : scipy.optimize.minimize with Nelder-Mead by default
    - "optuna" : optuna study (TPE sampler)

Usage:
    from totlib import Totlib
    from totlib.optimize import OptimizationProblem, ParamSpec, run_optimization
    from totlib.objectives import maximize_q0

    problem = OptimizationProblem(
        name="q0_demo",
        params=[
            ParamSpec("EQ.RR", lower=6.0, upper=7.5, init=6.5),
            ParamSpec("EQ.BB", lower=4.5, upper=6.5, init=5.3),
        ],
        fixed_params={"EQ.RA": 2.0},
        objective=maximize_q0,
        minimize=False,
        ntmax=10,
    )
    result = run_optimization(problem, backend="scipy", out_dir=Path("results/q0_demo"))
    print("best Q0 =", result.best_objective, "at", result.best_params)
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from itertools import product
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

from .state import TotState
from .totlib import Totlib
from .results import OptimizationResult, TrialRecord, append_trial


@dataclass
class ParamSpec:
    name: str
    lower: float
    upper: float
    init: float | None = None
    grid_n: int = 5  # used by grid backend

    def grid_points(self) -> np.ndarray:
        return np.linspace(self.lower, self.upper, self.grid_n)


@dataclass
class OptimizationProblem:
    name: str
    params: Sequence[ParamSpec]
    objective: Callable[[TotState], float]
    fixed_params: dict[str, float] = field(default_factory=dict)
    minimize: bool = True
    ntmax: int = 10
    max_iterations: int = 100
    seed: int = 0

    def initial_vector(self) -> np.ndarray:
        return np.array([
            (p.init if p.init is not None else 0.5 * (p.lower + p.upper))
            for p in self.params
        ], dtype=float)

    def bounds(self) -> list[tuple[float, float]]:
        return [(p.lower, p.upper) for p in self.params]

    def vector_to_dict(self, x: np.ndarray) -> dict[str, float]:
        return {p.name: float(v) for p, v in zip(self.params, x)}

    def to_dict(self, *, backend: str, method: str | None) -> dict:
        return {
            "name": self.name,
            "backend": backend,
            "method": method,
            "params": [asdict(p) for p in self.params],
            "fixed_params": dict(self.fixed_params),
            "objective": getattr(self.objective, "__name__", repr(self.objective)),
            "minimize": self.minimize,
            "ntmax": self.ntmax,
            "max_iterations": self.max_iterations,
            "seed": self.seed,
        }


# ------------------------------------------------------------------
# Trial harness
# ------------------------------------------------------------------

class TrialRunner:
    """Wraps a single Totlib instance and records each trial."""

    def __init__(self, problem: OptimizationProblem, trials_path: Path) -> None:
        self.problem = problem
        self.trials_path = trials_path
        self._counter = 0
        self.tot = Totlib()
        # Apply fixed parameters once.
        if problem.fixed_params:
            self.tot.set_params(problem.fixed_params)

    def close(self) -> None:
        self.tot.finalize()

    def __enter__(self) -> "TrialRunner":
        return self

    def __exit__(self, *a: Any) -> None:
        self.close()

    def evaluate(self, x: np.ndarray) -> float:
        params = self.problem.vector_to_dict(x)
        t0 = time.time()
        scalars: dict[str, float] = {}
        objective: float | None = None
        err: str | None = None
        try:
            self.tot.set_params(params)
            self.tot.run(ntmax=self.problem.ntmax)
            state = self.tot.get_state()
            objective = float(self.problem.objective(state))
            if state.tr is not None:
                scalars = {
                    "Q0": float(state.tr.Q0),
                    "WPT": float(state.tr.WPT),
                    "TAUE1": float(state.tr.TAUE1),
                    "BETA0": float(state.tr.BETA0),
                    "ALI": float(state.tr.ALI),
                }
        except Exception as e:  # noqa: BLE001 — record any failure
            err = type(e).__name__ + ": " + str(e)
        t1 = time.time()
        rec = TrialRecord(
            trial_id=self._counter,
            params=params,
            objective=objective,
            scalars=scalars,
            wall_time_s=t1 - t0,
            error=err,
        )
        append_trial(self.trials_path, rec)
        self._counter += 1
        # For minimize/maximize: scipy expects minimize, so negate when needed.
        if objective is None:
            return float("inf")
        return objective if self.problem.minimize else -objective


# ------------------------------------------------------------------
# Backends
# ------------------------------------------------------------------

def _run_grid(problem: OptimizationProblem, runner: TrialRunner) -> tuple[np.ndarray, float]:
    grids = [p.grid_points() for p in problem.params]
    best_x = problem.initial_vector()
    best_v = float("inf")
    for combo in product(*grids):
        x = np.array(combo, dtype=float)
        v = runner.evaluate(x)
        if v < best_v:
            best_v = v
            best_x = x
    return best_x, best_v


def _run_scipy(
    problem: OptimizationProblem, runner: TrialRunner, method: str
) -> tuple[np.ndarray, float, dict[str, Any]]:
    from scipy.optimize import minimize  # local import (optional dep)

    x0 = problem.initial_vector()
    res = minimize(
        runner.evaluate,
        x0,
        method=method,
        bounds=problem.bounds() if method != "Nelder-Mead" else None,
        options={"maxiter": problem.max_iterations, "disp": False},
    )
    convergence = {
        "success": bool(res.success),
        "message": str(res.message),
        "nit": int(getattr(res, "nit", -1)),
        "nfev": int(getattr(res, "nfev", -1)),
    }
    return np.asarray(res.x, dtype=float), float(res.fun), convergence


def _run_optuna(
    problem: OptimizationProblem, runner: TrialRunner
) -> tuple[np.ndarray, float, dict[str, Any]]:
    try:
        import optuna
    except ImportError as e:  # graceful degrade
        raise RuntimeError("optuna not installed — pip install optuna") from e

    sampler = optuna.samplers.TPESampler(seed=problem.seed)
    direction = "minimize" if problem.minimize else "maximize"
    study = optuna.create_study(direction=direction, sampler=sampler)

    def _suggest(trial: "optuna.trial.Trial") -> float:  # type: ignore[name-defined]
        x = np.array([
            trial.suggest_float(p.name, p.lower, p.upper) for p in problem.params
        ], dtype=float)
        v = runner.evaluate(x)  # always returns minimize-form (negated if !minimize)
        # optuna expects user objective in user-direction; un-negate when not minimizing
        return v if problem.minimize else -v

    study.optimize(_suggest, n_trials=problem.max_iterations)
    best_x = np.array(
        [study.best_params[p.name] for p in problem.params], dtype=float
    )
    return best_x, float(study.best_value), {
        "n_complete_trials": len(study.trials),
    }


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def run_optimization(
    problem: OptimizationProblem,
    *,
    backend: str = "scipy",
    method: str = "Nelder-Mead",
    out_dir: Path,
) -> OptimizationResult:
    """Run optimization and persist artifacts to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    problem_path = out_dir / "problem.json"
    trials_path = out_dir / "trials.ndjson"
    result_path = out_dir / "result.json"

    problem_path.write_text(
        json.dumps(problem.to_dict(backend=backend, method=method), indent=2, sort_keys=True) + "\n"
    )
    # Reset trials file (caller decides resume vs fresh).
    trials_path.write_text("")

    t0 = time.time()
    with TrialRunner(problem, trials_path) as runner:
        if backend == "grid":
            best_x, best_v = _run_grid(problem, runner)
            convergence: dict[str, Any] = {}
        elif backend == "scipy":
            best_x, best_v, convergence = _run_scipy(problem, runner, method=method)
        elif backend == "optuna":
            best_x, best_v, convergence = _run_optuna(problem, runner)
        else:
            raise ValueError(f"unknown backend: {backend!r}")
    t1 = time.time()

    # Re-scan trials.ndjson to identify the best (more robust than relying on
    # the optimizer's reported best — handles case when objective() was nan).
    best_trial_id, best_obj, n_trials, n_failed = _scan_trials(trials_path, problem.minimize)
    result = OptimizationResult(
        best_trial_id=best_trial_id,
        best_params=problem.vector_to_dict(best_x),
        best_objective=best_obj if best_obj is not None else float("nan"),
        n_trials=n_trials,
        n_failed=n_failed,
        wall_time_s=t1 - t0,
        convergence=convergence,
    )
    result.to_json(result_path)
    return result


def _scan_trials(trials_path: Path, minimize: bool) -> tuple[int, float | None, int, int]:
    n_trials, n_failed = 0, 0
    best_id, best_v = -1, None
    for line in trials_path.read_text().splitlines():
        if not line.strip():
            continue
        n_trials += 1
        rec = json.loads(line)
        if rec.get("error"):
            n_failed += 1
            continue
        v = rec.get("objective")
        if v is None or (isinstance(v, float) and (v != v or v == float("inf"))):
            n_failed += 1
            continue
        if best_v is None or (v < best_v if minimize else v > best_v):
            best_v = float(v)
            best_id = int(rec["trial_id"])
    return best_id, best_v, n_trials, n_failed
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/optimize.py
git commit -m "feat(totlib): add optimization driver (grid/scipy/optuna backends)"
```

---

## Task 7: `__init__.py` から re-export

**Files:**
- Modify: `python/totlib/__init__.py`

- [ ] **Step 1: re-export 追加**

`python/totlib/__init__.py` の末尾に追加:

```python
from .optimize import OptimizationProblem, ParamSpec, run_optimization
from .results import OptimizationResult, TrialRecord
from . import objectives

__all__ += [
    "OptimizationProblem", "ParamSpec", "run_optimization",
    "OptimizationResult", "TrialRecord", "objectives",
]
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/__init__.py
git commit -m "feat(totlib): re-export optimization API from package root"
```

---

## Task 8: `objectives.py` のユニットテスト

**Files:**
- Create: `python/totlib/tests/test_objectives.py`

- [ ] **Step 1: テスト**

作成: `python/totlib/tests/test_objectives.py`

```python
"""Unit tests for objective functions (no Totlib needed; mocks state)."""
import numpy as np
import pytest

from totlib import TotState
from totlib.state import TrState
from totlib.objectives import (
    maximize_q0, maximize_wpt, maximize_taue,
    match_target, weighted_sum, safe_or_inf,
)


def _state(**overrides):
    base = dict(
        nt=10, nrmax=2, nsmax=2,
        T=2.0, WPT=41.13, AJT=15.451, Q0=0.579,
        BETA0=0.012, BETAP0=0.089, BETAA=0.0023, BETAN=0.045,
        TAUE1=2.265, TAUE2=2.1, ZEFF0=1.5, ALI=0.75, RQ1=1.8,
        RN=np.zeros((2, 2)), RT=np.zeros((2, 2)),
        AJ=np.zeros(2), QP=np.zeros(2),
    )
    base.update(overrides)
    tr = TrState(**base)
    return TotState(tr_present=True, ti_present=True, fp_present=True, wr_present=True, tr=tr)


def test_maximize_q0_returns_q0():
    assert maximize_q0(_state(Q0=0.5)) == 0.5

def test_maximize_wpt_returns_wpt():
    assert maximize_wpt(_state(WPT=42.0)) == 42.0

def test_maximize_taue_returns_taue1():
    assert maximize_taue(_state(TAUE1=2.5)) == 2.5

def test_match_target_returns_abs_diff():
    obj = match_target("Q0", target_value=1.0)
    assert obj(_state(Q0=0.7)) == pytest.approx(0.3)

def test_weighted_sum_linear_combo():
    obj = weighted_sum({"WPT": 1.0, "TAUE1": -0.5})
    assert obj(_state(WPT=40.0, TAUE1=2.0)) == pytest.approx(40.0 - 1.0)

def test_safe_or_inf_replaces_nan():
    obj = safe_or_inf(lambda s: float("nan"))
    assert obj(_state()) == float("inf")

def test_safe_or_inf_passes_through_finite():
    obj = safe_or_inf(maximize_q0)
    assert obj(_state(Q0=0.7)) == 0.7
```

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task
PYTHONPATH=python python3 -m pytest python/totlib/tests/test_objectives.py -v
```
Expected: 全 PASS。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/totlib/tests/test_objectives.py
git commit -m "test(totlib): add unit tests for preset objectives (mock state)"
```

---

## Task 9: 最適化 backend の smoke test

**Files:**
- Create: `python/totlib/tests/test_optimize.py`

- [ ] **Step 1: テスト**

作成: `python/totlib/tests/test_optimize.py`

```python
"""Smoke tests for optimization backends.

These tests actually call libtotapi.so; keep them small and bounded.
"""
import json
from pathlib import Path

import pytest

from totlib import (
    OptimizationProblem, ParamSpec, run_optimization,
)
from totlib.objectives import maximize_q0


@pytest.fixture
def problem_q0():
    return OptimizationProblem(
        name="test_q0",
        params=[
            ParamSpec("EQ.RR", lower=6.2, upper=6.4, init=6.3, grid_n=2),
            ParamSpec("EQ.BB", lower=5.2, upper=5.4, init=5.3, grid_n=2),
        ],
        objective=maximize_q0,
        minimize=False,
        ntmax=1,
        max_iterations=4,
    )


class TestGridBackend:
    def test_grid_runs_and_writes_artifacts(self, tmp_path, problem_q0):
        result = run_optimization(problem_q0, backend="grid", out_dir=tmp_path)
        assert result.n_trials == 4   # 2x2 grid
        assert (tmp_path / "problem.json").exists()
        assert (tmp_path / "trials.ndjson").exists()
        assert (tmp_path / "result.json").exists()
        # NDJSON file has 4 lines.
        lines = (tmp_path / "trials.ndjson").read_text().splitlines()
        assert len(lines) == 4
        for line in lines:
            rec = json.loads(line)
            assert "params" in rec
            assert "EQ.RR" in rec["params"]


class TestScipyBackend:
    def test_scipy_nelder_mead_runs(self, tmp_path, problem_q0):
        scipy = pytest.importorskip("scipy.optimize")  # skip if unavailable
        result = run_optimization(
            problem_q0, backend="scipy", method="Nelder-Mead", out_dir=tmp_path
        )
        assert result.n_trials >= 1
        assert "EQ.RR" in result.best_params
        assert "EQ.BB" in result.best_params


class TestOptunaBackend:
    def test_optuna_tpe_runs(self, tmp_path, problem_q0):
        pytest.importorskip("optuna")
        result = run_optimization(problem_q0, backend="optuna", out_dir=tmp_path)
        assert result.n_trials == problem_q0.max_iterations
        assert "EQ.RR" in result.best_params
```

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task
TOTLIB_PATH=/home/k-yoshimi/program/task/tot/libtotapi.so \
PYTHONPATH=/home/k-yoshimi/program/task/python \
python3 -m pytest python/totlib/tests/test_optimize.py -v
```
Expected: grid PASS、scipy PASS（scipy 利用可能なら）、optuna は skip 可。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/totlib/tests/test_optimize.py
git commit -m "test(totlib): smoke tests for grid/scipy/optuna backends"
```

---

## Task 10: Quickstart Notebook 作成

**Files:**
- Create: `python/totlib/notebooks/01_quickstart_optimize.ipynb`

- [ ] **Step 1: notebook 作成**

実装方針: notebook はバージョン管理しやすくするため、`jupytext` の percent format で書いた `.py` から `jupyter nbconvert --to notebook` で生成するのが理想だが、L-7 ではそこまでは要求しない。直接 `.ipynb` を JSON で書き起こす。

最小内容（notebook の cells を表現する JSON）:

```bash
cat > /home/k-yoshimi/program/task/python/totlib/notebooks/01_quickstart_optimize.ipynb << 'EOF'
{
 "cells": [
  {"cell_type": "markdown", "metadata": {}, "source": [
    "# totlib Quickstart: Parameter Optimization\n",
    "\n",
    "This notebook demonstrates the L-7 optimization API:\n",
    "1. Define an OptimizationProblem with parameter bounds.\n",
    "2. Run with the grid backend (no external deps).\n",
    "3. Run with scipy Nelder-Mead.\n",
    "4. Plot trial trajectories."
  ]},
  {"cell_type": "code", "execution_count": null, "metadata": {}, "outputs": [], "source": [
    "import os, sys\n",
    "from pathlib import Path\n",
    "REPO = Path('..').resolve().parents[1]\n",
    "os.environ['TOTLIB_PATH'] = str(REPO / 'tot' / 'libtotapi.so')\n",
    "sys.path.insert(0, str(REPO / 'python'))\n",
    "from totlib import (OptimizationProblem, ParamSpec, run_optimization, objectives)\n",
    "import numpy as np, matplotlib.pyplot as plt, json"
  ]},
  {"cell_type": "code", "execution_count": null, "metadata": {}, "outputs": [], "source": [
    "problem = OptimizationProblem(\n",
    "    name='quickstart_q0',\n",
    "    params=[\n",
    "        ParamSpec('EQ.RR', lower=6.0, upper=7.0, init=6.5, grid_n=4),\n",
    "        ParamSpec('EQ.BB', lower=5.0, upper=6.0, init=5.5, grid_n=4),\n",
    "    ],\n",
    "    objective=objectives.maximize_q0,\n",
    "    minimize=False,\n",
    "    ntmax=1,\n",
    "    max_iterations=20,\n",
    ")\n",
    "out = Path('runs/quickstart_grid')\n",
    "result = run_optimization(problem, backend='grid', out_dir=out)\n",
    "print('best Q0 =', result.best_objective, 'at', result.best_params)"
  ]},
  {"cell_type": "code", "execution_count": null, "metadata": {}, "outputs": [], "source": [
    "trials = [json.loads(l) for l in (out / 'trials.ndjson').read_text().splitlines() if l.strip()]\n",
    "objs = [t.get('objective') for t in trials if t.get('objective') is not None]\n",
    "fig, ax = plt.subplots()\n",
    "ax.plot(objs, 'o-')\n",
    "ax.set_xlabel('trial id'); ax.set_ylabel('Q0'); ax.set_title('Grid sweep')\n",
    "plt.show()"
  ]},
  {"cell_type": "code", "execution_count": null, "metadata": {}, "outputs": [], "source": [
    "out2 = Path('runs/quickstart_nm')\n",
    "result2 = run_optimization(problem, backend='scipy', method='Nelder-Mead', out_dir=out2)\n",
    "print('Nelder-Mead best Q0 =', result2.best_objective, 'at', result2.best_params)"
  ]}
 ],
 "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.10"}},
 "nbformat": 4, "nbformat_minor": 5
}
EOF
```

- [ ] **Step 2: nbconvert で実行可能性を確認（optional）**

Run:
```bash
cd /home/k-yoshimi/program/task/python/totlib/notebooks
jupyter nbconvert --to notebook --execute 01_quickstart_optimize.ipynb --output 01_quickstart_optimize_run.ipynb 2>&1 | tail -10 || echo "execute step is optional"
```
Expected: 実行成功。jupyter が無い場合はスキップ。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/totlib/notebooks/01_quickstart_optimize.ipynb
git commit -m "docs(totlib): add quickstart notebook for parameter optimization"
```

---

## Task 11: 例題 notebook 2 つを追加（Q0 最大化 / 多目的）

**Files:**
- Create: `python/totlib/notebooks/02_q0_maximization.ipynb`
- Create: `python/totlib/notebooks/03_pareto_q_taue.ipynb`

- [ ] **Step 1: Q0 最大化 notebook**

作成: `python/totlib/notebooks/02_q0_maximization.ipynb`

```bash
cat > /home/k-yoshimi/program/task/python/totlib/notebooks/02_q0_maximization.ipynb << 'EOF'
{
 "cells": [
  {"cell_type": "markdown", "metadata": {}, "source": [
    "# Example: Maximize Q0 over (EQ.RR, EQ.BB, TR.PN[1])\n",
    "Demonstrates a 3D bounded search via scipy.optimize.minimize (L-BFGS-B)."
  ]},
  {"cell_type": "code", "execution_count": null, "metadata": {}, "outputs": [], "source": [
    "import os, sys\n",
    "from pathlib import Path\n",
    "REPO = Path('..').resolve().parents[1]\n",
    "os.environ['TOTLIB_PATH'] = str(REPO / 'tot' / 'libtotapi.so')\n",
    "sys.path.insert(0, str(REPO / 'python'))\n",
    "from totlib import OptimizationProblem, ParamSpec, run_optimization, objectives\n"
  ]},
  {"cell_type": "code", "execution_count": null, "metadata": {}, "outputs": [], "source": [
    "problem = OptimizationProblem(\n",
    "    name='q0_max_3d',\n",
    "    params=[\n",
    "        ParamSpec('EQ.RR',    lower=6.0, upper=7.5, init=6.5),\n",
    "        ParamSpec('EQ.BB',    lower=4.5, upper=6.5, init=5.3),\n",
    "        ParamSpec('TR.PN[1]', lower=0.4, upper=1.0, init=0.7),\n",
    "    ],\n",
    "    objective=objectives.safe_or_inf(objectives.maximize_q0),\n",
    "    minimize=False,\n",
    "    ntmax=10,\n",
    "    max_iterations=40,\n",
    ")\n",
    "result = run_optimization(problem, backend='scipy', method='L-BFGS-B', out_dir=Path('runs/q0_max_3d'))\n",
    "print('best:', result.best_objective, result.best_params)"
  ]}
 ],
 "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.10"}},
 "nbformat": 4, "nbformat_minor": 5
}
EOF
```

- [ ] **Step 2: 多目的 notebook (optuna 必須)**

作成: `python/totlib/notebooks/03_pareto_q_taue.ipynb`

```bash
cat > /home/k-yoshimi/program/task/python/totlib/notebooks/03_pareto_q_taue.ipynb << 'EOF'
{
 "cells": [
  {"cell_type": "markdown", "metadata": {}, "source": [
    "# Example: Pareto front for (Q0, TAUE1) — requires optuna\n",
    "Uses optuna's NSGA-II for multi-objective optimization. Skip if optuna is unavailable."
  ]},
  {"cell_type": "code", "execution_count": null, "metadata": {}, "outputs": [], "source": [
    "import os, sys\n",
    "from pathlib import Path\n",
    "REPO = Path('..').resolve().parents[1]\n",
    "os.environ['TOTLIB_PATH'] = str(REPO / 'tot' / 'libtotapi.so')\n",
    "sys.path.insert(0, str(REPO / 'python'))\n",
    "import optuna\n",
    "from totlib import Totlib\n",
    "import matplotlib.pyplot as plt"
  ]},
  {"cell_type": "code", "execution_count": null, "metadata": {}, "outputs": [], "source": [
    "def objective(trial):\n",
    "    rr = trial.suggest_float('EQ.RR', 6.0, 7.5)\n",
    "    bb = trial.suggest_float('EQ.BB', 4.5, 6.5)\n",
    "    with Totlib() as tot:\n",
    "        tot.set_params({'EQ.RR': rr, 'EQ.BB': bb})\n",
    "        tot.run(ntmax=5)\n",
    "        st = tot.get_state()\n",
    "    return float(st.tr.Q0), float(st.tr.TAUE1)\n",
    "\n",
    "study = optuna.create_study(\n",
    "    directions=['maximize', 'maximize'],\n",
    "    sampler=optuna.samplers.NSGAIISampler(seed=42),\n",
    ")\n",
    "study.optimize(objective, n_trials=30)"
  ]},
  {"cell_type": "code", "execution_count": null, "metadata": {}, "outputs": [], "source": [
    "front = optuna.visualization.plot_pareto_front(study, target_names=['Q0', 'TAUE1'])\n",
    "front.show()"
  ]}
 ],
 "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.10"}},
 "nbformat": 4, "nbformat_minor": 5
}
EOF
```

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/totlib/notebooks/02_q0_maximization.ipynb \
        python/totlib/notebooks/03_pareto_q_taue.ipynb
git commit -m "docs(totlib): add Q0-maximization and multi-objective notebooks"
```

---

## Task 12: README に L-7 セクション追記

**Files:**
- Modify: `python/totlib/README.md`

- [ ] **Step 1: README 更新**

`python/totlib/README.md` の末尾の「Parameter optimization (preview)」セクションを以下に置換:

````markdown
## Parameter optimization

`totlib.optimize` provides a unified driver for grid sweep, scipy
gradient-free / bounded methods, and optuna Bayesian / multi-objective
optimization.

```python
from totlib import OptimizationProblem, ParamSpec, run_optimization, objectives
from pathlib import Path

problem = OptimizationProblem(
    name="q0_demo",
    params=[
        ParamSpec("EQ.RR", lower=6.0, upper=7.5, init=6.5),
        ParamSpec("EQ.BB", lower=4.5, upper=6.5, init=5.3),
    ],
    objective=objectives.maximize_q0,
    minimize=False,
    ntmax=10,
    max_iterations=50,
)

result = run_optimization(problem, backend="scipy", method="Nelder-Mead",
                          out_dir=Path("runs/q0_demo"))
print("best Q0 =", result.best_objective, "at", result.best_params)
```

### Backends

| Backend  | Required dependency | Notes |
|----------|---------------------|-------|
| `grid`   | (none)              | Cartesian product over `ParamSpec.grid_n` |
| `scipy`  | scipy>=1.7          | `method` defaults to `Nelder-Mead`; bounded methods supported |
| `optuna` | optuna>=3.0         | TPE single-objective; NSGA-II for multi-obj via direct `study` API |

### Result artifacts

Results are persisted to `out_dir` as:

- `problem.json` — full problem snapshot for reproducibility
- `trials.ndjson` — one JSON line per trial (params, objective, scalars, wall_time)
- `result.json` — best trial summary

See `docs/superpowers/specs/2026-04-18-tot-optimization-results-format.md`
for the schema.

### Example notebooks

- `notebooks/01_quickstart_optimize.ipynb` — grid + Nelder-Mead
- `notebooks/02_q0_maximization.ipynb` — bounded L-BFGS-B over 3 params
- `notebooks/03_pareto_q_taue.ipynb` — optuna NSGA-II Pareto front

### Installation of optimization extras

```sh
pip install -r python/totlib/requirements-optimize.txt
```
````

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/README.md
git commit -m "docs(totlib): document L-7 optimization API and notebooks"
```

---

## Task 13: `run_tests.sh` に optimization smoke test を追加

**Files:**
- Modify: `test_run/test_definitions.conf`

- [ ] **Step 1: 追加**

`test_run/test_definitions.conf` の末尾（L-6 の totlib_* の下）に追加:

```
totlib_optimize_smoke:python:python/totlib/tests/test_optimize.py:none:600:Layer 7 optimization smoke (grid/scipy)
```

- [ ] **Step 2: 実行確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh totlib_optimize_smoke
```
Expected: PASS（scipy 無いと scipy 部分が skip、grid だけは PASS する想定）。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/test_definitions.conf
git commit -m "test(tot): wire L-7 optimization smoke test into run_tests.sh"
```

---

## Task 14: 全テスト最終確認

**Files:** なし

- [ ] **Step 1: 全テスト**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh
```
Expected: 全 FAIL ゼロ。totlib 系全 PASS。

- [ ] **Step 2: 完了マーカー**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "feat(tot): L-7 parameter optimization workflow complete"
```

---

## Verification (Phase L-7 完了基準)

- [ ] `python/totlib/optimize.py` が grid / scipy / optuna 3 backend を提供。
- [ ] `objectives.py` のプリセット目的関数が unit test で全 PASS。
- [ ] `test_optimize.py` で grid + scipy が実 `libtotapi.so` 経由で動作。optuna は optional skip。
- [ ] 結果 JSON / NDJSON が仕様 (`2026-04-18-tot-optimization-results-format.md`) どおり。
- [ ] 3 つの notebook が Markdown / コード cell 構造として整っている。
- [ ] `python/totlib/README.md` に L-7 セクション + インストール手順が記載されている。
- [ ] `run_tests.sh` から `totlib_optimize_smoke` が呼べる。
- [ ] L-0..L-6 の全テストが不変。

---

## Dependencies & Fallback

**前提:** L-0..L-6 完了。Python 3.8+。

**強い前提:**
- L-3 の param dispatcher が Python 側からの set_params をエラーなく回す（L-6 Layer 3 でカバー済）。
- L-6 Layer 4 sweep が NaN/Inf 検出ゼロで完走（不安定設定があると optimizer が暴走するため）。

**Fallback:**
- scipy が利用不可 → grid backend のみで進める。README に手順明記済み。
- optuna が利用不可 → notebook 03 はマージ前に削除 or `pip install` 済み環境でのみ実行する旨を明記。
- 単一 trial が遅すぎて最適化が現実的でない → `Totlib` の incremental run（trial 間で state を持続させて差分だけ計算）を将来 phase で検討。
- TR/EQ で `set_param` が走った後、内部キャッシュ（geometry など）が古いまま → trial 開始時に **毎回 `Totlib()` を再作成** する設計も可（パフォーマンス trade-off）。L-7 の TrialRunner は同一 Totlib を使い回す高速版。問題が出たら `OptimizationProblem.fresh_each_trial=True` フラグを足して切り替えられるよう拡張。

---

## Out of scope（次フェーズ送り）

- Bayesian + サロゲートモデル統合（GP, RBF surrogate） → 別 phase
- 並列 trial 実行（multiprocessing） → 別 phase（`Totlib` がプロセス内シングル前提なので別プロセスを起動）
- 真の resume（途中で殺しても続きから） → trials.ndjson のスキャンと初期点復元の追加実装が必要
- パラメータ感度解析（Sobol indices） → 別 phase
- ハードウェアアクセラレータ対応 → 範囲外
