# -*- coding: utf-8 -*-
"""fig12_spatial_use.py -- 空间使用的定量化：19 C 的活动范围最受限（新发现 ③）

坐标系（关键，勿误读）
----------------------
本系统为**缸底仰拍**（相机固定在缸下方，向上拍）。故图像 x / y 两个轴
**都是水平面内的坐标**，**都不代表水深**——单目 2D 无法给出垂直位置。
坐标轴按图像约定绘制（y 向下，`set_ylim(y1, y0)`），与 `Fig7_trajectory_heatmap.png` 一致。
隐含尺度：`SCALE = 0.03125 cm/px`，X 量程 1183 px = 37.0 cm、Y 量程 794 px = 24.8 cm
（缸体标称 60 x 45 cm，故观测外接矩形是"鱼可达范围"，不等于缸壁）。

结论
----
  · **Y 方向的活动范围（逐鱼 SD）在 19 C 显著收窄**（106 px vs 其余 163-183 px）
    F(4,10) = 6.62, P = 0.0072, eta2 = 0.726；Tukey：19 C 与**其余四个温度全部**不同。
  · **Y 方向的平均位置在 19 C 显著偏移**（715 px vs 其余 396-532 px）
    F(4,10) = 9.45, P = 0.0020, eta2 = 0.791。
  => 19 C 组被"压"在 Y 方向的一条窄带里 —— 把 Fig5A 中
     "activity range relatively restricted, clusters at tank edges and corners"
     的**目视描述**升级为**有 P 值的定量结果**。
  · X 方向无差异（SD: F = 0.37, P = 0.826）。

混淆排查
--------
19 C 三尾的 1 Hz 缺秒数为 **0 / 0 / 0**（最快缺帧的是 23 C：14 / 14 / 35 s），
故本结论**不受检出缺口混淆**。

版式
----
**不加面板字母 (A)/(B)/(C)、不加标题**（项目 §9 规则）—— 字母在拼版时统一添加。
上排 = 1 x 5 张占用点云（共同坐标轴）；下排 = 活动范围检验 + 逐鱼占用带。

数据源：`P.QUANT/7_中心点轨迹_全身.xlsx`（1 Hz 中心点，605 点/尾）
输出  ：`P.FIG/Fig12_spatial_use.png`（PNG @900 DPI）
用法  ：python fig12_spatial_use.py
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口

OUT = P.FIG
os.makedirs(OUT, exist_ok=True)

DPI = 900
FIG_W, FIG_H = 7.2, 4.2
AXES_LW = 1.0
SCALE = 0.03125                     # cm/px（项目常量）
DEG = chr(176)                      # 度符号（避开转义字面量的坑）
TEMPS = [16, 19, 21, 23, 25]
TEMP_COLORS = {16: '#FEE08B', 19: '#FDAE61', 21: '#F46D43',
               23: '#D73027', 25: '#A50026'}
C_SIG = '#D62728'
C_GREY = '#708090'
C_FRAME = '#cccccc'

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


# ================= 1. 读取 1 Hz 中心点 =================
tracks, rows = {}, []
for sh, d in pd.read_excel(P.q('7_中心点轨迹_全身.xlsx'), sheet_name=None,
                           engine='openpyxl').items():
    t, r = parse(sh)
    if t is None:
        continue
    d = d.dropna(subset=['中心点X', '中心点Y'])
    cx = d['中心点X'].to_numpy(float)
    cy = d['中心点Y'].to_numpy(float)
    tracks[(t, r)] = (cx, cy)
    rows.append({'temp': t, 'fish': r,
                 'cx': cx.mean(), 'cy': cy.mean(),
                 'cx_sd': cx.std(ddof=1), 'cy_sd': cy.std(ddof=1),
                 'n': len(cx)})
S = pd.DataFrame(rows).sort_values(['temp', 'fish']).reset_index(drop=True)

X0 = min(v[0].min() for v in tracks.values())
X1 = max(v[0].max() for v in tracks.values())
Y0 = min(v[1].min() for v in tracks.values())
Y1 = max(v[1].max() for v in tracks.values())

# ================= 2. 检验 =================
g_sd = [S.loc[S.temp == t, 'cy_sd'].to_numpy(float) for t in TEMPS]
g_mu = [S.loc[S.temp == t, 'cy'].to_numpy(float) for t in TEMPS]
F_sd, P_sd, E_sd, PR_sd = anova_tukey(g_sd)
F_mu, P_mu, E_mu, PR_mu = anova_tukey(g_mu)
g_xsd = [S.loc[S.temp == t, 'cx_sd'].to_numpy(float) for t in TEMPS]
F_x, P_x, E_x, _ = anova_tukey(g_xsd)

print('\n=== 空间使用（Y 方向）===')
print('  Y scatter (SD)  : F(4,10) = %.2f  P = %.4f  eta2 = %.3f  %s'
      % (F_sd, P_sd, E_sd, PR_sd))
print('  Y position (mu) : F(4,10) = %.2f  P = %.4f  eta2 = %.3f  %s'
      % (F_mu, P_mu, E_mu, PR_mu))
print('  X scatter (SD)  : F(4,10) = %.2f  P = %.4f (n.s. -> 不画)' % (F_x, P_x))
print('  coordinates: X %.0f-%.0f px (%.1f cm) | Y %.0f-%.0f px (%.1f cm)'
      % (X0, X1, (X1 - X0) * SCALE, Y0, Y1, (Y1 - Y0) * SCALE))
for t in TEMPS:
    print('    %2d C  mean Y = %6.0f px | SD(Y) = %5.0f px'
          % (t, S.loc[S.temp == t, 'cy'].mean(), S.loc[S.temp == t, 'cy_sd'].mean()))

let_sd = sig_letters(g_sd)

# ================= 3. 绘图 =================
fig = plt.figure(figsize=(FIG_W, FIG_H))
gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.02], hspace=0.42,
                      left=0.088, right=0.985, top=0.975, bottom=0.13)
gsA = gs[0].subgridspec(1, 5, wspace=0.13)
gsB = gs[1].subgridspec(1, 2, wspace=0.34)

XL, XR = X0 - 60, X1 + 60
YT, YB = Y1 + 60, Y0 - 60                 # 图像 y 向下

# ---- (A) 五种温度的占用点云（共同坐标轴）----
rng = np.random.default_rng(0)
axesA = []
for i, t in enumerate(TEMPS):
    ax = fig.add_subplot(gsA[0, i])
    axesA.append(ax)
    for f in sorted(S.loc[S.temp == t, 'fish']):
        cx, cy = tracks[(t, f)]
        idx = rng.choice(len(cx), size=min(len(cx), 180), replace=False)
        ax.scatter(cx[idx], cy[idx], s=2.0, color=TEMP_COLORS[t],
                   alpha=0.40, linewidths=0, zorder=3)
    mu = float(S.loc[S.temp == t, 'cy'].mean())
    sd = float(S.loc[S.temp == t, 'cy_sd'].mean())
    ax.axhline(mu, color=C_SIG, lw=0.9, ls='-', zorder=5)
    ax.axhline(mu - sd, color=C_SIG, lw=0.7, ls='--', zorder=5)
    ax.axhline(mu + sd, color=C_SIG, lw=0.7, ls='--', zorder=5)
    ax.text(0.5, 0.025, 'SD %d' % round(sd), transform=ax.transAxes,
            ha='center', va='bottom', fontsize=6.6, color=C_SIG, zorder=6,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.78, pad=0.9))
    ax.set_xlim(XL, XR)
    ax.set_ylim(YB, YT)
    for sp in ax.spines.values():
        sp.set_linewidth(AXES_LW)
        sp.set_color(C_FRAME)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('%d %sC' % (t, DEG), fontsize=8.5, labelpad=2)
axesA[0].set_ylabel('Tank Y (px)', fontsize=8.5)

# ---- (B) Y 方向活动范围（逐鱼 SD）----
axB = fig.add_subplot(gsB[0, 0])
means = [S.loc[S.temp == t, 'cy_sd'].mean() for t in TEMPS]
sems = [S.loc[S.temp == t, 'cy_sd'].sem() for t in TEMPS]
axB.bar(range(5), means, width=0.62, color=[TEMP_COLORS[t] for t in TEMPS],
        edgecolor=C_GREY, linewidth=0.7, alpha=0.85, zorder=2)
axB.errorbar(range(5), means, yerr=sems, fmt='none', ecolor='black',
             elinewidth=0.9, capsize=2.6, capthick=0.9, zorder=4)
for i, t in enumerate(TEMPS):
    v = S.loc[S.temp == t, 'cy_sd'].to_numpy(float)
    axB.scatter(i + np.array([-0.13, 0.0, 0.13]), v, s=17, color='black',
                zorder=5, linewidths=0)
    axB.text(i, means[i] + sems[i] + 6, let_sd[i], ha='center', va='bottom',
             fontsize=10, fontweight='bold', color=C_SIG, zorder=6)
axB.set_xticks(range(5))
axB.set_xticklabels([str(t) for t in TEMPS])
axB.set_xlabel('Temperature (%sC)' % DEG)
axB.set_ylabel('Y spread (px)')
axB.set_ylim(0, max(np.array(means) + np.array(sems)) * 1.24)

# 面板字母 (A)/(B)/(C) 按项目规则不在此脚本添加 —— 拼图时统一加。

# ---- (C) 逐鱼占用带（mean ± SD）----
axC = fig.add_subplot(gsB[0, 1])
for i, t in enumerate(TEMPS):
    y = i                                         # 与 set_yticks(range(5)) 的标签顺序一致
    g = S[S.temp == t].sort_values('fish')
    for j, (_, rr) in enumerate(g.iterrows()):
        off = (j - 1) * 0.13
        axC.plot([rr['cy'] - rr['cy_sd'], rr['cy'] + rr['cy_sd']],
                 [y + off, y + off], color=TEMP_COLORS[t], lw=2.8,
                 solid_capstyle='round', zorder=3)
        axC.scatter([rr['cy']], [y + off], s=13, color=TEMP_COLORS[t],
                    edgecolors='black', linewidths=0.45, zorder=4)
    axC.plot([g['cy'].mean()] * 2, [y - 0.27, y + 0.27], color='black',
             lw=0.8, ls=':', zorder=5)
axC.set_ylim(-0.6, 4.6)
axC.set_yticks(range(5))
axC.set_yticklabels([str(t) for t in TEMPS])
axC.set_xlim(150, 880)
axC.set_xlabel('Tank Y (px)')
axC.set_ylabel('Temperature (%sC)' % DEG)
axC.text(1.0, 1.02, 'bar = fish (mean $\\pm$ SD), dotted = group mean',
         transform=axC.transAxes, ha='right', va='bottom', fontsize=6.4,
         color=C_SIG)


p = os.path.join(OUT, 'Fig12_spatial_use.png')
save_png(fig, p, DPI)
plt.close(fig)
print('[OK]', p)
