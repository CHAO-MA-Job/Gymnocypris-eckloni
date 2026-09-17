# -*- coding: utf-8 -*-
"""fig6b_kinematics.py -- Figure 6B: velocity (bars) + displacement (line), twin axes.

量纲（以量化表 `8_速度位移_全身.xlsx` 为准）：
  `velocity_cm_s` = mean(每尾各 10 s 块的 `v/cm_mean`)；而 `v/cm` 由
  `5_process_quanshen.py` 定义为 位移_px / dt x SCALE（dt 单位 = 秒）
  -> **单位是 cm/s（每秒速度）**，不是 cm/10s。
  ⚠ 量化表列名 `v/10s` / `v/10秒` 是历史遗留：其值与 `v/cm_mean` **逐行恒等**
  （"10s" 指"每 10 秒一块"，不是"除以 10 秒"）。表内自证：块内位移 `S/10s`
  ≈ `v/cm_mean` x 10 s（16℃-1 第 1 块：2.2403 x 10 = 22.403 ≈ 22.2544 cm）。

Layout:
  * 左轴 = 速度柱（Tukey HSD 紧凑字母），右轴 = 位移折线 + SD 带。
  * **左上角嵌图** = 速度–位移散点（15 尾按温度着色 + 参考线），
    直观呈现二者的共线性，替代原先单行 `r = 0.997` 公式。
  * **图例移到右上角**，为嵌图腾出左上角。
  * 顶部预留约 30% 轴高给「嵌图 + 图例」，避免遮挡最长柱（23 C）。
无标题、无面板字母（项目规则）。
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.ticker import FuncFormatter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P

CSV = P.q('per_fish_metrics.csv')
OUT = P.FIG
os.makedirs(OUT, exist_ok=True)

DPI = 900
FIG_W, FIG_H = 6.4, 4.4
AXES_LW = 1.2

C_BAR = '#F4A460'
C_LINE = '#708090'
C_SIG = '#D62728'
TEMP_COLORS = {16: '#FEE08B', 19: '#FDAE61', 21: '#F46D43',
               23: '#D73027', 25: '#A50026'}

# ---- 版面常量 ----
VEL_DIV = 0.74          # 最高柱顶（含误差棒）占轴高比例 -> 顶部留白
DIS_DIV = 0.70          # 最高位移点占轴高比例 -> 顶部留白
INSET_RECT = [0.088, 0.560, 0.360, 0.365]   # 嵌图 [x0, y0, w, h]（ax1 轴坐标）
CBAR_RECT = [0.461, 0.560, 0.016, 0.365]    # 嵌图右侧竖排温度色带
NOMINAL_S = 610.0       # 回退值：标称观测时长（s）；参考线 位移 ≈ 速度 x 时长

plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['mathtext.fontset'] = 'stix'   # 数学字体与 Times 一致，避免斜体 v 被读成 ν
plt.rcParams['font.size'] = 10
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


def nominal_duration():
    """参考线斜率（s）——**以量化表 `8_速度位移_全身.xlsx` 为准**。

    该表一行 = 一个 10 s 块（30 fps x 300 帧）：
      `v/cm_mean`      = 块内逐帧 `v/cm` 均值，**cm/s（每秒速度）**
      `S/总位移_结束`  = 该块末的累计位移（cm）
    逐尾取 v_mean = mean(v/cm_mean)、S = max(S/总位移_结束)，令 T_i = S / v_mean
    （该尾的有效观测时长），取 15 尾均值作为参考线斜率：位移 ≈ 速度 x T。
    """
    path = P.q('8_速度位移_全身.xlsx')
    if os.path.exists(path):
        try:
            books = pd.read_excel(path, sheet_name=None)
            t = []
            for d in books.values():
                if not len(d):
                    continue
                vbar = float(pd.to_numeric(d['v/cm_mean'],
                                           errors='coerce').mean())
                s_tot = float(pd.to_numeric(d['S/总位移_结束'],
                                            errors='coerce').max())
                if vbar > 0:
                    t.append(s_tot / vbar)
            if t:
                t = np.asarray(t, dtype=float)
                return float(t.mean()), (
                    'quant-table 8_速度位移_全身.xlsx, per-fish S/v_mean = '
                    '%.0f-%.0f s' % (t.min(), t.max()))
        except Exception as exc:                       # noqa: BLE001
            print('   [warn] 读量化表失败，回退 NOMINAL_S：', exc)
    return float(NOMINAL_S), 'fallback'


def add_corr_inset(ax, temps, v, s, r, row_colors, t_ref):
    """左上角嵌图：速度–位移散点（按温度着色）+ 标称观测时长参考线。"""
    cmap = LinearSegmentedColormap.from_list(
        'gyo_temp', [TEMP_COLORS[t] for t in temps])
    norm = Normalize(vmin=min(temps), vmax=max(temps))

    axin = ax.inset_axes(INSET_RECT)
    axin.set_zorder(5)
    axin.patch.set_alpha(1.0)

    # 参考线：位移 = 速度 x 标称观测时长（斜率取自量化表 10 s 分块）
    vt = np.array([0.0, float(np.max(v)) * 1.06])
    axin.plot(vt, t_ref * vt, '--', color='0.55', lw=0.9, zorder=1)

    axin.scatter(v, s, c=row_colors, s=22, edgecolor='black',
                 linewidth=0.35, zorder=3)

    axin.set_xlim(0, vt[1])
    axin.set_ylim(0, float(np.max(s)) * 1.12)
    axin.set_xlabel('Velocity (cm / s)', fontsize=6.5, labelpad=1.5)
    axin.set_ylabel('Displacement (cm)', fontsize=6.5, labelpad=1.5)
    axin.tick_params(labelsize=5.8, length=2, pad=1)
    # x/y 在原点共用同一个 0：隐去 y 轴上的 0 标签
    axin.yaxis.set_major_formatter(
        FuncFormatter(lambda val, pos: '' if abs(val) < 1e-9 else '%g' % val))
    for sp in ('top', 'right'):
        axin.spines[sp].set_visible(False)
    for sp in ('left', 'bottom'):
        axin.spines[sp].set_linewidth(0.6)

    axin.text(0.035, 0.955, '$r$ = %.3f' % r, transform=axin.transAxes,
              fontsize=6.5, va='top', ha='left', zorder=6,
              bbox=dict(facecolor='white', edgecolor='none', alpha=0.85, pad=1.0))

    # 温度色带（竖排在嵌图右侧；主 x 轴已标明温度，故不再重复 axis label）
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cax = ax.inset_axes(CBAR_RECT)
    cax.set_zorder(5)
    cax.patch.set_alpha(1.0)
    cb = ax.figure.colorbar(sm, cax=cax, orientation='vertical')
    cb.set_ticks(temps)
    cb.ax.tick_params(labelsize=5.2, length=1.5, pad=1)
    cb.outline.set_linewidth(0.4)
    return axin


def main():
    df = pd.read_csv(CSV).dropna(subset=['velocity_cm_s', 'displacement_cm'])
    temps = sorted(int(t) for t in df['temp'].unique())
    x = np.arange(len(temps))

    g = df.groupby('temp')
    vel_m = g['velocity_cm_s'].mean().reindex(temps).to_numpy(float)
    vel_e = g['velocity_cm_s'].sem().reindex(temps).to_numpy(float)
    dis_m = g['displacement_cm'].mean().reindex(temps).to_numpy(float)
    dis_s = g['displacement_cm'].std(ddof=1).reindex(temps).to_numpy(float)

    vel_groups = [df.loc[df['temp'] == t, 'velocity_cm_s'].to_numpy(float)
                  for t in temps]
    letters = sig_letters(vel_groups)
    F_v, p_v = stats.f_oneway(*vel_groups)
    v = df['velocity_cm_s'].to_numpy(float)
    s = df['displacement_cm'].to_numpy(float)
    r = float(np.corrcoef(v, s)[0, 1])

    fig, ax1 = plt.subplots(figsize=(FIG_W, FIG_H))

    bars = ax1.bar(x, vel_m, 0.62, yerr=vel_e, color=C_BAR, alpha=0.9,
                   capsize=3, zorder=2, label='Mean velocity',
                   error_kw={'ecolor': 'gray', 'elinewidth': 1.2,
                             'capthick': 1.2})

    ax1.set_xlabel('Temperature (' + chr(176) + 'C)', fontsize=12)
    ax1.set_ylabel('Mean velocity (cm / s)', fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(t) for t in temps])
    span = float((vel_m + vel_e).max()) / VEL_DIV
    ax1.set_ylim(0, span)
    ax1.set_xlim(-0.6, len(temps) - 0.4)

    for i, b in enumerate(bars):
        ax1.text(b.get_x() + b.get_width() / 2.,
                 vel_m[i] + vel_e[i] + span * 0.022, letters[i],
                 ha='center', va='bottom', fontweight='bold',
                 color=C_SIG, fontsize=11, zorder=6)

    ax2 = ax1.twinx()
    ax2.fill_between(x, dis_m - dis_s, dis_m + dis_s,
                     color=C_LINE, alpha=0.15, lw=0, zorder=1)
    ax2.plot(x, dis_m, '-', color=C_LINE, marker='D', ms=6, lw=2.0,
             zorder=3, label='Cumulative displacement')
    ax2.set_ylabel('Cumulative displacement (cm)', fontsize=12)
    ax2.set_ylim(0, float((dis_m + dis_s).max()) / DIS_DIV)

    # ---- 左上角：速度–位移相关嵌图（替代原先单行 r 公式）----
    t_ref, t_src = nominal_duration()
    row_colors = [TEMP_COLORS[int(t)] for t in df['temp'].tolist()]
    add_corr_inset(ax1, temps, v, s, r, row_colors, t_ref)

    # ---- 图例移到右上角 ----
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc='upper right',
               bbox_to_anchor=(1.0, 0.995), frameon=True,
               edgecolor='gray', fontsize=9, framealpha=0.92)

    for a in (ax1, ax2):
        a.spines['left'].set_linewidth(AXES_LW)
        a.spines['bottom'].set_linewidth(AXES_LW)
        a.spines['right'].set_linewidth(AXES_LW)

    fig.tight_layout()
    p = os.path.join(OUT, 'Fig6B_velocity_displacement.png')
    fig.savefig(p, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print('[OK]', p)
    print('   ANOVA velocity F=%.3f p=%.4f | r(vel,dis)=%.4f'
          % (F_v, p_v, r))
    print('   嵌图: %d 尾, 温度 %s, 参考线斜率 %.0f s（来源 %s）'
          % (len(v), temps, t_ref, t_src))
    print('   量纲: velocity_cm_s = cm/s（每秒）；量化表列名 v/10s 值 == v/cm_mean')


if __name__ == '__main__':
    main()
