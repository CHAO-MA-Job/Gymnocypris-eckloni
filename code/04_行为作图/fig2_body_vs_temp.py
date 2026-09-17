# -*- coding: utf-8 -*-
"""fig2_body_vs_temp.py（原 `fig1_2_temp_response.py` 的 Fig2 部分）
—— 全身速度 / 累计位移 vs 温度（**运动学简版**）

来源：`P.QUANT/per_fish_metrics.csv`（5 温度 × 3 尾 = 15 尾）。
版面：1 × 2（速度 / 累计位移），逐鱼散点 + mean ± SEM + 组均值连线。

⚠ 与 `fig6b_kinematics.py`（Fig.6B 正图）**同源重叠**：本图是其简版。
⚠ 速度与位移是**同一维度**（r = 0.9967, r² = 0.9934；`位移 = 速度 × 时长` 为几何恒等式），
  并列作两个面板只是重复呈现，**不构成两条独立证据**（见 `总览.md` §10-2）。
⚠ 频率类指标**不在此图**（已迁至 `04_Outputs/05_频率计算/`）。

落点：`P.FIG/Fig2_body_vs_temp.png`（PNG @900 DPI）。
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口

OUT = P.FIG
P.ensure(OUT)

C_VEL = '#4C72B0'   # 速度（蓝）
C_DIS = '#708090'   # 位移（灰）

plt.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'],
    'font.size': 9,
    'axes.linewidth': 0.9,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'xtick.direction': 'out',
    'ytick.direction': 'out',
    'savefig.dpi': 900,
})

df = pd.read_csv(os.path.join(P.QUANT, 'per_fish_metrics.csv'))
temps = sorted(int(t) for t in df['temp'].unique())

SPECS = [('velocity_cm_s', C_VEL, 'Velocity (cm / s)'),
         ('displacement_cm', C_DIS, 'Cumulative displacement (cm)')]

fig, axes = plt.subplots(1, 2, figsize=(5.2, 2.7))
for ax, (col, color, ylab) in zip(axes, SPECS):
    g = df.groupby('temp')[col]
    m = g.mean().reindex(temps).to_numpy(float)
    s = g.sem().reindex(temps).to_numpy(float)
    for i, t in enumerate(temps):
        y = df.loc[df['temp'] == t, col].to_numpy(float)
        ax.scatter(np.full(len(y), i) + np.linspace(-0.08, 0.08, len(y)), y,
                   s=18, facecolor=color, edgecolor='black', linewidth=0.4,
                   alpha=0.85, zorder=3)
    ax.errorbar(range(len(temps)), m, yerr=s, fmt='o', color=color,
                ecolor=color, capsize=3, ms=6, mfc='white', mew=1.5,
                elinewidth=1.3, zorder=4)
    ax.plot(range(len(temps)), m, '-', color=color, lw=1.2, alpha=0.7, zorder=2)
    ax.set_xticks(range(len(temps)))
    ax.set_xticklabels([str(t) for t in temps])
    ax.set_xlabel('Temperature (\u00b0C)  (n = 3)')
    ax.set_ylabel(ylab)

fig.tight_layout()
p = os.path.join(OUT, 'Fig2_body_vs_temp.png')
fig.savefig(p, dpi=900, bbox_inches='tight')
plt.close(fig)
print('[OK]', p)
