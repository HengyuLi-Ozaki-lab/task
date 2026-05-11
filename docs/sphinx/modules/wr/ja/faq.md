# FAQ — `wr` 固有

## Q1. `wr` は何をするモジュール?

`wr` (Wave Ray) は **幾何光学的レイトレース** ソルバです. プラズマ中の
電磁波 (RF) の伝搬を, 屈折率テンソルで決まる ray 方程式 (Hamiltonian
形式) に従って積分します.

主な用途:

- **ECRH/ECCD** (電子サイクロトロン共鳴加熱・電流駆動) のパワー堆積位置
- **LH** (低域混成波) のパワー吸収解析
- **NBI** の中性化 + イオン化過程
- **fast wave / Alfvén wave** など他の RF 加熱方式

## Q2. `tr`/`ti`/`fp` と何が違う?

| | `tr`/`ti` | `fp` | `wr` |
|---|---|---|---|
| **方程式** | 流体 + 補助物理 | Fokker-Planck (5D) | **ray 方程式** |
| **時間発展** | あり | あり | **なし** (空間積分) |
| **`run` 引数** | `ntmax` | `ntmax` | **`nray_request`** |
| **出力** | プロファイル | モーメント | レイ軌跡 + 吸収位置 |

`wr` は **入射波が決まったときに, それがどこで吸収されるか** を計算
するモジュールで, 時間発展しません. `run(nray_request=N)` で N 本の
光線を独立にトレースします.

## Q3. `nray_request` の意味は?

`run(nray_request=N)` で **N 本のレイ** を要求します. ただし設定済みの
`NRAYMAX` パラメータが上限なので, 実際にトレースされる本数は
`min(nray_request, NRAYMAX)` です.

`nray_request=0` を指定すると `NRAYMAX` の値を使います.

## Q4. レイが途中で止まってしまう

可能性:

- `NSTPMAX` (最大ステップ数) に達した — `set_param("NSTPMAX", 50000)` で増やす
- `UUMIN` (最小残存パワー閾値) に達した — `UUMIN` を下げる
- 計算領域 (`Rmax_wr`, `Rmin_wr`, `Zmax_wr`, `Zmin_wr`) を出た
- プラズマカットオフに到達 (波が伝搬できない密度に到達)

`state.nstp_end[i]` で各レイの終端ステップ番号がわかります.

## Q5. ピークパワーが 0 になる

レイが吸収されない領域を通り抜けただけ可能性があります. 確認:

- 周波数 `RF` が共鳴 (例: ECRH なら electron cyclotron 周波数) と合う?
- 入射角度 `RNZI`, `RNPHII` が適切?
- `MODELP` (波動モデル選択) が物理的に正しい?

## Q6. 結果が `wrx2` (CLI 版) と一致しない

回帰テスト `wrlib_equivalence` を実行:

```bash
bash test_run/run_tests.sh wrlib_equivalence
```

tolerance は `1e-10`. 許容値以上ずれる場合は登録漏れのパラメータを確認.

## Q7. `wr` と `wrx` どちらを使うべき?

- **`wr` (geometric optics)**: 高速, シンプルなレイトレース. ビーム広がり
  を `NRAYMAX` 本のレイで近似. 多くのケースで十分.
- **`wrx` (extended)**: beam tracing — ビームの有限幅を直接モデル化. EC や
  LH で集束ビームの解析が必要なときに使う. 計算コスト高.

不明な場合は **まず `wr` で十分**, 結果が荒すぎたら `wrx` を検討.

## Q8. NumPy が必要?

**不要**. `WrState` は Python の `list` です. NumPy を使いたい場合は
`import numpy as np; np.array(state.pwr_nrs)` で変換できます.
