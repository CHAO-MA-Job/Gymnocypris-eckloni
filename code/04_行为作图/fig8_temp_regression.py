# -*- coding: utf-8 -*-
"""fig8_temp_regression.py —— 温度作【连续变量】的回归 + 效应量 / bootstrap CI

为什么做
--------
现行为 5 组 one-way ANOVA（n = 3/温度），功效有限、且只能说"23 ≠ 其余"。
把温度当连续变量、用全部 15 尾拟合二次模型，可给出：
  · **峰值温度 T\\* 及其 bootstrap 95% CI**（"23℃ 最快"的定量版）；
  · 各温度均值的 **bootstrap 95% CI**（不依赖正态假设）；
  · **效应量**（η²、ω²）与 **置换检验**（23 ℃ vs 其余四组，不依赖分布假设）。

版面（1 × 2，样式对齐 `Fig6B_velocity_displacement.png`）
  (a) 速度 vs 温度：15 尾散点（按温度着色）+ **描述性**二次曲线 + bootstrap 95% 带
  (b) 逐温度 mean ± bootstrap 95% CI + 置换检验 P（23 ℃ vs 其余）

⚠ **不做"热最适温度（thermal optimum / TPC）"推断**（2026-09-15 降级）：
  · 二次形式是我们选定的，不是数据推出来的（实测为"平铺 + 23 ℃ 一根尖刺"）；
  · 原 (c) 面板（峰值温度 T\\* 的 bootstrap 分布）**已删除** —— T\\* 由模型顶点定义，
    其"分布"只是模型不确定度，不是最适温度的置信区间；
  · **唯一可陈述的是事实**：在被测的 5 个温度中，23 ℃ 的平均速度最高。
  保留的稳健证据只有两条：Cliff's δ = 1.000（23 ℃ 三尾与其余 12 尾零重叠）
  与置换检验 P = 0.0027（n = 3/温度下已接近该设计能达到的极限）。

⚠ 位移与速度是同一维度（r = 0.9967，见 `总览.md` §10-2）→ 本图只对**速度**做主图，
  位移的同类统计只在打印里给出，不另画一套。
落点：`P.FIG/Fig8_temp_regression.png`（PNG @900 DPI）。
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
DPI = 900
SEED = 20260915
NBOOT = 4000

TEMP_COLORS = {16: '#FEE08B', 19: '#FDAE61', 21: '#F46D43',
               23: '#D73027', 25: '#A50026'}
C_LINE, C_SIG, C_GREY = '#708090', '#D62728', '#555555'

plt.rcParams.update({
    'font.family': 'Times New Roman',
    'mathtext.fontset': 'stix',
    'font.size': 10,
    'axes.linewidth': 1.2,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'axes.grid': False,
    'savefig.dpi': DPI,
    'svg.fonttype': 'none',
})

df = pd.read_csv(P.q('per_fish_metrics.csv'))
TEMPS = sorted(int(t) for t in df['temp'].unique())
T = df['temp'].to_numpy(float)


# ---------------------------------------------------------------- 统计工具
def cohen_eta2(y, groups):
    """one-way ANOVA 的 η² 与 ω²。"""
    from scipy import stats
    F, p = stats.f_oneway(*groups)
    grand = y.mean()
    ss_b = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ss_t = ((y - grand) ** 2).sum()
    ss_w = ss_t - ss_b
    k, n = len(groups), len(y)
    ms_w = ss_w / (n - k)
    eta2 = ss_b / ss_t
    omega2 = (ss_b - (k - 1) * ms_w) / (ss_t + ms_w)
    return F, p, eta2, omega2


def cliffs_delta(a, b):
    """Cliff's δ（秩域效应量，-1..1）。"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    gt = sum((x > b).sum() for x in a)
    lt = sum((x < b).sum() for x in a)
    return (gt - lt) / (len(a) * len(b))


def blocked_bootstrap_idx(rng, t, temps, n=1):
    """按温度分层重抽（保持每组 n 不变）→ 返回索引。"""
    return np.concatenate([rng.choice(np.where(t == tt)[0], n, replace=True)
                           for tt in temps])


