"""模擬プロット PNG を生成するヘルパスクリプト。

スライド 11 の `tr.plot("RNT")` の出力イメージを matplotlib で描画し、
`assets/mock_rnt_plot.png` として保存します。pptx 生成本体から切り離して
おくことで、依存を最小化しています。
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

# 日本語フォント (Noto Sans CJK JP) を rcParams に登録
for font_path in (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
):
    try:
        font_manager.fontManager.addfont(font_path)
    except Exception:
        pass

plt.rcParams["font.family"] = ["Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def main() -> None:
    out_dir = Path(__file__).parent / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    rho = np.linspace(0.0, 1.0, 50)
    # 模擬プロファイル: 中心ピークの密度プロファイル
    rn_e = 1.0 * np.exp(-2.5 * rho ** 2) + 0.05
    rn_d = 0.92 * np.exp(-2.4 * rho ** 2) + 0.05
    rn_t = 0.05 * np.exp(-1.5 * rho ** 2) + 0.01

    fig, ax = plt.subplots(figsize=(8.0, 4.8), dpi=240)
    ax.plot(rho, rn_e, color="#1f77b4", lw=2.0, label="electron")
    ax.plot(rho, rn_d, color="#d62728", lw=2.0, label="deuteron")
    ax.plot(rho, rn_t, color="#2ca02c", lw=2.0, label="tritium")

    ax.set_xlabel(r"$\rho$ (normalized minor radius)", fontsize=11)
    ax.set_ylabel(r"density [$10^{20}\,\mathrm{m}^{-3}$]", fontsize=11)
    ax.set_title('tr.plot("RN") — 模擬出力イメージ', fontsize=12)
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 1.2)
    ax.grid(True, ls=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)

    fig.tight_layout()
    fig.savefig(out_dir / "mock_rnt_plot.png", dpi=240, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_dir / 'mock_rnt_plot.png'}")


if __name__ == "__main__":
    main()
