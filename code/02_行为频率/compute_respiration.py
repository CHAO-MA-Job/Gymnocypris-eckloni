# -*- coding: utf-8 -*-
"""compute_respiration.py —— 呼吸（鳃盖）频率【一致性校验】
==========================================================================
逻辑已**不在本脚本实现**，统一由 postproc.py 的 operculum 配置提供
（`smooth_K=1`；2026-09-15 起 dedupe=True, ffill=False；周期法 cycle, min_dur=2；
现行 21-1 人眼 AR=94.22%, r=+0.35；历史 2026-09-14 为 AR=95.94%, r=+0.72）。
本脚本作用：用同一逻辑重算 → 与权威合并表**逐格比对**，确认口径一致。
输入 : P.QUANT/2_鳃盖.xlsx
权威 : P.QUANT/呼吸频率.xlsx（由 combine_15_sheets.py 合并）
输出 : **不落盘**（2026-09-15 起）。此前输出 `P.QUANT/呼吸频率_重算.xlsx`，
       该文件与权威表**逐格完全相同**（15 sheet × 2811 格，0 处差异）、且无任何脚本读取，
       属纯冗余 → 已停止产出。校验结论以本脚本打印的逐格 MAE / r 为准。
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postproc as pp  # noqa: E402

PART = "operculum"
RES_DIR = pp.SRC_DIR     # 阶段2 归口：与频率合并表同根（02_模型量化数据_GH1）
FREQ_COL = pp.PARTS[PART]["col"]
REF_XLSX = os.path.join(RES_DIR, "呼吸频率.xlsx")


def main():
    ref = pd.ExcelFile(REF_XLSX) if os.path.exists(REF_XLSX) else None
    diffs, xs, ys = [], [], []
    print(f"[{FREQ_COL}] 重算 vs 权威合并表（只校验，不落盘）")
    for sh, df in pp.iter_sheets(PART):
        res, _ = pp.compute(df, PART)
        a = res[FREQ_COL].to_numpy(float)
        if ref is not None and sh in ref.sheet_names:
            v = pd.to_numeric(ref.parse(sh)[FREQ_COL], errors="coerce").to_numpy(float)
            m = min(len(a), len(v))
            diffs.append(np.abs(a[:m] - v[:m]))
            xs.append(a[:m])
            ys.append(v[:m])
            r = np.corrcoef(a[:m], v[:m])[0, 1] if m > 2 else float("nan")
            print(f"  {sh:>8} 重算均值={a.mean():7.2f} 权威均值={np.nanmean(v[:m]):7.2f} "
                  f"MAE={np.mean(np.abs(a[:m] - v[:m])):4.2f} r={r:.3f}")
        else:
            print(f"  {sh:>8} 重算均值={a.mean():7.2f}")
    if diffs:
        D = np.concatenate(diffs)
        X = np.concatenate(xs)
        Y = np.concatenate(ys)
        r_all = np.corrcoef(X, Y)[0, 1] if X.size > 2 else float("nan")
        print("[校验汇总] sheet=%d  逐格 MAE=%.4f  r=%.6f  最大绝对差=%.4g"
              % (len(diffs), float(np.nanmean(D)), float(r_all),
                 float(np.nanmax(D))))
        print("           逐格完全一致 → 单一实现、无口径漂移" if np.nanmax(D) == 0
              else "           ⚠ 存在差异，须排查")
    else:
        print("[警告] 未找到权威合并表，无法比对:", REF_XLSX)


if __name__ == "__main__":
    main()