def main():
    rng = np.random.default_rng(SEED)

    # ---- (a) 二次拟合 + bootstrap 带 + 峰值 ----
    grid = np.linspace(min(TEMPS), max(TEMPS), 200)
    v_all = df['velocity_cm_s'].to_numpy(float)
    c_obs = np.polyfit(T, v_all, 2)
    curve = np.polyval(c_obs, grid)                # 观测拟合曲线
    t_star = float(-c_obs[1] / (2 * c_obs[0]))     # 观测峰值温度

    boots, peaks = [], []
    for _ in range(NBOOT):
        idx = blocked_bootstrap_idx(rng, T, TEMPS, 3)
        c = np.polyfit(T[idx], v_all[idx], 2)
        if c[0] < 0:                               # 只保留上凸（有峰）的拟合
            boots.append(np.polyval(c, grid))
            peaks.append(-c[1] / (2 * c[0]))
    band = np.percentile(np.array(boots), [2.5, 97.5], axis=0)
    peaks = np.asarray(peaks)
    lo, hi = np.percentile(peaks, [2.5, 97.5])

    # ---- 置换检验：23 ℃ vs 其余四组 ----
    v = df['velocity_cm_s'].to_numpy(float)
    obs = v[T == 23].mean() - np.concatenate([v[T == t] for t in TEMPS if t != 23]).mean()
    perm = np.empty(NBOOT)
    for i in range(NBOOT):
        lab = rng.permutation(T)
        perm[i] = (v[lab == 23].mean()
                   - np.concatenate([v[lab == t] for t in TEMPS if t != 23]).mean())
    p_perm = float((np.abs(perm) >= abs(obs)).mean())

    # ---- 效应量 ----
    F, p_aov, eta2, omega2 = cohen_eta2(v, [v[T == t] for t in TEMPS])
    delta = cliffs_delta(v[T == 23], np.concatenate([v[T == t] for t in TEMPS if t != 23]))

    # ---- 逐温度 bootstrap CI ----
    gmean = np.array([v[T == t].mean() for t in TEMPS])
    ci = np.empty((len(TEMPS), 2))
    for j, t in enumerate(TEMPS):
        b = [v[blocked_bootstrap_idx(rng, T, TEMPS, 3)][T == t].mean()
             for _ in range(1500)]
        ci[j] = np.percentile(b, [2.5, 97.5])

    # 位移的同类统计（只打印）
    d = df['displacement_cm'].to_numpy(float)
    _, p_d, eta2_d, _ = cohen_eta2(d, [d[T == t] for t in TEMPS])
    c_d = np.polyfit(T, d, 2)
    t_star_d = -c_d[1] / (2 * c_d[0]) if c_d[0] < 0 else float('nan')

    # ---------------------------------------------------------------- 出图
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4))

    # (a) 散点 + 二次拟合 + 95% 带
    ax = axes[0]
    for t in TEMPS:
        m = T == t
        ax.scatter(T[m], v[m], s=26, color=TEMP_COLORS[t], edgecolor='black',
                   linewidth=0.4, alpha=0.9, zorder=3)
    ax.fill_between(grid, band[0], band[1], color=C_LINE, alpha=0.18, lw=0,
                    zorder=1, label='Bootstrap 95% band')
    ax.plot(grid, curve, '-', color=C_LINE, lw=2.0, zorder=2,
            label='Descriptive quadratic')
    # ⚠ **不标 T\\***：二次形式是我们选的、不是数据推的（数据实为"平铺 + 23℃ 一根尖刺"），
    #   且 T\\* 的 CI 上界超出观测范围 → 报"热最适温度/TPC"属过度解释。
    #   可陈述的只有事实："在被测的 5 个温度中，23℃ 最快"。
    # 图例置于左上（该处无数据）；η² 注记置于**右上角**（23 ℃ 点簇右侧、拟合曲线上方，无数据）
    # ——两者分处对角，不再重叠。
    ax.legend(frameon=False, fontsize=7.5, loc='upper left')
    ax.set_xticks(TEMPS)
    ax.set_xlabel('Temperature (\u00b0C)')
    ax.set_ylabel('Mean velocity (cm / s)')
    ax.text(0.97, 0.96, '$\\eta^2$ = %.3f' % eta2, transform=ax.transAxes,
            fontsize=8, ha='right', va='top', color=C_GREY,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=1.2))

    # (b) 逐温度 mean ± bootstrap 95% CI + 置换检验
    ax = axes[1]
    for j, t in enumerate(TEMPS):
        ax.errorbar(j, gmean[j], yerr=[[gmean[j] - ci[j, 0]], [ci[j, 1] - gmean[j]]],
                    fmt='o', ms=6, mfc='white', mew=1.4, color=TEMP_COLORS[t],
                    ecolor=TEMP_COLORS[t], elinewidth=1.4, capsize=3, zorder=3)
        ax.scatter(np.full((T == t).sum(), j) + np.linspace(-0.10, 0.10, (T == t).sum()),
                   v[T == t], s=22, color=TEMP_COLORS[t], edgecolor='black',
                   linewidth=0.35, alpha=0.85, zorder=2)
    ax.set_xticks(range(len(TEMPS)))
    ax.set_xticklabels([str(t) for t in TEMPS])
    ax.set_xlabel('Temperature (\u00b0C)')
    ax.set_ylabel('Mean velocity (cm / s)')
    ax.set_ylim(0, float(v.max()) * 1.40)      # 顶部留白，避免注记压住 23℃ 误差棒
    ax.text(0.97, 0.97, '23\u00b0C vs rest\n$P_{perm}$ = %.4f\nCliff $\\delta$ = %.2f'
            % (p_perm, delta), transform=ax.transAxes, fontsize=8, va='top',
            ha='right', color=C_SIG,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.85, pad=1.4))
    # ⚠ 不标 "$P_{ANOVA}$"：用 %.4f 打印必然是 0.0000（真值约 3e-05），
    #   写着没信息、且易被误读成"P = 0"。n = 3/温度时置换检验的 P 才是该报的数
    #   （其精确值随脚本控制台打印，格式 %.2e）。

    # ⚠ **(c) 峰值温度分布面板已删除**（2026-09-15）：
    #   T\\* 由二次模型的顶点定义，而该模型形式是我们选定的 → 其"分布"只是模型不确定度，
    #   不是生物学上的最适温度区间。保留会诱导读者把它读成 TPC 的最适点。
    #   相应数值仍在控制台打印，备查。

    fig.tight_layout()
    p = os.path.join(OUT, 'Fig8_temp_regression.png')
    fig.savefig(p, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print('[OK]', p)

    # ---------------------------------------------------------------- 打印
    print('\n== 速度：温度作连续变量 ==')
    print('  二次模型  v = %.4f T^2 %+.4f T %+.4f' % tuple(c_obs))
    print('  峰值温度 T* = %.2f C   95%% CI = %.2f-%.2f C  (n_boot=%d)'
          % (t_star, lo, hi, len(peaks)))
    print('  一维 ANOVA : F(4,10) = %.3f  P = %.2e  eta2 = %.3f  omega2 = %.3f'
          % (F, p_aov, eta2, omega2))
    print('  置换检验   : 23C vs 其余  delta = %.3f  P_perm = %.4f (n=%d)'
          % (obs, p_perm, NBOOT))
    print('  Cliff delta: 23C vs 其余 = %.3f' % delta)
    print('  逐温度均值与 bootstrap 95% CI:')
    for j, t in enumerate(TEMPS):
        print('    %2d C  mean = %.3f  CI = %.3f-%.3f'
              % (t, gmean[j], ci[j, 0], ci[j, 1]))
    print('\n== 位移（同一维度，仅备查）==')
    print('  P_ANOVA = %.4f  eta2 = %.3f  二次拟合峰值 = %.2f C'
          % (p_d, eta2_d, t_star_d))


if __name__ == '__main__':
    main()
