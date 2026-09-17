# -*- coding: utf-8 -*-
"""类别5,6,7——尾鳍摆动频率计算与绘图.py
================================================================
部位 : caudal 尾鳍 (类别 5/6/7, 6 为中间态)
逻辑 : 统一由 03_Code/02_行为频率/postproc.py 提供（`smooth_K=1`；2026-09-15 起 dedupe=True, ffill=False）
       —— 同态摆动 swing(连续两帧同为 5 或 7) + 间隔 >= 30 帧去重
       —— 人眼验证（21-1，n=1，真值源 P.QUANT/21-1_人眼.xlsx，现行口径）：
          MAE **1.00（三部位最准）** / MAPE 17.26% / AR 82.74% / r=+0.84
          〔历史 2026-09-14（旧 960+dedupe=False）：MAE 1.13 / MAPE 20.45% / AR 79.55% / r=+0.86〕
       —— 不做时序平滑（`smooth_K=1`）
⚠ `ffill` 必须保持 False：缺口前向填充会虚增 swing 事件（同数据同覆盖率下 23℃ 尾鳍 6.36→7.87，+24% 纯伪影）。
⚠ 已知性质（2026-09-15 实测，8 种定义横评）：本定义**本质是"处于摆动态时长"的代理量**
  （与该窗 5/7 时长占比 r=+0.866，与真值 r=+0.84），并非离散摆动计数。
  换成"数游程/数切换/数完整周期"等更"正统"的定义后一致性均**大幅变差**（AR 17–66%，r≈0 或为负），
  故维持现定义。其 AR 不最高的原因是**人眼基数小**（7.53）→ MAPE 被放大；按 MAE 计为三部位最准。
  类别可分性不是瓶颈：混淆矩阵对角召回 6/7/8 = 0.83/0.91/0.88，优于胸鳍 4/5 = 0.78/0.83。
⚠ 三部位频率为**辅助描述量、不作结论**（尾鳍 p=0.25 无温度效应；见 总览.md §10-10）。
输出 : 03_分析结果/尾鳍摆动频率/尾鳍摆动频率统计/{sheet}_尾鳍摆动频率统计.xlsx
       03_分析结果/尾鳍摆动频率/尾鳍摆动频率图/{sheet}_尾鳍摆动频率图.png
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline  # 平滑曲线

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postproc as pp  # noqa: E402

PART = "caudal"
input_path = pp.src_path(PART)
output_base_dir = pp.part_out_dir(PART)   # 阶段2 归口：<02_模型量化数据_GH1>/尾鳍摆动频率/
output_plot_dir = os.path.join(output_base_dir, "尾鳍摆动频率图")
output_excel_dir = os.path.join(output_base_dir, "尾鳍摆动频率统计")
os.makedirs(output_plot_dir, exist_ok=True)
os.makedirs(output_excel_dir, exist_ok=True)

xls = pd.ExcelFile(input_path)

for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name)
    if not {'帧编号', '类别'}.issubset(df.columns):
        raise ValueError(f"表格中'{sheet_name}'必须包含'帧编号'和'类别'列。")

    # === 频率计算（统一后处理：postproc / caudal 最优逻辑） ===
    result_df, _ = pp.compute(df, PART)

    output_excel = os.path.join(output_excel_dir, f"{sheet_name}_尾鳍摆动频率统计.xlsx")
    output_plot = os.path.join(output_plot_dir, f"{sheet_name}_尾鳍摆动频率图.png")
    result_df.to_excel(output_excel, index=False)

    # === 绘图 ===
    x = result_df['开始时间（秒）']
    y = result_df['尾鳍摆动频率']
    if len(x) >= 4:
        x_new = np.linspace(x.min(), x.max(), 300)
        y_smooth = make_interp_spline(x, y, k=3)(x_new)
    else:
        x_new, y_smooth = x, y

    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    plt.plot(x_new, y_smooth, linestyle='-', color='black')
    plt.title(f'Caudal fin oscillation frequency - {sheet_name}')
    plt.xlabel('Time (s)')
    plt.ylabel('Caudal fin oscillation frequency')
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.grid(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    plt.tight_layout()
    plt.savefig(output_plot, dpi=300)
    plt.close()

    print(f"[OK] '{sheet_name}' 尾鳍摆动频率统计表 -> {output_excel}")
    print(f"[OK] '{sheet_name}' 尾鳍摆动频率图像   -> {output_plot}")
