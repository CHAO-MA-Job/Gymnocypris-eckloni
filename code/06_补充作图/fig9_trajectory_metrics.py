# -*- coding: utf-8 -*-
"""fig9_trajectory_metrics.py —— 轨迹几何指标（把 Fig7 热图**量化**）

现状：`Fig7_trajectory_heatmap.py` 只把轨迹画成图，**没有量化**。本脚本算出 4 个
几何指标并按温度比较 —— 它们**不依赖频率那套计数后处理**，是本项目里独立于
"计数层"的一组运动学证据。

指标（逐尾，全时长）
  · **直线度 D/L** = 净位移 / 路径长（0–1）
  · **平均转向角** = 相邻两步方向夹角的均值（度）
  · **Burst 占比** = 秒步速度 > 2 × 该尾中位速度 的步数占比
  · **占用面积**   = 该尾 (x, y) 轨迹**凸包**面积（cm^2）

数据源（**2026-09-15 修正**）
  `P.QUANT/7_中心点轨迹_全身.xlsx` —— **1 Hz**（605 行 = 0..604 s，一行一秒）。
  ⚠ 为什么不用逐帧的 `5_公式计算后_全身.xlsx`：
    ① 该表的 `时间S` **只精确到整秒**（605 个唯一值），逐帧 dt 绝大多数为 0，
       无法按帧计时；
    ② 逐帧中心点抖动（检测噪声）主导 Σ|Δp|，线长被噪声撑大 → 几何指标失真。
  → 先在 1 Hz 上算：时间轴干净、抖动被平均掉，且**跨尾可比**。
    代价是线长偏短（秒内走弦长），故各指标一律作**相对比较**用，不报绝对值。

L 闭合校验（**先校验，不通过直接报错、不出图**）
  1 Hz 线长必然 ≤ 逐帧累计路径（`8_速度位移_全身.S/总位移_结束`），
  且不应小得离谱；越界即抛错，避免再产出不可用的中间稿。

版面（**2 × 2**，样式对齐 `Fig6B_velocity_displacement.png`）：逐鱼散点 + mean ± SEM + ANOVA P；
每个面板都带自己的横轴刻度（温度），便于独立裁切使用。
落点：`P.SUPP/Fig9_trajectory_metrics.png` + `P.SUPP/_traj_metrics.csv`（PNG @900 DPI）。
"""
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口

OUT = P.SUPP
P.ensure(OUT)
DPI = 900
SCALE = 0.03125                # cm/px（项目常量）

# 闭合校验阈值：1 Hz 弦长 / 逐帧路径
RATIO_MIN, RATIO_MAX = 0.30, 1.02

TEMP_COLORS = {16: '#FEE08B', 19: '#FDAE61', 21: '#F46D43',
               23: '#D73027', 25: '#A50026'}
C_LINE, C_SIG, C_GREY = '#708090', '#D62728', '#555555'

plt.rcParams.update({
    'font.family': 'Times New Roman', 'mathtext.fontset': 'stix',
    'font.size': 10, 'axes.linewidth': 1.2,
    'xtick.direction': 'in', 'ytick.direction': 'in',
    'axes.grid': False, 'savefig.dpi': DPI, 'svg.fonttype': 'none',
})


