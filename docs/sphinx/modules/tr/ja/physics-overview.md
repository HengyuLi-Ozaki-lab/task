# 物理の概観

```{admonition} このページの位置付け
:class: note

導出ではなく **方向付け (orientation)** のページです. TR が
何を解くか, どの近似を置いているか, 各主張がコードのどこに
あるか, を素描します. 想定読者は輸送モデリングに初めて触れる
大学院生・若手研究者. 方程式は名前で呼び, 数式は書きません —
数学的な詳細はトカマク輸送の教科書 (下の "さらに読むために"
参照) を参照してください.
```

---

## TR が解いていること

TR は flux-surface 平均化された格子上で 1 次元の半径方向輸送
方程式系を解きます. 出力は半径プロファイル (密度, 温度, 電流,
安全係数 `q`) と {doc}`state` で定義される派生スカラー
診断 (`WPT`, `TAUE1`, `TAUE2`, `BETAN` など) の時間発展です.

方程式の組立と陰的時間ステップ求解は時間ステップごとに行います.
ソース項と輸送係数の組立は `tr/trcalc.f90:TRCALC` で
(beam, RF, 核融合, ohmic, 放射等の寄与をまとめている),
陰的ステップのソルバ呼び出しは `tr/trexec.f90:67-99` に
あります: `BANDRD` が line 69, LAPACK バンドソルバ経路の
`DGBTRF` / `DGBTRS` / `DGBSV` が line 81 / 86 / 96 です
(line 65 の `'Solve matrix equation'` コメントブロックは
そのすぐ上にあります).

このページでは微分方程式の symbolic 表現は意図的に書きません.
導出が必要な読者は輸送理論の教科書を参照してください.

---

## 空間格子と境界条件

- **半径座標.** TR の格子は flux-surface label (`rho` と書か
  れる正規化半径座標) で 1 次元です. セル数は `NRMAX` で,
  コンパイル時上限は `TR_MAX_NRMAX = 500` (`tr/tr_api.h`).
  プロファイル配列は長さ `NRMAX`. メッシュレイアウトの詳細
  (どの配列がセル中心 / セル端にあるか) は {doc}`design` に
  あり, このページは「半径軸が 1 本ある」「すべての半径
  プロファイルが長さ `NRMAX` の配列である」という方向付け
  だけを与えます.

- **内側境界.** 磁気軸 (配列 indexing で `NR = 1`) では
  正則性 / 対称性条件が自動で適用されます. ユーザ設定不要.

- **外側境界.** プラズマ端 (`NR = NRMAX`) では境界値が
  registry パラメータ経由で与えられます (プロファイルの
  edge pinning, Dirichlet 風). 設定可能な surface 値は
  {doc}`parameters` 参照. TR は edge / SOL 専用の輸送問題
  を別に解くわけではありません (下の "TR が向く領域" 参照).

- **発展量と parameterize される量.** 時間発展するのは
  プロファイル配列 (密度 / 温度 / 電流). **輸送係数** は
  inner iteration ごとに現在のプロファイルから再計算
  されます (Codex round-3 で `tr/trexec.f90` を確認:
  inner loop entry が line 56, matrix solve が 62-99,
  profile update が 160-282, `TRCALC` 再計算が 298). 加熱源,
  NB beam deposition, RF パワープロファイル等の駆動も
  各ステップで再計算されてソース項として入ります.

---

## TR が解ける方程式

TR は 7 個の輸送方程式スイッチ (`MDLEQ*` 群) を持ち,
それぞれ独立に ON/OFF できます. デフォルトは
`tr/trinit.f90:687-695` 由来:

