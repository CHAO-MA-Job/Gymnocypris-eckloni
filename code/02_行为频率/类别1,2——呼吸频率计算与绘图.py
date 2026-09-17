# -*- coding: utf-8 -*-
"""类别1,2——呼吸频率计算与绘图.py
================================================================
部位 : operculum 鳃盖 (类别 1/2)
逻辑 : 统一由 03_Code/02_行为频率/postproc.py 提供（`smooth_K=1`；2026-09-15 起 dedupe=True, ffill=False）
       —— 逐行游程压缩 → 周期法 cycle(1→2→1 / 2→1→2)，中间态连续 >= 2 帧记一次
       —— 人眼验证（21-1，n=1，真值源 21-1_人眼.xlsx，现行口径）：
          MAE 1.13 / MAPE 5.78% / AR 94.22% / r=+0.35
          〔历史 2026-09-14（旧 960+dedupe=False）：MAE 0.77 / MAPE 4.06% / AR 95.94% / r=+0.72〕
       —— 不做时序平滑（`smooth_K=1`）
⚠ 三部位频率为**辅助描述量、不作结论**（胸鳍 p=0.34、尾鳍 p=0.25 无温度效应；见 总览.md §10-10）。
本脚本只负责：读表 → 调 postproc → 写逐鱼统计 xlsx + 出图。
输出 : 03_分析结果/呼吸频率/呼吸频率统计/{sheet}_呼吸频率统计.xlsx
       03_分析结果/呼吸频率/呼吸频率图/{sheet}_呼吸频率图.png
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline  # 平滑曲线

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postproc as pp  # noqa: E402

PART = "operculum"
input_path = pp.src_path(PART)
output_base_dir = pp.part_out_dir(PART)   # 阶段2 归口：<02_模型量化数据_GH1>/呼吸频率/
output_plot_dir = os.path.join(output_base_dir, "呼吸频率图")
output_excel_dir = os.path.join(output_base_dir, "呼吸频率统计")
os.makedirs(output_plot_dir, exist_ok=True)
os.makedirs(output_excel_dir, exist_ok=True)

xls = pd.ExcelFile(input_path)

for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name)
    if not {'帧编号', '类别'}.issubset(df.columns):
        raise ValueError(f"表格中'{sheet_name}'必须包含'帧编号'和'类别'列。")

    # === 频率计算（统一后处理：postproc / operculum 最优逻辑） ===
    result_df, _ = pp.compute(df, PART)

    output_excel = os.path.join(output_excel_dir, f"{sheet_name}_呼吸频率统计.xlsx")
    output_plot = os.path.join(output_plot_dir, f"{sheet_name}_呼吸频率图.png")
    result_df.to_excel(output_excel, index=False)

    # === 绘图 ===
    x = result_df['开始时间（秒）']
    y = result_df['呼吸频率']
    if len(x) >= 4:
        x_new = np.linspace(x.min(), x.max(), 300)
        y_smooth = make_interp_spline(x, y, k=3)(x_new)
    else:
        x_new, y_smooth = x, y

    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    plt.plot(x_new, y_smooth, linestyle='-', color='black')
    plt.title(f'Breathing Frequency - {sheet_name}')
    plt.xlabel('Time (s)')
    plt.ylabel('Breathing Frequency')
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.grid(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    plt.tight_layout()
    plt.savefig(output_plot, dpi=300)
    plt.close()

    print(f"[OK] '{sheet_name}' 呼吸频率统计表 -> {output_excel}")
    print(f"[OK] '{sheet_name}' 呼吸频率图像   -> {output_plot}")
