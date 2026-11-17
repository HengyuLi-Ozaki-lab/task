# 入力パラメータの指定方法

4 通りあります.

## 方法 A — スカラー (`set_param`)

`tr` と違い, `eq` の `set_params(**kwargs)` はスカラー専用 (位置引数で
mapping を受ける形もサポート, 下記 B 参照). 通常は 1 つずつ
`set_param("NAME", value)`:

```python
eq.set_param("RR", 6.5)
eq.set_param("MODELG", 3)      # int は double で渡して OK
eq.set_param("RIPFC[1]", 0.5)  # PF コイル電流 (1-origin, 1..10)
```

```{admonition} `PSIB` だけは 0-origin
:class: warning

Fortran 宣言が `REAL(KIND=8) :: PSIB(0:5)` で 0 から始まるため, 添字も
`PSIB[0]` 〜 `PSIB[5]` です. 添字無しの裸の `"PSIB"` はレジストリで
明示的に拒否されます (`EqlibInvalidParamError`). 他の 1-D 配列
(`RIPFC`, `RPFC`, `ZPFC`, `WPFC`) は 1-origin です.
```

## 方法 B — 一括 dict / kwargs (`set_params`)

```python
eq.set_params(RR=6.5, BB=5.3, MODELG=3)       # kwargs 形式
eq.set_params({"RR": 6.5, "BB": 5.3})          # 位置引数 mapping 形式
```

## 方法 C — 文字列パラメータ (`set_param_str`)

ファイル名 (`KNAMEQ` などの `KNAM*`) は `CHARACTER(LEN=80)` で, **専用 API** が必須です.
`set_param` には渡せません.

```python
eq.set_param_str("KNAMEQ",  "eqdata.ITER01")
eq.set_param_str("KNAMWR",  "wrdata.dat")
```

対応するキーは **7 個**:
`KNAMEQ`, `KNAMEQ2`, `KNAMWR`, `KNAMWM`, `KNAMFP`, `KNAMFO`, `KNAMPF`.

## 方法 D — 事前検証 (`validate`)

```{admonition} 新機能 (PR #164)
:class: important

`validate()` はパラメータを `run()` に渡す前に一括検査する API です.
グリッド寸法の整合性, ファイル不在などを診断 dataclass のリストで
返します. パラメータ設定後, `run()` の前に呼ぶのが推奨フローです.
```

```python
from eqlib import Eq, EqDiagCode

with Eq() as eq:
    eq.set_params(RR=6.5, BB=5.3, RIP=1.5, MODELG=3)
    eq.set_param_str("KNAMEQ", "eqdata.missing")  # 存在しないファイル

    diags = eq.validate()
    for d in diags:
        print(f"[{EqDiagCode(d.code).name}] {d.param}: {d.message}")
    if diags:
        raise SystemExit("fix the diagnostics before running")

    eq.run()  # mode=1 (ファイル読み込み. MODELG=3: TASK/EQ 形式)
```

Grad-Shafranov 求解には `mode=0` を渡します:

```python
with Eq() as eq:
    eq.set_params(RR=3.0, RA=1.0, BB=3.0, RIP=1.5)  # MODELG=2 既定
    diags = eq.validate()
    if diags:
        raise SystemExit("fix the diagnostics before running")
    eq.run(mode=0)  # EQCALC (EPSEQ まで反復) + EQCALQ
```

診断コードは `tr` と共通の 5 種類:

| コード | 意味 |
|---|---|
| `OUT_OF_RANGE`           | 値が許容範囲外 |
| `INCONSISTENT_PAIR`      | 関連パラメータ対の不整合 |
| `OUT_OF_RANGE_AFTER_DEP` | 依存パラメータ評価後の範囲逸脱 |
| `FILE_MISSING`           | 読み込みが読むファイルが無い, またはその名前 (`KNAMEQ`) が空 |
| `MISSING_REQUIRED`       | 必須パラメータが未設定 |

`eq_validate` は **10 個のグリッド寸法** (`NSGMAX`, `NTGMAX`, `NUGMAX`,
`NRGMAX`, `NZGMAX`, `NPSMAX`, `NRMAX`, `NTHMAX`, `NSUMAX`, `NRVMAX`) を
コンパイル時の上限と比べ, 読み込み (`run(mode=1)`) が読むファイルがあることを
チェックします: `MODELG` 3, 5, 8, 9, 25 では `KNAMEQ` が空でなくファイルを指す
こと (2 つのファイルを読む 8 では `KNAMEQ2` も), `MODELG` 15 では `KNAMEQ` の代わりに読む固定ファイル `eqdb.dat` があること
(`MODELG` として報告). 名前は読み込みと同じく, `validate()` の時点の作業
ディレクトリから探します. Grad-Shafranov 求解 (`run(mode=0)`.
ファイル形式以外のすべての `MODELG` はこれで解く) ではさらに次をチェックします:

- 壁がプラズマを囲む: `RB >= RA` (`INCONSISTENT_PAIR`);
- プラズマ電流が負でない: `RIP >= 0` (`OUT_OF_RANGE`. 負の電流は `run(0)`
  が拒否します);
- `MDLEQF >= 10` でソルバーが箱 `RGMIN`..`ZGMAX` を読むとき
  (`OUT_OF_RANGE_AFTER_DEP`): `RR` が `RGMIN`..`RGMAX` の中にある (磁気軸は
  そこから出発し, 箱の中になければならない), `RGMAX` が外縁 `RR + RA` より
  小さくない (小さいと解はそこでプラズマを切る. 磁気軸より小さければ失敗する), `ZGMIN < 0 < ZGMAX`
  (磁気軸は `Z = 0` にある). プラズマのそれ以外の部分は箱の外にあっても
  結果は同じです. 事前に見えない失敗が二つあります: 磁気軸は解く間に動く
  (シャフラノフシフトで外へ, 三角度で内へ. `RDLT = 0.4` では `RR` より内側で
  止まるので `RGMIN = RR` は失敗する) ことと, 丸め誤差の範囲 (`1e-14`) で
  0 に近い Z の境界は 0 と同じく失敗することです.

`validate()` は `MODELG` で判断します: ファイル形式 (`MODELG` 3, 5, 8, 9, 15,
25) は `run(mode=1)` で読み込むものとみなし, 幾何はファイルから得るので,
これらの幾何チェックは行いません (ファイル形式を `run(mode=0)` で解く場合も
行いません). `MDLEQF >= 10` の読み込みも, ファイルから求めた磁気軸を箱に
収めようとします. 軸が箱の外にあると読み込みは失敗し, そのエラー
(`Eq.last_error()`) が軸の探索の終点と箱を示します.
