# -*- coding: utf-8 -*-
"""Fig6 (model performance) — 人眼对照曲线（模型 vs 人眼，逐 10 s 窗）。

定位：模型验证图，与混淆矩阵 / 训练曲线同归 `04_Outputs/05_模型作图/`（阶段3）。
**一次输出两版**：
  · `Fig6_validation_curve.png`         原始逐窗折线（3 面板横排，主图）
  · `Fig6_validation_curve_smooth.png`  平滑版（**竖排 3 行**；B 样条 k=3 + 显著标记，
                                         风格对齐 `04_行为作图/Fig5/Fig5_temporal_validation.png`）

- 数据 : **`P.QUANT/21-1_人眼.xlsx`**（用户指定；含「模型」与「人眼」两组逐窗计数）
         —— 模型侧为**现行口径**（G0_yolo11n_640 @640+TTA + dedupe=True/ffill=False）
         回退源：`21-1_countboard_data.xlsx`（由 `make_21-1_countboard.py` 机器生成，结构相同）
         ⚠ `21-1_人眼.xlsx` 的「模型」列为**人工同步**；上游口径一变须重跑
           `make_21-1_countboard.py` 并刷新，否则与本文件的回退源不一致。
- 真值 : 同表「人眼」列（21-1 逐窗计数，唯一权威，见 总览.md §7）
- 口径 : MAPE = mean(|模型−人眼| / 人眼) × 100；AR = 100 − MAPE；另附 r（逐窗 Pearson）
         ⚠ **两版的 AR/r 均由原始逐窗值计算**，与平滑无关 —— 平滑只影响画法。
- 平滑 : 平滑版用 **B 样条（`make_interp_spline`, k=3）** 在 300 个等距点上重建曲线
         （与 `fig4A.py` 同法），负值截为 0。
         ⚠ 样条会在窗口之间**插值/过冲**（可能略高于或低于实测点）—— 它只用于观察趋势，
           任何数值引用必须回到原始点或 `21-1_人眼.xlsx`。
- 配色 : 项目约定（总览 §9）—— **模型 橙 `#F4A460` / 人眼 灰 `#708090` / 强调 红 `#D62728`**
- 版式 : Times New Roman；`axes.linewidth 1.2`；刻度朝内；去上/右边框；PNG @900 DPI；
         按 2026-09-15 规则**不加面板字母、不加额外标题** —— 部位名由 **Y 轴标签**承载，
         其余说明归图注。
- 注意 : 三部位频率为**辅助描述量、不作结论**（胸鳍 p=0.34、尾鳍 p=0.25 无温度效应）；
         本图仅用于说明检测/计数层与人眼的一致性，不支撑温度效应结论。

用法 : python fig6_validation_curve.py
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（阶段3）

# 21-1 模型 vs 人眼对照表：**优先用户指定的 21-1_人眼.xlsx**（阶段1/2 数据根），
# 回退到机器生成的 countboard（分析中间物 → 数据根）。
CB = P.pick(P.q('21-1_人眼.xlsx'),
            P.res('21-1_countboard_data.xlsx'),
            P.q('21-1_countboard_data.xlsx'))
OUT = P.MODEL_FIG              # 阶段3 图根：04_Outputs/05_模型作图
os.makedirs(OUT, exist_ok=True)

DPI = 900
N_SMOOTH = 300                 # 样条重建点数
C_MODEL = '#F4A460'    # 橙 —— 模型
C_HUMAN = '#708090'    # 灰 —— 人眼（人工）
C_EMPH = '#D62728'     # 红 —— 强调（误差数值）

plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['axes.spines.right'] = False
plt.rcParams['axes.spines.top'] = False
plt.rcParams['xtick.direction'] = 'in'
plt.rcParams['ytick.direction'] = 'in'

SPECS = [('鳃盖_模型', '鳃盖_人眼', 'Operculum',
          'Operculum (breathing rate)'),
         ('胸鳍_模型', '胸鳍_人眼', 'Pectoral fin',
          'Pectoral fin (beating frequency)'),
         ('尾鳍_模型', '尾鳍_人眼', 'Caudal fin',
          'Caudal fin (propulsion frequency)')]


def mape(model, human):
    """逐窗相对误差再平均（%）；忽略人眼为 0 或缺失的窗。"""
    m = pd.to_numeric(pd.Series(model), errors='coerce').to_numpy(float)
    h = pd.to_numeric(pd.Series(human), errors='coerce').to_numpy(float)
    ok = ~(np.isnan(m) | np.isnan(h)) & (h != 0)
    return float(100.0 * np.mean(np.abs(m[ok] - h[ok]) / h[ok]))


def stats_of(mm, hh):
    """(AR, r) —— 一律基于原始逐窗值。"""
    ok = ~(np.isnan(mm) | np.isnan(hh))
    mp = mape(mm, hh)
    r = (float(np.corrcoef(mm[ok], hh[ok])[0, 1])
         if ok.sum() > 2 and mm[ok].std() > 0 and hh[ok].std() > 0
         else float('nan'))
    return 100 - mp, r


# ================================================================ 版 A：原始（3 面板横排）
def render_raw(d, t):
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 3.7), sharex=True)
    for ax, (mc, hc, short, _long) in zip(axes, SPECS):
        mm = pd.to_numeric(d[mc], errors='coerce').to_numpy(float)
        hh = pd.to_numeric(d[hc], errors='coerce').to_numpy(float)
        ar, r = stats_of(mm, hh)

        ax.fill_between(t, np.minimum(mm, hh), np.maximum(mm, hh),
                        color=C_MODEL, alpha=0.16, lw=0, zorder=1)
        ax.plot(t, hh, '--', color=C_HUMAN, marker='s', ms=3.4, mfc='white',
                mew=0.9, lw=1.2, zorder=3, label='Human')
        ax.plot(t, mm, '-', color=C_MODEL, marker='o', ms=3.4, lw=1.7,
                zorder=4, label='Model')

        # 2026-09-15 规则：不加面板字母、不加额外标题 —— 部位名进 Y 轴标签
        ax.set_ylabel('%s\n(counts / 10 s)' % short, fontsize=10.5)
        ax.set_xlabel('Time (s)')
        ax.set_xticks(np.arange(180, 471, 60))
        ax.set_ylim(0, max(np.nanmax(mm), np.nanmax(hh)) * 1.22)
        ax.text(0.03, 0.97, 'AR = %.2f%%\nr = %+.2f' % (ar, r),
                transform=ax.transAxes, ha='left', va='top',
                fontsize=10, color=C_EMPH, fontweight='bold',
                bbox=dict(facecolor='white', edgecolor='none',
                          alpha=0.8, pad=1.5))
        ax.legend(fontsize=9, loc='lower center', ncol=2, frameon=False)

    fig.tight_layout(rect=(0, 0.05, 1, 0.99))
    fig.text(0.5, 0.005, 'Fish 21-1', ha='center', va='bottom',
             fontsize=9, color='0.35')
    return fig


# ================================================================ 版 B：B 样条平滑（竖排）
def render_smooth(d, t):
    """风格对齐 Fig5_temporal_validation.png：竖排 3 行 + B 样条 + 显著标记。"""
    fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    xs = np.linspace(np.nanmin(t), np.nanmax(t), N_SMOOTH)

    for i, (ax, (mc, hc, _short, long_name)) in enumerate(zip(axes, SPECS)):
        mm = pd.to_numeric(d[mc], errors='coerce').to_numpy(float)
        hh = pd.to_numeric(d[hc], errors='coerce').to_numpy(float)
        ok = ~(np.isnan(mm) | np.isnan(hh))
        ar, r = stats_of(mm, hh)

        # B 样条重建（k=3）；计数非负，过冲出的负值截为 0
        ys_m = np.maximum(make_interp_spline(t[ok], mm[ok], k=3)(xs), 0)
        ys_h = np.maximum(make_interp_spline(t[ok], hh[ok], k=3)(xs), 0)

        ax.plot(xs, ys_m, '-', color=C_MODEL, lw=2.5, alpha=0.9,
                label='Model identification')
        ax.scatter(t[ok], mm[ok], color=C_MODEL, marker='o', s=40, zorder=5)
        ax.plot(xs, ys_h, '--', color=C_HUMAN, lw=2.5, alpha=0.85,
                label='Human identification')
        ax.scatter(t[ok], hh[ok], color=C_HUMAN, marker='s', s=40, zorder=5)

        # 部位名进 Y 轴标签（替代参考图里的面板标题）
        ax.set_ylabel('%s\ncounts / 10 s' % long_name,
                      fontsize=12, fontweight='bold')
        # zorder 须高于散点(5)，否则标记会压在注记上
        ax.text(0.975, 0.95, 'AR = %.2f%%\nr = %+.2f' % (ar, r),
                transform=ax.transAxes, fontsize=12, fontweight='bold',
                color=C_EMPH, ha='right', va='top', zorder=8,
                bbox=dict(facecolor='white', alpha=0.85, edgecolor='none'))
        ax.grid(True, ls=':', alpha=0.6)
        if i == 0:
            ax.legend(loc='upper left', frameon=True, fontsize=10,
                      edgecolor='gray', framealpha=0.9)

    axes[-1].set_xlabel('Time (s)', fontsize=14, fontweight='bold')
    axes[-1].set_xlim(170, 480)
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.text(0.5, 0.002, 'Fish 21-1', ha='center', va='bottom',
             fontsize=10, color='0.35')
    return fig


def main():
    d = pd.read_excel(CB)
    t = pd.to_numeric(d['开始时间（秒）'], errors='coerce').to_numpy(float)

    for fn, name in ((render_raw, 'Fig6_validation_curve.png'),
                     (render_smooth, 'Fig6_validation_curve_smooth.png')):
        fig = fn(d, t)
        p = os.path.join(OUT, name)
        fig.savefig(p, dpi=DPI)
        plt.close(fig)
        print('[OK] %s   (源 %s)' % (p, os.path.basename(CB)))

    print('   指标（两版一致，均按原始逐窗值计算）:')
    for mc, hc, _short, long_name in SPECS:
        mm = pd.to_numeric(d[mc], errors='coerce').to_numpy(float)
        hh = pd.to_numeric(d[hc], errors='coerce').to_numpy(float)
        ar, r = stats_of(mm, hh)
        print('     %-34s AR=%.2f%%  r=%+.2f' % (long_name, ar, r))


if __name__ == '__main__':
    main()
