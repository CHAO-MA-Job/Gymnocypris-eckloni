# -*- coding: utf-8 -*-
"""fig10_metric_structure.py —— 指标结构：相关矩阵 + PCA

目的
----
一次性回答"本项目到底测了**几个独立维度**"：
  · 速度 / 位移 已被证明是同一维度（r = 0.9967，`总览.md` §10-2）；
  · 三部位频率与速度/位移是否独立？`cost_ratio` 是否只是速度的镜像？
若频率落不到自己的主成分上，就把"频率是辅助描述量"从**裁定**升级为**数据结论**。

变量（15 尾 × 6）：`velocity_cm_s`、`displacement_cm`、`operculum_N10s`、
`pectoral_N10s`、`caudal_N10s`、`cost_ratio`。

版面（1 × 2，样式对齐 `Fig6B_velocity_displacement.png`）
  (a) 6 × 6 Pearson 相关矩阵（`RdBu_r`，标注 r）
  (b) PCA 双标图：15 尾得分（按温度着色）+ 载荷箭头；轴注方差解释率

落点：`P.SUPP/Fig10_metric_structure.png`（PNG @900 DPI）。
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口

OUT = P.SUPP
P.ensure(OUT)
DPI = 900

TEMP_COLORS = {16: '#FEE08B', 19: '#FDAE61', 21: '#F46D43',
               23: '#D73027', 25: '#A50026'}
C_SIG = '#D62728'

plt.rcParams.update({
    'font.family': 'Times New Roman', 'mathtext.fontset': 'stix',
    'font.size': 10, 'axes.linewidth': 1.2,
    'xtick.direction': 'in', 'ytick.direction': 'in',
    'axes.grid': False, 'savefig.dpi': DPI, 'svg.fonttype': 'none',
})

VARS = ['velocity_cm_s', 'displacement_cm', 'operculum_N10s',
        'pectoral_N10s', 'caudal_N10s', 'cost_ratio']
SHORT = ['Velocity', 'Displacement', 'Opercular', 'Pectoral', 'Caudal', 'Cost ratio']


def main():
    df = pd.read_csv(P.q('per_fish_metrics.csv'))
    X = df[VARS].to_numpy(float)

    # ---- 相关矩阵 ----
    C = np.corrcoef(X.T)

    # ---- PCA（标准化后，SVD）----
    Z = (X - X.mean(0)) / X.std(0, ddof=1)
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    ev = S ** 2 / (len(Z) - 1)                 # 特征值
    evr = ev / ev.sum() * 100                  # 方差解释率 %
    scores = U * S                             # 主成分得分
    loads = Vt.T                               # 载荷（变量 × PC）

    # ---------------------------------------------------------------- 出图
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.6))

    # (a) 相关矩阵
    ax = axes[0]
    norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
    im = ax.imshow(C, cmap='RdBu_r', norm=norm)
    ax.set_xticks(range(len(SHORT)))
    ax.set_yticks(range(len(SHORT)))
    ax.set_xticklabels(SHORT, rotation=45, ha='right', fontsize=8)
    ax.set_yticklabels(SHORT, fontsize=8)
    for i in range(len(SHORT)):
        for j in range(len(SHORT)):
            ax.text(j, i, '%.2f' % C[i, j], ha='center', va='center',
                    fontsize=7.5,
                    color='white' if abs(C[i, j]) > 0.6 else '#222222')
    ax.set_title('Pearson correlation (n = 15 fish)', fontsize=9)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label('$r$', fontsize=9)
    cb.ax.tick_params(labelsize=8)

    # (b) PCA 双标图
    ax = axes[1]
    k = 2.9
    # 每个变量的标签**手动错位**（Velocity 与 Displacement 箭头几乎同向，自动放必撞）
    LAB = {'Velocity': (0.12, -0.42, 'left', 'top'),
           'Displacement': (0.14, 0.34, 'left', 'bottom'),
           'Cost ratio': (-0.10, 0.06, 'right', 'bottom'),
           'Caudal': (0.10, 0.14, 'left', 'bottom'),
           'Opercular': (-0.12, 0.12, 'right', 'bottom'),
           'Pectoral': (0.06, 0.16, 'left', 'bottom')}
    for v, (lx, ly) in enumerate(zip(loads[:, 0], loads[:, 1])):
        ax.arrow(0, 0, lx * k, ly * k, color='0.35', width=0.012,
                 head_width=0.10, length_includes_head=True, zorder=2)
        ox, oy, ha_, va_ = LAB[SHORT[v]]
        ax.text(lx * k + ox, ly * k + oy, SHORT[v], fontsize=8.5,
                ha=ha_, va=va_, color='0.25', zorder=5,
                bbox=dict(facecolor='white', edgecolor='none',
                          alpha=0.80, pad=0.8))
    for t in sorted(df['temp'].unique()):
        m = (df['temp'] == t).to_numpy()
        ax.scatter(scores[m, 0], scores[m, 1], s=42,
                   color=TEMP_COLORS[int(t)], edgecolor='black',
                   linewidth=0.5, alpha=0.92, zorder=4)
    ax.axhline(0, color='silver', lw=0.8, zorder=0)
    ax.axvline(0, color='silver', lw=0.8, zorder=0)
    ax.set_xlim(-2.7, 4.0)          # 留出右侧标签空间
    ax.set_ylim(-3.5, 3.0)
    ax.set_xlabel('PC1 (%.1f%% of variance)' % evr[0])
    ax.set_ylabel('PC2 (%.1f%% of variance)' % evr[1])
    ax.set_title('PCA of the six per-fish metrics', fontsize=9, pad=8)
    ax.text(0.03, 0.96, 'PC1 + PC2 = %.1f%%' % (evr[0] + evr[1]),
            transform=ax.transAxes, fontsize=8, va='top', color=C_SIG)

    fig.tight_layout()
    p = os.path.join(OUT, 'Fig10_metric_structure.png')
    fig.savefig(p, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print('[OK]', p)

    # ---------------------------------------------------------------- 打印
    print('\n== 相关矩阵（Pearson, n = 15）==')
    print(pd.DataFrame(C, index=SHORT, columns=SHORT).round(3).to_string())
    print('\n== PCA 特征值 / 方差解释率 ==')
    for i in range(len(ev)):
        print('  PC%d  特征值 = %7.4f  解释 = %5.1f%%   累计 = %5.1f%%'
              % (i + 1, ev[i], evr[i], evr[:i + 1].sum()))
    print('\n== 载荷（变量 → PC1 / PC2 / PC3）==')
    L = pd.DataFrame(loads[:, :3], index=SHORT, columns=['PC1', 'PC2', 'PC3'])
    print(L.round(3).to_string())


if __name__ == '__main__':
    main()
