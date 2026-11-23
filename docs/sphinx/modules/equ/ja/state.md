# 状態

`Equ.get_state()` は `EquState` を返す. C 構造体 `equ_state_t` (`equ/equ_api.h`) を有効な
大きさで切り出したもの. `to_dict()` は大文字のキーを返す.

| フィールド | 意味 |
|---|---|
| `nr`, `nz`, `nv`, `nsu` | R, Z の格子点数, 磁気面の数, 境界の点数 |
| `mode` | run の mode (0 または 1) |
| `fct_steps`, `fct_converged`, `erreq` | 最後の FCT ループ: ステップ数, `EEQMAX` を満たしたか, 誤差 |
| `raxis`, `zaxis`, `psi_axis` | 磁気軸 [m], 軸上の磁束 |
| `xpoint_status`, `rsep`, `zsep`, `psi_sep` | X 点: 正なら見つかった. 位置 [m]. セパラトリクスの磁束 |
| `ip`, `ip_target`, `rbt` | 計算された電流 [MA], `TCUR` [MA], R B_t [T m] |
| `beta_t`, `beta_s`, `beta_j`, `li` | トロイダルベータ [%], beta* [%], beta_J, li |
| `q_axis`, `q_surf`, `q95`, `qqj` | 軸上, 表面, 95 % の q, q_J |
| `rmaj`, `rpla`, `elip`, `trig`, `el95`, `volume` | 結果の形状と体積 |
| `cvac` | コイル群 0..18 の電流 |
| `rg`, `zg` | 格子 [m] |
| `profiles` | 磁気面上 (1 = 軸): `psi`, `psit`, `pressure` [Pa], `q`, `f` (R B_t), `vol`, `rminor`, `rcentre`, `kappa`, `delta` |
| `rsu`, `zsu` | プラズマ境界 (閉じていない多角形) |

`get_psi_rz()` は ψ(R, Z) を `[i_r, i_z]` の numpy 配列で返す.

## 知っておくこと

- **FCT ループは収束するとは限らない.** `equ/example` の二つの例題では, 最後の FCT ループは
  `EEQMAX` = 1e-3 に対し `erreq` 0.2 から 0.6 で `IEQMAX` に達して終わる. プログラムはこれを
  失敗としない. ライブラリも同じ. `fct_converged` を見ること.
- **圧力の単位.** 状態の `pressure` は Pa. `write_geqdsk` がそのまま使う EQU の G-EQDSK 書き出し
  は `pres` と `pprime` を MPa で書く.
- **`ip` と `ip_target` は異なる.** `ip` は計算された平衡の電流 (プログラムは `tcur` と表示する).
  QUEST の mode 1 は目標 0.30 MA に対し 0.31 MA になる.