| Flag | 量 | Default | 注 |
|---|---|---|---|
| `MDLEQB` | ポロイダル B (電流拡散 / `q` プロファイル発展) | 1 (ON) | |
| `MDLEQT` | 温度 (熱拡散) | 1 (ON) | |
| `MDLEQN` | 粒子密度 (イオン種ごと) | 0 (OFF) | |
| `MDLEQU` | 回転 | 0 (OFF) | |
| `MDLEQZ` | 不純物 | 0 (OFF) | |
| `MDLEQ0` | 中性粒子 | 0 (OFF) | |
| `MDLEQE` | 電子密度の扱い — 0 / 1 / 2 モード (boolean ではない) | 0 (OFF) | 各モードが異なる電子 / イオン密度方程式の扱いに対応 (`tr/trprep.f90:407-415`, `tr/trexec.f90:180-201`); `MDLEQN = 1` のときのみ意味を持つ (`tr/trprep.f90:202-203`). モードごとの挙動はソースを参照. |

**箱から出してそのままの状態 (デフォルト ON 集合) は
`{MDLEQB, MDLEQT}`** — TR は電流と温度だけを発展させ,
粒子・回転・不純物・中性は対応する flag を ON にしない限り
発展しません. ユーザ向けコントロールは {doc}`parameters` 参照.

---

## 近似

### Flux-surface 平均 (1 次元半径方向)

TR は「すべてのプロファイル量が単一の半径座標で indexing
される」という意味で 1 次元です. 2 次元の equilibrium
ジオメトリは `eq` モジュールから BPSD ブローカー経由で
入ってきます: `tr_bpsd_get` (`tr/trbpsd.f90:160-183`) が
device + plasma の量を pull し, equilibrium / metric の pull
は `tr/trbpsd.f90:213-245` で geometry-aware な `MODELG`
設定のときだけ走ります (analytic-equilibrium 経路では skip).
全体像は "1.5 次元" (1 次元輸送 + 2 次元 equilibrium) で,
標準的な輸送コードのスタイルです.

### 準定常 equilibrium

equilibrium は輸送よりも遅い時間スケールで変動するという
仮定を置いており, BPSD 結合は各輸送ステップ内で
`eq.run()` push → tr pull の流れで動きます. TR は自己
無撞着な動的 equilibrium を解いていません. equilibrium が
急速に変化するシナリオ (transient disruption 研究等) では,
ユーザは `eq` の再走頻度を上げるか, この準定常近似を受け入れる
必要があります.

### 輸送モデル選択肢の地図

TR の輸送係数は複数の独立なソースから来ており, それぞれ独自
のモデル選択 flag を持ちます. 設計時に `tr/trinit.f90` と
`tr/tr_param_registry.f90` で確認した layout:

**公開 parameter registry に露出されている選択肢** (実行時に
`tr.set_param` から設定可能,
`tr/tr_param_registry.f90:43-49,124-128`):

- **`MDLKAI` — 乱流熱輸送.** 乱流 (anomalous) 熱輸送モデル
  を選択. 選択肢は CDBM, IFS-PPPL, GLF23, mixed Bohm /
  gyro-Bohm その他. 全リストは {doc}`appendix-mdlkai` 参照.
- **`MDLETA` — 抵抗率.** 電流拡散 (`MDLEQB` 方程式) で使う
  抵抗率モデルを選択.
- **`MDLAD` — 粒子拡散 (モデルファミリ).** 粒子拡散モデル
  を選択. Hinton-Hazeltine 解析形を含む複数の variant を
  持つ (`tr/trinit.f90:290-295`,
  `tr/trcoef_adhoc.f90:35-45`); 単一の ad-hoc スイッチでは
  なく **モデルファミリ** の選択です.
- **`MDLAVK` — thermal pinch.** 熱 pinch (内向き熱流の
  対流成分) モデルを選択. 文献では "anomalous V_K" / thermal
  pinch と呼ばれるもの. *これは neoclassical の selector では
  ない* — 過去のドラフトで紛らわしい命名から誤認していた
  経緯がある (`tr/trinit.f90:296-308`, `parameters.md` の
  該当エントリで意味確認).

**Fortran ソースのみ (`tr/trinit.f90` のコンパイル時デフォルト
で固定)**:

- **`MDLKNC` — neoclassical 熱伝導 / 抵抗率の処理.**
  デフォルトは `tr/trinit.f90:306`.
