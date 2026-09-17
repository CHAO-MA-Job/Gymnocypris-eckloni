# -*- coding: utf-8 -*-
"""F2_waveform.py —— 频率波形（手稿 Fig.6A）

**版面照 `05_figues/Fig7A_Objective_ANOVA_HeatColors.png` 绘制**：
  · 3 行 × 5 列 —— 行 = 部位（鳃盖 / 胸鳍 / 尾鳍），列 = 温度（16 / 19 / 21 / 23 / 25 ℃）；
  · 每格 = 该温度下该部位的 **mean 折线 + SD 带**；颜色 = **温度梯度**（不是部位色）；
  · 列标题 = 温度；行身份 = 首列 y 轴标签（部位名 + Frequency）；
  · 每格右上角 = 该温度的 **Tukey HSD 紧凑字母**（按部位在 5 个温度间做 CLD）；
  · 统一 x（0–600 s）与 y 轴范围，四边细边框。

来源：`P.QUANT/{呼吸频率,胸鳍摆动频率,尾鳍摆动频率}.xlsx`（各 15 sheet，窗 = 10 s）。
⚠ 描述性图（`总览.md` §10-10）：频率为辅助描述量、不作结论；字母仅供参考（n = 3/温度）。
落点：`P.FREQ/F2_waveform.png`（PNG @900 DPI）。
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

S.apply_rc_fig6b()          # 与 Fig6B_velocity_displacement.png 同款
TEMPS = S.TEMPS

# ---------------------------------------------------------------- 取数
long = S.load_freq_long()
agg = (long.groupby(['part', 'temp', 'time'])['val']
       .agg(['mean', 'std']).reset_index())

# 逐部位：按逐鱼均值的 Tukey CLD → 每个温度一个字母
pf = S.load_per_fish()
letters = {p: S.sig_letters([pf.loc[pf['temp'] == t, S.PF_COL[p]].to_numpy(float)
                             for t in TEMPS])
           for p in S.PARTS}

YMAX = float((agg['mean'] + agg['std'].fillna(0)).max()) * 1.10
XMAX = float(agg['time'].max())

# ---------------------------------------------------------------- 出图（3 × 5）
fig, axes = plt.subplots(len(S.PARTS), len(TEMPS), figsize=(11.0, 5.4),
                         sharex=True, sharey=True)

for r, part in enumerate(S.PARTS):
    for c, temp in enumerate(TEMPS):
        ax = axes[r, c]
        d = agg[(agg['part'] == part) & (agg['temp'] == temp)].sort_values('time')
        col = S.TEMP_COLORS[temp]
        ax.plot(d['time'], d['mean'], color=col, lw=1.2, zorder=3)
        ax.fill_between(d['time'], d['mean'] - d['std'].fillna(0),
                        d['mean'] + d['std'].fillna(0),
                        color=col, alpha=0.28, lw=0, zorder=2)
        ax.text(0.96, 0.94, letters[part][c], transform=ax.transAxes,
                ha='right', va='top', fontsize=10, fontweight='bold',
                color=S.C_SIG)                     # 显著性与 Fig6B 同色（红）
        if r == 0:
            ax.set_title('%d\u00b0C' % temp, fontsize=10)
        if c == 0:
            ax.set_ylabel('%s\nFrequency (beats / 10 s)' % S.PART_LABELS[part],
                          fontsize=10)
        if r == len(S.PARTS) - 1:
            ax.set_xlabel('Time (s)', fontsize=10)
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_linewidth(1.2)
        ax.tick_params(labelsize=8, direction='in')

for ax in axes.ravel():
    ax.set_xlim(0, XMAX)
    ax.set_ylim(0, YMAX)

fig.tight_layout()
S.save(fig, 'F2_waveform.png')

print('n rows:', len(long), '| 温度:', TEMPS)
for p in S.PARTS:
    print('  %-10s 字母(按 %s) = %s' % (p, TEMPS, letters[p]))
