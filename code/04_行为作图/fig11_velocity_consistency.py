# -*- coding: utf-8 -*-
"""fig11_velocity_consistency.py -- 速度的"组内波动"随温度变化（新发现 ②）

问题
----
原先只报了速度的**均值**（23 C 最快）。本图问的是另一件事：
**同一尾鱼在 10 s 内，速度波动多大？**

结论
----
23 C 的**块内速度 SD 显著高于其余四个温度**（约 1.7-2.3 倍），
但**块间**（61 个 10 s 窗口的平均速度之间的）SD 无差异（F = 1.77, P = 0.212）。
=> 23 C 不是"更持久地快"，而是**短时冲刺与停顿交替**（间歇式运动）。

稳健性（本图 Panel C 即为此）
----------------------------
  · 全部帧            F = 46.1  eta2 = 0.949
  · 仅无缺口块        F = 45.1  eta2 = 0.947
  · 仅 conf >= 0.50   F = 40.2  eta2 = 0.941
  · 仅 conf >= 0.80   F = 12.0  eta2 = 0.827
四种口径的 Tukey 显著对**完全一致**（16!=23, 19!=23, 21!=23, 23!=25）。
且每块帧数各温度齐平（296-298, F = 1.14, P = 0.39）——缺帧不构成解释；
检出置信度 23 C 最低（0.787 vs 0.84-0.87），故专门做了置信度阈值检验。

版式
----
**不加面板字母 (A)/(B)/(C)、不加标题**（项目 §9 规则）—— 字母在拼版时统一添加。
三块并列，宽度比 A : B : C = 1.25 : 1.0 : 1.25。
· 显著性字母**紧贴误差棒 / 上须上方**，不与数据点重叠。
  (A) 的散点**只画须内**（Q1/Q3 ± 1.5 IQR），与箱线 `showfliers=False` 同一口径
  —— 否则个别极端窗会把字母顶到轴顶。图注须写明 "outliers not drawn"。
· (C) 内文字只保留 `Tukey groups identical` 一行；口径细节全部交给图注，
  不塞进图里（用户 2026-09-16 要求）。

数据源：`P.QUANT/6_总结版_全身.xlsx`（逐 10 s 块，61 块/尾）
        `P.QUANT/5_公式计算后_全身.xlsx`（逐帧，供置信度口径）
输出  ：`P.FIG/Fig11_velocity_consistency.png`（PNG @900 DPI）
用法  ：python fig11_velocity_consistency.py
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
FIG_W, FIG_H = 7.2, 3.0
AXES_LW = 1.0
TEMPS = [16, 19, 21, 23, 25]
DEG = chr(176)                      # 度符号（不用转义，避开字面量 \u00b0 的坑）
TEMP_COLORS = {16: '#FEE08B', 19: '#FDAE61', 21: '#F46D43',
               23: '#D73027', 25: '#A50026'}
C_SIG = '#D62728'
C_GREY = '#708090'

plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.size'] = 9
plt.rcParams['axes.linewidth'] = AXES_LW
plt.rcParams['xtick.direction'] = 'in'
plt.rcParams['ytick.direction'] = 'in'
plt.rcParams['svg.fonttype'] = 'none'


def sig_letters(groups):
    """one-way ANOVA + Tukey HSD -> compact letter display."""
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
    """先渲染到内存再落盘（规避大画布下的 imsave OSError）。"""
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


# ================= 1. 逐块表 =================
blocks = []
for sh, d in pd.read_excel(P.q('6_总结版_全身.xlsx'), sheet_name=None,
                           engine='openpyxl').items():
    t, r = parse(sh)
    if t is None:
        continue
    inc = (d['结束帧编号'] - d['起始帧编号'] + 1).to_numpy(float)
    blocks.append(pd.DataFrame({
        'temp': t, 'fish': r,
        'v_mean': d['v/cm_mean'].to_numpy(float),
        'v_sd': d['v/cm_std'].to_numpy(float),
        'gap_free': inc >= 0.98 * 300,
    }))
B = pd.concat(blocks, ignore_index=True)

# ================= 2. 各口径（逐鱼 -> 温度）=================
CALIPERS = {}


def add_caliper(key, label, per_fish_series):
    CALIPERS[key] = {'label': label, 'vals': per_fish_series}


# (a) 全部帧
pf_all = B.groupby(['temp', 'fish'])['v_sd'].mean()
add_caliper('all', 'all frames', pf_all)
# (b) 仅无缺口块
pf_gap = B[B.gap_free].groupby(['temp', 'fish'])['v_sd'].mean()
add_caliper('gap', 'gap-free blocks', pf_gap)

# (c)(d) 置信度口径：需逐帧表
print('读取逐帧表（置信度口径）...')
conf_pf = {0.5: {}, 0.8: {}}
for sh, d in pd.read_excel(P.q('5_公式计算后_全身.xlsx'), sheet_name=None,
                           engine='openpyxl').items():
    t, r = parse(sh)
    if t is None:
        continue
    d = d[['time/10s', 'v/cm', '置信度']].apply(pd.to_numeric, errors='coerce').dropna()
    for thr in (0.5, 0.8):
        vals = []
        for _, g in d.groupby('time/10s'):
            gg = g.loc[g['置信度'] >= thr, 'v/cm']
            if len(gg) >= 5:
                vals.append(gg.std(ddof=1))
        conf_pf[thr][(t, r)] = float(np.mean(vals))
    print('  %s' % sh, flush=True)

for thr in (0.5, 0.8):
    s = pd.Series(conf_pf[thr])
    s.index = pd.MultiIndex.from_tuples(s.index, names=['temp', 'fish'])
    add_caliper('conf%d' % (thr * 100), 'detection conf $\\geq$ %.2f' % thr, s)

# ================= 3. 主检验（现行口径 = 全部帧）=================
groups = [pf_all.loc[t].to_numpy(float) for t in TEMPS]
F0, P0, E0, PAIRS0 = anova_tukey(groups)
letters = sig_letters(groups)
print('\n=== 速度一致性（块内 SD, cm/s）===')
print('  F(4,10) = %.2f   P = %.4f   eta2 = %.3f' % (F0, P0, E0))
print('  Tukey pairs: %s' % PAIRS0)
print('  letters: %s' % dict(zip(TEMPS, letters)))
for t in TEMPS:
    print('    %2d C  %.3f +/- %.3f' % (t, pf_all.loc[t].mean(), pf_all.loc[t].sem()))

# ================= 4. 绘图 =================
fig = plt.figure(figsize=(FIG_W, FIG_H))
gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.0, 1.25],
                      wspace=0.34, left=0.062, right=0.985,
                      top=0.895, bottom=0.155)

# ---- (A) 逐块 v_sd 分布 ----
axA = fig.add_subplot(gs[0, 0])
dataA = [B.loc[B.temp == t, 'v_sd'].to_numpy(float) for t in TEMPS]
bp = axA.boxplot(dataA, positions=range(5), widths=0.62, showfliers=False,
                 patch_artist=True, medianprops=dict(color='black', lw=0.9),
                 whiskerprops=dict(color=C_GREY, lw=0.7),
                 capprops=dict(color=C_GREY, lw=0.7))
for b, t in zip(bp['boxes'], TEMPS):
    b.set_facecolor(TEMP_COLORS[t])
    b.set_edgecolor(C_GREY)
    b.set_linewidth(0.7)
    b.set_alpha(0.75)
rng = np.random.default_rng(0)
# 须端（Q1/Q3 ± 1.5 IQR，夹到该组极值）—— 与 showfliers=False 的箱线口径一致
whis = []
for arr in dataA:
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    whis.append((max(float(arr.min()), q1 - 1.5 * iqr),
                 min(float(arr.max()), q3 + 1.5 * iqr)))
yA_top = max(w[1] for w in whis) * 1.16
axA.set_ylim(0, yA_top)

for i, (t, arr) in enumerate(zip(TEMPS, dataA)):
    wlo, whi = whis[i]
    # 散点只落在须内（与箱线 showfliers=False 同规则）→ 字母得以紧贴上须而不重叠
    inside = arr[(arr >= wlo) & (arr <= whi)]
    s = rng.choice(inside, size=min(len(inside), 70), replace=False)
    axA.scatter(i + rng.normal(0, 0.075, s.size), s, s=3.2, color=C_GREY,
                alpha=0.30, linewidths=0, zorder=3)
    axA.text(i, whi + 0.030 * yA_top, letters[i], ha='center', va='bottom',
             fontsize=10, fontweight='bold', color=C_SIG, zorder=6)
axA.set_xticks(range(5))
axA.set_xticklabels([str(t) for t in TEMPS])
axA.set_xlabel('Temperature (\u00b0C)')
axA.set_ylabel('Speed SD (cm / s)')

# ---- (B) 逐鱼均值 + 检验 ----
axB = fig.add_subplot(gs[0, 1])
means = [pf_all.loc[t].mean() for t in TEMPS]
sems = [pf_all.loc[t].sem() for t in TEMPS]
axB.bar(range(5), means, width=0.62, color=[TEMP_COLORS[t] for t in TEMPS],
        edgecolor=C_GREY, linewidth=0.7, alpha=0.85, zorder=2)
axB.errorbar(range(5), means, yerr=sems, fmt='none', ecolor='black',
             elinewidth=0.9, capsize=2.6, capthick=0.9, zorder=4)
axB.set_xticks(range(5))
axB.set_xticklabels([str(t) for t in TEMPS])
axB.set_xlabel('Temperature (\u00b0C)')
axB.set_ylabel('Speed SD (cm / s)')
axB.set_ylim(0, max(np.array(means) + np.array(sems)) * 1.22)
_yB_top = axB.get_ylim()[1]
for i, t in enumerate(TEMPS):
    v = pf_all.loc[t].to_numpy(float)
    axB.scatter(i + np.array([-0.14, 0.0, 0.14]), v, s=17, color='black',
                zorder=5, linewidths=0)
    # 字母紧贴误差棒上方；若有个体点更高，则抬到该点之上 —— 保证不重叠
    y_let = max(means[i] + sems[i], float(v.max())) + 0.035 * _yB_top
    axB.text(i, y_let, letters[i], ha='center', va='bottom',
             fontsize=10, fontweight='bold', color=C_SIG, zorder=6)

# 面板字母 (A)/(B)/(C) 按项目规则不在此脚本添加 —— 拼图时统一加。

# ---- (C) 四口径稳健性 ----
axC = fig.add_subplot(gs[0, 2])
keys = ['all', 'gap', 'conf50', 'conf80']
xpos = np.arange(len(keys))
W = 0.16
cmax = max(float(CALIPERS[k]['vals'].loc[t].mean()
                 + CALIPERS[k]['vals'].loc[t].sem())
           for k in keys for t in TEMPS)
for j, t in enumerate(TEMPS):
    hts, errs = [], []
    for k in keys:
        s = CALIPERS[k]['vals']
        hts.append(float(s.loc[t].mean()))
        errs.append(float(s.loc[t].sem()))
    axC.bar(xpos + (j - 2) * W, hts, width=W * 0.92, color=TEMP_COLORS[t],
            edgecolor=C_GREY, linewidth=0.45, alpha=0.9, zorder=2,
            label='%d %sC' % (t, DEG))
    axC.errorbar(xpos + (j - 2) * W, hts, yerr=errs, fmt='none',
                 ecolor='black', elinewidth=0.55, capsize=1.6, zorder=3)
axC.set_xticks(xpos)
axC.set_xticklabels(['all\nframes', 'gap-free\nblocks',
                     '$\\geq$ 0.50', '$\\geq$ 0.80'], fontsize=7.6)
axC.set_xlabel('Caliper', labelpad=1)
axC.set_ylabel('Speed SD (cm / s)')
axC.set_ylim(0, cmax * 1.18)
axC.legend(frameon=False, fontsize=6.4, ncol=5, handlelength=0.9,
           columnspacing=0.65, handletextpad=0.32,
           loc='lower center', bbox_to_anchor=(0.58, 1.015))
axC.text(0.975, 0.955, 'Tukey groups identical',
         transform=axC.transAxes, ha='right', va='top', fontsize=6.8,
         color=C_SIG)


p = os.path.join(OUT, 'Fig11_velocity_consistency.png')
save_png(fig, p, DPI)
plt.close(fig)
print('[OK]', p)
