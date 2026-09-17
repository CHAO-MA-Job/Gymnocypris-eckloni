# -*- coding: utf-8 -*-
"""fig13_bbox_area.py —— 投影面积（发现 ④，描述性 / 候选）

量
--
`bbox 投影面积` = (x2 − x1) × (y2 − y1)：鱼在**图像平面**上的"表观大小"（px²）。
单目 2D 下它同时混合了 ① 距离镜头的远近（水深/深度）与 ② 姿态（滚转 / 俯仰 / 朝向），
**不是真实体型**。故本图只作描述，不下"位置 / 姿态"结论。

结论（现行数据）
----------------
  · 投影面积 23–25 ℃ 显著最小（F(4,10)=11.6, P=0.0009, η²=0.82；21 ℃ 最高）。
  · 拆解：主要由**宽度**（沿 X 轴投影）驱动，高度变化弱。
  · 稳健性：剔除低置信度帧后，23–25 ℃ 偏小的方向**不变**（见控制台打印）。

⚠ 混淆排查（控制台打印）
  23 ℃ 检出置信度最低（0.787 vs 0.84–0.87）→ 专门做了置信度阈值检验：
  全部帧 / conf≥0.5 / conf≥0.8 三种口径的 ANOVA 均显著、方向一致 → 非框抖动伪影。

数据源：`P.QUANT/6_总结版_全身.xlsx`（x1/y1/x2/y2 块均值 → 逐鱼）
        `P.QUANT/5_公式计算后_全身.xlsx`（逐帧，全身表 `类别` 全为 0，供置信度口径）
输出  ：`P.FIG/Fig13_bbox_area.png`（PNG @900 DPI）
用法  ：python fig13_bbox_area.py
"""
import io
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口

OUT = P.FIG
os.makedirs(OUT, exist_ok=True)

DPI = 900
FIG_W, FIG_H = 6.0, 2.8
AXES_LW = 1.0
DEG = chr(176)
SCALE = 0.03125                  # cm/px
TEMPS = [16, 19, 21, 23, 25]
TEMP_COLORS = {16: '#FEE08B', 19: '#FDAE61', 21: '#F46D43',
               23: '#D73027', 25: '#A50026'}
C_SIG = '#D62728'
C_GREY = '#708090'
C_W = '#9ECAE1'                  # 宽度（浅蓝）
C_H = '#6BAED6'                  # 高度（深蓝）

plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.size'] = 9
plt.rcParams['axes.linewidth'] = AXES_LW
plt.rcParams['xtick.direction'] = 'in'
plt.rcParams['ytick.direction'] = 'in'
plt.rcParams['svg.fonttype'] = 'none'


def sig_letters(groups):
    pv = stats.tukey_hsd(*groups).pvalue
    sig = pv < 0.05
    order = np.argsort([np.mean(g) for g in groups])
    bags, out = [], [''] * len(groups)
    for i in order:
        for k, members in enumerate(bags):
            if all(not sig[i, m] for m in members):
                members.append(i)
                out[i] += chr(ord('a') + k)
                break
        else:
            bags.append([i])
            out[i] += chr(ord('a') + len(bags) - 1)
    return out


def eta2(groups):
    grand = np.concatenate(groups)
    ssb = sum(len(g) * (g.mean() - grand.mean()) ** 2 for g in groups)
    return ssb / ((grand - grand.mean()) ** 2).sum()


def anova_tukey(groups):
    F, P = stats.f_oneway(*groups)
    pv = stats.tukey_hsd(*groups).pvalue
    pairs = [(TEMPS[i], TEMPS[j]) for i in range(5) for j in range(i + 1, 5)
             if pv[i, j] < 0.05]
    return F, P, eta2(groups), pairs


def save_png(fig, path, dpi):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi)
    data = buf.getvalue()
    buf.close()
    with open(path, 'wb') as f:
        f.write(data)
    print('   %s  %.2f MB' % (os.path.basename(path), len(data) / 1e6))


def parse(sheet):
    m = re.search(r'(\d+)\s*℃?\s*-\s*(\d+)', str(sheet))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


# ================= 1. 逐鱼 bbox 面积 / 宽 / 高 =================
rows = []
for sh, d in pd.read_excel(P.q('6_总结版_全身.xlsx'), sheet_name=None,
                           engine='openpyxl').items():
    t, r = parse(sh)
    if t is None:
        continue
    w = (d['x2_mean'] - d['x1_mean']).to_numpy(float)
    h = (d['y2_mean'] - d['y1_mean']).to_numpy(float)
    rows.append({'temp': t, 'fish': r,
                 'area': float((w * h).mean()),
                 'w': float(w.mean()),
                 'h': float(h.mean())})
B = pd.DataFrame(rows).sort_values(['temp', 'fish']).reset_index(drop=True)

# ================= 2. 检验 =================
g_area = [B.loc[B.temp == t, 'area'].to_numpy(float) for t in TEMPS]
g_w = [B.loc[B.temp == t, 'w'].to_numpy(float) for t in TEMPS]
g_h = [B.loc[B.temp == t, 'h'].to_numpy(float) for t in TEMPS]
F_a, P_a, E_a, PR_a = anova_tukey(g_area)
F_w, P_w, E_w, PR_w = anova_tukey(g_w)
F_h, P_h, E_h, PR_h = anova_tukey(g_h)
let_a = sig_letters(g_area)
let_w = sig_letters(g_w)

