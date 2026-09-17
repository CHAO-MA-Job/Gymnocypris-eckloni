# -*- coding: utf-8 -*-
"""F1_freq_vs_temp.py（原 `04_行为作图/fig1_2_temp_response.py` 的 Fig1 部分）
—— 三部位频率 vs 温度

来源：`P.QUANT/per_fish_metrics.csv`（5 温度 × 3 尾 = 15 尾）。
版面：1 × 3（鳃盖 / 胸鳍 / 尾鳍），逐鱼散点 + mean ± SEM + 组均值连线。

⚠ **辅助描述图**（2026-09-15 裁定，见 `总览.md` §10-10 / `postproc.py` 头部）：
  三部位频率中 **胸鳍 P = 0.344、尾鳍 P = 0.248 无温度效应**，仅鳃盖 P = 0.015；
  且逐温度绝对值对后处理口径高度敏感（口径漂移 ÷ 组内 SD 达 200–750 %）。
  ⇒ 每个面板自动标注 one-way ANOVA 结果，**不显著者标 `n.s.`**，
    避免"折线连着走"被读成趋势。符号与数值仅供参考，**不作结论**。

落点：`P.SUPP/F1_freq_vs_temp.png`（PNG @900 DPI）。
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
import freq_style as S         # 阶段5 统一样式 / 配色（唯一真源）

DATA = P.QUANT
S.apply_rc_fig6b()          # 与 Fig6B_velocity_displacement.png 同款

df = pd.read_csv(os.path.join(DATA, 'per_fish_metrics.csv'))
temps = sorted(int(t) for t in df['temp'].unique())

SPECS = [('operculum', 'operculum_N10s', 'Opercular rate\n(beats / 10 s)'),
         ('pectoral', 'pectoral_N10s', 'Pectoral fin beat\n(beats / 10 s)'),
         ('caudal', 'caudal_N10s', 'Caudal fin beat\n(beats / 10 s)')]

fig, axes = plt.subplots(1, 3, figsize=(9.0, 3.0))
for ax, (key, col, ylab) in zip(axes, SPECS):
    # 散点按温度梯度着色（与 Fig6B 嵌图同）；均值折线用灰（与 Fig6B 折线同）
    S.bar_scatter(ax, df, col, color=S.C_LINE, temp_colors=True)
    ax.set_title(S.PART_LABELS[key], fontsize=10)    # 面板题（身份），非面板字母
    ax.set_xlabel('Temperature (\u00b0C)')
    ax.set_ylabel(ylab)
    _, p, _ = S.anova_by_temp(df, col)
    S.sig_note(ax, p)                                # 显著性注记（§9 允许）
    for sp in ax.spines.values():
        sp.set_linewidth(1.2)

fig.tight_layout()
# 描述性声明（纯英文，防 CJK 缺字）
fig.text(0.5, -0.045,
         'Descriptive only \u2014 no ANOVA effect across temperatures for pectoral '
         'or caudal (n = 3 per temperature).',
         ha='center', va='top', fontsize=7, color='0.35')
S.save(fig, 'F1_freq_vs_temp.png', supp=True)

for key, col, _ in SPECS:
    _, p, agg = S.anova_by_temp(df, col)
    print('%-10s P=%.4f  mean=%s  sem=%s'
          % (key, p, np.round(agg['mean'].to_numpy(float), 2),
             np.round(agg['sem'].to_numpy(float), 2)))