def metrics_of(t, x, y):
    """1 Hz (时间S, X, Y) -> 几何指标。

    ⚠ 1 Hz 表**只包含有检出的秒**（缺秒即缺行，23℃ 尤其明显），
      故必须用 `dt = diff(时间S)` 而非"一行一秒"：
        · **线长 L** 保留所有相邻点对（与逐帧表的 ΣS/单次位移 同口径，含跨缺口弦长）；
        · **转向角 / burst** 只用 `dt == 1` 的相邻对（跨缺口的夹角/速度无意义）；
      **按给定顺序**处理，不排序（`时间S` 有重复风险时排序会打乱帧序 —— 见 2026-09-15 修正）。
    """
    dt = np.diff(t)
    dx, dy = np.diff(x), np.diff(y)
    step = np.hypot(dx, dy) * SCALE                    # cm
    L = float(step.sum())                              # 线长（含缺口弦长）
    D = float(np.hypot(x[-1] - x[0], y[-1] - y[0]) * SCALE)   # 净位移
    good = dt == 1                                     # 无缺口相邻对

    turn = np.nan
    if good.sum() > 2:
        v1 = np.column_stack([dx[:-1], dy[:-1]])[good[:-1] & good[1:]]
        v2 = np.column_stack([dx[1:], dy[1:]])[good[:-1] & good[1:]]
        n1, n2 = np.linalg.norm(v1, axis=1), np.linalg.norm(v2, axis=1)
        ok = (n1 > 0.5) & (n2 > 0.5)                   # > 0.5 px，剔除静止抖动
        if ok.sum() > 2:
            cos = (v1[ok] * v2[ok]).sum(1) / (n1[ok] * n2[ok])
            turn = float(np.degrees(np.arccos(np.clip(cos, -1, 1))).mean())

    spd = step[good] / dt[good]                        # cm/s（只用无缺口对）
    burst = float((spd > 2 * np.median(spd)).mean()) if len(spd) else np.nan

    area = np.nan
    pts = np.column_stack([x, y])
    if len(pts) > 3:
        try:
            area = float(ConvexHull(pts).volume * SCALE ** 2)   # 2D: volume = 面积
        except Exception:                                       # 共线退化
            area = np.nan
    return dict(L=L, D=D, straight=(D / L if L > 0 else np.nan),
                turn=turn, burst=burst, area=area)