- **`MDNCLS` — NCLASS スタイルの neoclassical モジュールを
  ON/OFF** (標準的な NCLASS 新古典ライブラリ). デフォルトは
  `tr/trinit.f90:324` と `tr/trinit.f90:717`.

これら 2 つが TR で実際の neoclassical の knob ですが,
`tr.set_param` からは触れません. 変えたい上級ユーザは
`tr/trinit.f90` を直接編集してリビルドする必要があります.

このページの役割は selector landscape の **地図** を読者に
渡すことで, 各 knob がどの物理を狙うかを把握してもらう
ことです. 実行時 settable な選択肢は {doc}`parameters` と
{doc}`appendix-mdlkai`, registry 非登録のものは {doc}`design`
が入口です.

---

## TR が向く領域

**時間スケール.** TR は輸送時間スケールのコードです. 自然
な時間ステップは ms オーダー, 総走行時間は秒オーダー
(`tr/trinit.f90:374,376` のデフォルト `DT = 0.01 s`,
`NTMAX = 100`, total `1.0 s` と整合的). より高速の現象は
解像できません.

**TR が簡略化モデルで扱うもの** — これらは現象論的・縮約
モデルで, 第一原理 MHD ではありません:

- **Sawtooth 振動.** `MDLST` selector
  (`tr/trinit.f90:392-402`). 混合は `TRSAWT` で実装
  (header が `tr/trcalc.f90:1072`,
  `tr/trloop.f90:59-65` から呼ばれる) され,
  温度 / 密度 / `q` の再分配ステップは
  `tr/trcalc.f90:1127-1150` にあります. 現象論的な
  reconnection / mixing モデルで, kink モードを解いている
  わけではありません.
- **ELM 縮約.** `MDLELM` selector (`tr/trinit.f90:720-729`).
  ELM 周波数 / ELM エネルギー損失の縮約モデルで, 第一原理
  ペデスタル安定性計算ではありません.

**TR がまったく扱わないもの:**

- Edge / pedestal 物理 (第一原理的な意味で). ETB 専用の
  輸送障壁は解かない; 境界条件は最外側半径セルに与える.
- 一般の MHD 不安定性 (kink, tearing, NTM, RWM 等) — 上記の
  簡略化された sawtooth と ELM 縮約のみが存在する.
- 3 次元効果 (stellarator ジオメトリ, resonant magnetic
  perturbation) — TR は flux-surface 平均によって
  axisymmetry を仮定している.
- 高速 (gyrokinetic スケール) 揺動を直接解くこと — これらは
  乱流輸送モデルから輸送係数として取り入れられるのみ.

関連オープン輸送コード (ASTRA, JETTO-SANCO, TRANSP) との
比較表は {doc}`limitations-and-references` 参照. 走行時の
安定性・診断ガイダンスは
{doc}`numerical-stability-and-diagnostics` 参照.

---

## さらに読むために

このセクションは **一般的な** トカマク輸送の標準文献を初学者
向けの読書出発点として並べたものです. TASK 固有の出版物と
関連オープンコードとの比較は {doc}`limitations-and-references`
の references 節を参照してください.

下記は author + title (および canonical な edition がある場合
のみ edition 番号) を pointer 形式で挙げたもので, **publisher
と year は意図的に省いています**. 複数の版・重版があり, ページ
が「これ」と特定の版を主張すると過剰主張になるためです.
authoritative な bibliographic citation ではなく, 読書出発点
として扱ってください.

- J. Wesson, *Tokamaks* (Oxford University Press, 4th
  edition) — equilibrium, 輸送, 安定性, 加熱, 診断を網羅
  する百科全書的教科書.
- R. D. Hazeltine & J. D. Meiss, *Plasma Confinement* —
  TR のようなコードの背後にある輸送理論に集中.
- J. P. Freidberg, *Ideal Magnetohydrodynamics* — equilibrium
  と安定性の基礎; TR が使う flux-surface 座標はこの系統の
  解析から来ている.

このページはこれらの本から個別の方程式やページ番号を引用
していません — bibliographic pointer です.
