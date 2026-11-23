# クイックスタート

## ビルド

```bash
make -C equ libequapi.so          # TASK のチェックアウトで. bpsd はその隣
export PYTHONPATH=$PWD/python
```

## 例題を実行する

例題は `equ/example` にある. ネームリストは `KNAMCOIL` でコイルファイルを作業ディレクトリ
からの相対パスで指定する. `equparm.quest` は `coildata` を指す.

```python
import os, shutil, tempfile
from equlib import Equ

work = tempfile.mkdtemp()
shutil.copy("equ/example/equparm.quest", f"{work}/equparm")
shutil.copy("equ/example/coildata.quest", f"{work}/coildata")
os.chdir(work)

with Equ() as equ:
    equ.read_parm("equparm")          # &EQU ネームリスト
    assert equ.validate() == []       # 入力のすべての検査
    equ.run()                         # mode 1: プログラムの R
    st = equ.get_state()
    print(st.ip, st.q_axis, st.raxis, st.fct_converged)
    equ.write_geqdsk("quest.geqdsk")  # プログラムの E
```

`python python/equlib/examples/quickstart.py` が同じことをする.

## 入力を変える

```python
with Equ() as equ:
    equ.read_parm("equparm")
    equ.set_param("TCUR", 0.28)        # MA
    equ.set_param("CVACST[3]", -0.25)  # コイル群の目標電流
    equ.run()
```

各 run は設定された入力から始まる. run の後の `set_param` は, ソルバが書き換えた値ではなく
入力を変える.

## エラー

| 例外 | 起きるとき |
|---|---|
| `EqulibInvalidParamError` | 未知の名前, レジストリが受け付けない値, `validate` の検査, 平衡のない `get_state` |
| `EqulibCalculationFailedError` | 解が失敗した (例: 等値線の出発点が見つからない). ハンドルはその後も使える |
| `EqulibNotImplementedError` | `run(mode)` の mode が 1 より大きい |

`equ.last_error()` がライブラリの理由を返す. 例外もそれを含む.