def main():
    xl = pd.ExcelFile(P.q('7_中心点轨迹_全身.xlsx'))
    # 逐帧累计路径（闭合校验的参照）：8_速度位移 表每 sheet 很小，直接取 max
    ref = {sh: float(pd.to_numeric(d['S/总位移_结束'], errors='coerce').max())
           for sh, d in pd.read_excel(P.q('8_速度位移_全身.xlsx'),
                                      sheet_name=None).items()}

    rows, problems = [], []
    for sh in xl.sheet_names:
        m = re.search(r'(\d+)\s*℃\s*-\s*(\d+)', str(sh))
        if not m:
            continue
        d = xl.parse(sh)
        t = pd.to_numeric(d['时间S'], errors='coerce').to_numpy(float)
        x = pd.to_numeric(d['中心点X'], errors='coerce').to_numpy(float)
        y = pd.to_numeric(d['中心点Y'], errors='coerce').to_numpy(float)
        if not np.all(np.diff(t) > 0):
            problems.append('%s 时间S 非严格递增' % sh)
        # 缺秒报告（1 Hz 表只含有检出的秒）——不判失败，但要如实记录
        n_miss = int((np.diff(t) - 1).sum())
        r = metrics_of(t, x, y)
        s_ref = ref.get(sh, np.nan)
        ratio = r['L'] / s_ref if s_ref else np.nan
        r.update(temp=int(m.group(1)), fish=int(m.group(2)),
                 S_total=s_ref, ratio=ratio, n_miss=n_miss)
        if not (RATIO_MIN <= ratio <= RATIO_MAX):
            problems.append('%s 闭合校验失败：L/L_per-frame = %.3f（期望 %.2f-%.2f）'
                            % (sh, ratio, RATIO_MIN, RATIO_MAX))
        rows.append(r)

    if problems:
        print('[校验不通过] 共 %d 项：' % len(problems))
        for p_ in problems:
            print('   -', p_)
        raise SystemExit('轨迹指标校验未通过，**不产出图**（避免留下不可用结果）')

    df = pd.DataFrame(rows).sort_values(['temp', 'fish']).reset_index(drop=True)
    temps = sorted(df['temp'].unique())
    print('[校验通过] %d 尾全部满足 %.2f <= L/L_per-frame <= %.2f'
          % (len(df), RATIO_MIN, RATIO_MAX))
    print('  L/L_per-frame : mean = %.3f  范围 %.3f-%.3f'
          % (df['ratio'].mean(), df['ratio'].min(), df['ratio'].max()))
    print('  1 Hz 缺秒数（表只含有检出的秒）: mean = %.1f  范围 %d-%d'
          % (df['n_miss'].mean(), df['n_miss'].min(), df['n_miss'].max()))
    for t in temps:
        sub = df[df['temp'] == t]
        print('    %2d C  缺秒 %s' % (t, sub['n_miss'].astype(int).tolist()))

    SPECS = [('straight', 'Straightness ($D$ / $L$)', None),
             ('turn', 'Mean turning angle (\u00b0)', None),
             ('burst', 'Burst fraction of steps', None),
             ('area', 'Occupancy area (cm$^2$)', None)]

    fig, axes = plt.subplots(2, 2, figsize=(7.6, 6.0))     # **2 行 2 列**
    out = {}
    for ax, (key, ylab, _) in zip(axes.ravel(), SPECS):
        g = df.groupby('temp')[key]
        mean = g.mean().reindex(temps).to_numpy(float)
        sem = g.sem().reindex(temps).to_numpy(float)
        for i, t in enumerate(temps):
            yv = df.loc[df['temp'] == t, key].dropna().to_numpy(float)
            ax.scatter(np.full(len(yv), i) + np.linspace(-0.10, 0.10, len(yv)), yv,
                       s=26, color=TEMP_COLORS[t], edgecolor='black',
                       linewidth=0.4, alpha=0.9, zorder=3)
        ax.errorbar(range(len(temps)), mean, yerr=sem, fmt='o-', color=C_LINE,
                    linewidth=1.4, capsize=3, markersize=5,
                    markerfacecolor='white', markeredgewidth=1.2, zorder=4)
        ax.set_xticks(range(len(temps)))
        ax.set_xticklabels([str(t) for t in temps])
        ax.set_xlabel('Temperature (\u00b0C)', labelpad=4)
        ax.set_ylabel(ylab, labelpad=5)
        ax.set_ylim(top=float(np.nanmax([df[key].max(), mean.max() + sem.max()])) * 1.22)
        groups = [df.loc[df['temp'] == t, key].dropna().to_numpy(float) for t in temps]
        F, p = stats.f_oneway(*groups)
        grand = df[key].mean()
        eta2 = (sum(len(g_) * (g_.mean() - grand) ** 2 for g_ in groups)
                / ((df[key] - grand) ** 2).sum())
        ax.text(0.97, 0.97, '$P$ = %.3f' % p, transform=ax.transAxes,
                fontsize=8, ha='right', va='top', color=C_SIG,
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=1.2))
        ax.text(0.03, 0.97, '$\\eta^2$ = %.2f' % eta2, transform=ax.transAxes,
                fontsize=8, va='top', color=C_GREY,
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=1.2))
        out[key] = (F, p, eta2, mean)

    fig.tight_layout()
    # ⚠ 多重比较说明（2026-09-15 补）：4 项指标同图检验，未做校正
    fig.text(0.5, -0.035,
             'No multiple-comparison correction: none of the four metrics reaches the '
             'Bonferroni-adjusted threshold (\u03b1 = 0.0125 for 4 tests).\n'
             'Burst fraction does not even reach nominal significance (P = 0.063). '
             'Exploratory only \u2014 the 23 \u00b0C group additionally has missing '
             'seconds (14 / 14 / 35), which may bias burst downward.',
             ha='center', va='top', fontsize=7, color='0.35')

    p_out = os.path.join(OUT, 'Fig9_trajectory_metrics.png')
    fig.savefig(p_out, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print('[OK]', p_out)

    print('\n== 轨迹几何指标（1 Hz；one-way ANOVA, n = 3/温度）==')
    for key, ylab, _ in SPECS:
        F, p, eta2, mean = out[key]
        print('  %-9s F(4,10)=%7.2f  P=%.4f  eta2=%.3f   逐温度均值=%s'
              % (key, F, p, eta2, np.round(mean, 3)))
    # 注：Windows GBK 控制台无法输出 '⚠'，故打印统一用 [warn]
    print('\n  [warn] 多重比较（Bonferroni, 4 项检验 -> \u03b1 = 0.0125）：')
    for key, ylab, _ in SPECS:
        _, p, _, _ = out[key]
        print('    %-9s P = %.4f  -> %s' % (key, p,
              'pass' if p < 0.0125 else
              ('nominal only' if p < 0.05 else 'n.s.')))
    print('    => 四项均未过校正；burst 连名义显著（0.05）都未达到。'
          '\n    => 23 ℃ 三尾分别缺 14/14/35 秒，可能把 burst 系统性压低 —— 与检出缺口混淆，'
          '\n       以上结果属**探索性**，不作结论。')
    print('\n== 逐尾明细 ==')
    print(df.drop(columns=['S_total']).round(4).to_string(index=False))
    csv = os.path.join(OUT, '_traj_metrics.csv')
    df.to_csv(csv, index=False, encoding='utf-8-sig')
    print('已写明细:', csv)


if __name__ == '__main__':
    main()