print('\n=== bbox 投影面积（px²）/ 宽（px）/ 高（px）===')
print('  area   F(4,10)=%.2f  P=%.4f  eta2=%.3f  %s' % (F_a, P_a, E_a, PR_a))
print('  width  F(4,10)=%.2f  P=%.4f  eta2=%.3f  %s' % (F_w, P_w, E_w, PR_w))
print('  height F(4,10)=%.2f  P=%.4f  eta2=%.3f  %s' % (F_h, P_h, E_h, PR_h))
for t in TEMPS:
    g = B[B.temp == t]
    print('    %2d C  area=%8.0f px² (=%.1f cm²)  w=%.0f px (%.1f cm)  h=%.0f px'
          % (t, g.area.mean(), g.area.mean() * SCALE**2,
             g.w.mean(), g.w.mean() * SCALE, g.h.mean()))

# ================= 3. 置信度稳健性（逐帧，类别=1 全身）=================
print('\n读取逐帧表（置信度口径）...')
conf_area = {0.0: {}, 0.5: {}, 0.8: {}}
for sh, d in pd.read_excel(P.q('5_公式计算后_全身.xlsx'), sheet_name=None,
                           engine='openpyxl').items():
    t, r = parse(sh)
    if t is None:
        continue
    d = d[['time/10s', 'x1', 'y1', 'x2', 'y2', '置信度']].apply(
        pd.to_numeric, errors='coerce').dropna()
    d['a'] = (d['x2'] - d['x1']) * (d['y2'] - d['y1'])
    for thr in (0.0, 0.5, 0.8):
        vals = []
        for _, g in d.groupby('time/10s'):
            gg = g.loc[g['置信度'] >= thr, 'a']
            if len(gg) >= 5:
                vals.append(gg.mean())
        conf_area[thr][(t, r)] = float(np.mean(vals))
    print('  %s' % sh, flush=True)

print('\n=== 面积 × 置信度阈值（逐鱼均值，n=3/温度）===')
for thr, lab in [(0.0, 'all frames'), (0.5, 'conf>=0.50'), (0.8, 'conf>=0.80')]:
    s = pd.Series(conf_area[thr])
    s.index = pd.MultiIndex.from_tuples(s.index, names=['temp', 'fish'])
    g = [s.loc[t].to_numpy(float) for t in TEMPS]
    F, P, E, PR = anova_tukey(g)
    print('  %-12s F=%.2f  P=%.4f  eta2=%.3f  %s' % (lab, F, P, E, PR))
    print('       %s' % ' | '.join('%d:%.0f' % (t, s.loc[t].mean()) for t in TEMPS))

# ================= 4. 绘图 =================
fig, axes = plt.subplots(1, 2, figsize=(FIG_W, FIG_H))
plt.subplots_adjust(left=0.10, right=0.985, top=0.93, bottom=0.16, wspace=0.34)

# ---- (A) 投影面积 ----
ax = axes[0]
means = [B.loc[B.temp == t, 'area'].mean() for t in TEMPS]
sems = [B.loc[B.temp == t, 'area'].sem() for t in TEMPS]
ax.bar(range(5), means, width=0.62, color=[TEMP_COLORS[t] for t in TEMPS],
       edgecolor=C_GREY, linewidth=0.7, alpha=0.85, zorder=2)
ax.errorbar(range(5), means, yerr=sems, fmt='none', ecolor='black',
            elinewidth=0.9, capsize=2.6, capthick=0.9, zorder=4)
for i, t in enumerate(TEMPS):
    v = B.loc[B.temp == t, 'area'].to_numpy(float)
    ax.scatter(i + np.array([-0.13, 0.0, 0.13]), v, s=16, color='black',
               zorder=5, linewidths=0)
    ax.text(i, means[i] + sems[i] + 2500, let_a[i], ha='center', va='bottom',
            fontsize=10, fontweight='bold', color=C_SIG, zorder=6)
ax.set_xticks(range(5))
ax.set_xticklabels([str(t) for t in TEMPS])
ax.set_xlabel('Temperature (%sC)' % DEG)
ax.set_ylabel('Projected area (px$^2$)')
ax.set_ylim(0, max(np.array(means) + np.array(sems)) * 1.30)
ax.text(0.035, 0.985, '$F_{4,10}$ = %.1f\n$P$ = %.4f' % (F_a, P_a),
        transform=ax.transAxes, ha='left', va='top', fontsize=7.6,
        color=C_SIG, linespacing=1.4)

# ---- (B) 宽 / 高拆解 ----
ax = axes[1]
wmean = [B.loc[B.temp == t, 'w'].mean() for t in TEMPS]
hmean = [B.loc[B.temp == t, 'h'].mean() for t in TEMPS]
x = np.arange(5)
wd = 0.38
ax.bar(x - wd / 2, wmean, width=wd, color=C_W, edgecolor='0.45',
       linewidth=0.6, alpha=0.95, label='width (X)', zorder=2)
ax.bar(x + wd / 2, hmean, width=wd, color=C_H, edgecolor='0.45',
       linewidth=0.6, alpha=0.95, label='height (Y)', zorder=2)
for i, t in enumerate(TEMPS):
    ax.text(i, wmean[i] + 12, let_w[i], ha='center', va='bottom',
            fontsize=10, fontweight='bold', color=C_SIG, zorder=6)
ax.set_xticks(range(5))
ax.set_xticklabels([str(t) for t in TEMPS])
ax.set_xlabel('Temperature (%sC)' % DEG)
ax.set_ylabel('Projected size (px)')
ax.set_ylim(0, max(wmean + hmean) * 1.30)
ax.legend(frameon=False, fontsize=7.5, loc='upper left')
ax.text(0.975, 0.985, '$P$ = %.3f (width)' % P_w,
        transform=ax.transAxes, ha='right', va='top', fontsize=7.4,
        color=C_SIG)

p = os.path.join(OUT, 'Fig13_bbox_area.png')
save_png(fig, p, DPI)
plt.close(fig)
print('[OK]', p)
