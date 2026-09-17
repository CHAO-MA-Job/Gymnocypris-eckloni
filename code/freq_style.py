# -*- coding: utf-8 -*-
"""freq_style.py —— 阶段5【频率图统一样式与取数】（唯一实现，禁止各脚本各自复制）

用途
----
`03_Code/05_频率作图/` 下所有 F* 脚本一律 `import freq_style as S`，统一：
  · 配色（温度梯度 + 三部位色 + 强调色）
  · rcParams（字体 / 轴宽 / 刻度朝内 / 900 DPI）
  · 三张频率合并表的读取与长表化
  · 落点（`P.FREQ` = `04_Outputs/05_频率计算/`）
  · **描述性标注**（§10-10：三部位频率为辅助描述量，不作结论 → 每张图必须带 P / n.s.）

口径（与 `总览.md` §9 / §10-10 一致）
-------------------------------------
  · n = 3 尾/温度 × 5 温度（16 / 19 / 21 / 23 / 25 ℃）= 15 尾；窗 = 300 帧 = 10 s。
  · 频率单位 = **次 / 10 s**（beats / 10 s），**不是** Hz。
  · 现行统计：鳃盖 P = 0.015（显著对仅 16≠19、19≠21）；胸鳍 P = 0.344、尾鳍 P = 0.248 —— 无温度效应。
"""
import os
import re
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gyo_paths as P                                    # noqa: E402  统一路径入口

# ------------------------------------------------------------------ 落点
OUT = P.FREQ                 # 阶段5 频率作图（F2）
OUT_SUPP = P.SUPP            # 阶段6 补充作图（F1/F3/F4/F5）
P.ensure(OUT, OUT_SUPP)

# ------------------------------------------------------------------ 配色（唯一真源）
# 温度梯度（`总览.md` §9）
TEMP_COLORS = {16: '#FEE08B', 19: '#FDAE61', 21: '#F46D43',
               23: '#D73027', 25: '#A50026'}
TEMPS = [16, 19, 21, 23, 25]

# 三部位固定色（**用户的既有调色板**，取自 `plot_analysis.py` L53；
# 全阶段5 统一使用这一套，勿改 —— 蓝 / 紫 / 橙）
PART_COLORS = {'operculum': '#2b6cb0',   # 蓝 —— 呼吸
               'pectoral': '#8e44ad',    # 紫 —— 胸鳍
               'caudal': '#e67e22'}      # 橙 —— 尾鳍
PART_LABELS = {'operculum': 'Operculum',
               'pectoral': 'Pectoral fin',
               'caudal': 'Caudal fin'}
PARTS = ['operculum', 'pectoral', 'caudal']

# 运动学量（阶段4 / 散点用；同取自 `plot_analysis.py` L54）
BODY_COLORS = {'velocity': '#2b6cb0', 'displacement': '#2e8b8b', 'cost': '#5d6d7e'}

# 项目「橙-灰-红」体系（§9）：模型 / 人工 / 强调
C_MODEL, C_HUMAN, C_ACCENT = '#F4A460', '#708090', '#D62728'
# 与 `04_行为作图/fig6b_kinematics.py` 同名别名 —— 便于需要与 Fig6B 对齐的脚本直接引用
C_BAR, C_LINE, C_SIG = C_MODEL, C_HUMAN, C_ACCENT

# 三部位对（协同性图，灰阶区分）
PAIR_STYLES = [('operculum', 'pectoral', 'Opercular–Pectoral', '#333333', '-', 'o'),
               ('operculum', 'caudal', 'Opercular–Caudal', '#666666', '--', 's'),
               ('pectoral', 'caudal', 'Pectoral–Caudal', '#999999', '-.', '^')]

# 合并表 → 部位键
FILES = {'operculum': '呼吸频率.xlsx',
         'pectoral': '胸鳍摆动频率.xlsx',
         'caudal': '尾鳍摆动频率.xlsx'}

# 现行 ANOVA（n = 3/温度）。⚠ 仅用于图上的"不显著"提示，引用数值须重算（见 anova_by_temp）。
ANOVA_P = {'operculum': 0.0150, 'pectoral': 0.3435, 'caudal': 0.2475}

# `per_fish_metrics.csv` 的部位 → 列名
PF_COL = {'operculum': 'operculum_N10s', 'pectoral': 'pectoral_N10s',
          'caudal': 'caudal_N10s'}


def apply_rc(font='Arial'):
    """统一 rcParams —— 与 `04_行为作图/plot_analysis.py` 的既有风格对齐。"""
    plt.rcParams.update({
        'font.family': ['sans-serif'],
        'font.sans-serif': [font, 'Helvetica', 'DejaVu Sans', 'sans-serif'],
        'font.size': 8,
        'axes.linewidth': 0.8,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'legend.frameon': False,
        'xtick.direction': 'out',
        'ytick.direction': 'out',
        'axes.grid': False,
        'figure.dpi': 150,
        'savefig.dpi': 900,
        'mathtext.fontset': 'stix',
        'svg.fonttype': 'none',
    })


def apply_rc_fig6b():
    """**与 `04_行为作图/Fig6B_velocity_displacement.png` 同款**样式。

    `Fig6B` 为本项目已定稿的基准图：Times New Roman / `mathtext=stix` /
    `axes.linewidth = 1.2` / 刻度朝内。需要与它"看起来是同一套图"的脚本用本函数。
    """
    plt.rcParams.update({
        'font.family': 'Times New Roman',
        'mathtext.fontset': 'stix',      # 数学字体与 Times 同族
        'font.size': 10,
        'axes.linewidth': 1.2,
        'xtick.direction': 'in',
        'ytick.direction': 'in',
        'axes.grid': False,
        'figure.dpi': 150,
        'savefig.dpi': 900,
        'svg.fonttype': 'none',
    })


def panel_label(ax, s, x=-0.08, y=1.04):
    """面板字母（用户既有风格：`plot_analysis.py` → `panel_label`）。"""
    ax.text(x, y, s, transform=ax.transAxes, fontsize=9,
            fontweight='bold', va='bottom', ha='left')


# ------------------------------------------------------------------ 取数
def parse_sheet(name):
    """sheet 名 `16℃-1` → (16, 1)。"""
    m = re.search(r'(\d+)\s*℃\s*-\s*(\d+)', str(name))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def _read_one(path, part):
    """读单张合并表 → 长表 [part, temp, rep, time, val]。"""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    rows = []
    xl = pd.ExcelFile(path)
    for sh in xl.sheet_names:
        temp, rep = parse_sheet(sh)
        if temp is None:
            continue
        d = xl.parse(sh)
        tcol = [c for c in d.columns if '开始时间' in str(c)][0]
        vcol = [c for c in d.columns
                if str(c) not in ('时间段编号', str(tcol))][0]
        rows.append(pd.DataFrame({
            'part': part, 'temp': temp, 'rep': rep,
            'time': pd.to_numeric(d[tcol], errors='coerce'),
            'val': pd.to_numeric(d[vcol], errors='coerce')}))
    return pd.concat(rows, ignore_index=True)


def load_freq_long(parts=None):
    """三张合并表 → 长表 [part, temp, rep, time, val]（val = 次 / 10 s）。"""
    parts = parts or PARTS
    return pd.concat([_read_one(P.q(FILES[p]), p) for p in parts],
                     ignore_index=True).dropna(subset=['val'])


def load_per_fish():
    """`per_fish_metrics.csv` → 逐鱼标量（含三部位频率 + 速度 + cost_ratio）。"""
    return pd.read_csv(P.q('per_fish_metrics.csv'))


def sig_letters(groups):
    """one-way ANOVA + Tukey HSD → 紧凑字母（CLD）。

    与 `04_行为作图/fig6b_kinematics.py` 同一实现；`groups` 按 TEMPS 顺序给出逐温度样本。
    """
    from scipy import stats
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


def anova_by_temp(df, col):
    """按温度分组做 one-way ANOVA → (F, p, 逐温度 mean/SEM)。"""
    from scipy import stats
    g = [df.loc[df['temp'] == t, col].to_numpy(float) for t in TEMPS]
    F, p = stats.f_oneway(*g)
    agg = df.groupby('temp')[col].agg(['mean', 'sem']).reindex(TEMPS)
    return F, p, agg


# ------------------------------------------------------------------ 绘图小件
def sig_note(ax, p, xy=(0.97, 0.96), fontsize=8):
    """统计注记：**统一给 P 值**（`P` 斜体，mathtext stix）。

    ⚠ **不用 `n.s.`**（2026-09-15 定）：
      · `n.s.` 不是标准符号，各刊要求不一（APA 明确要求给统计量）；
      · 更关键 —— `n.s.` 容易被读成"已证实相等"，而我们要表达的是"**没检出差**"。
    直接给 P 值：信息量更大、三格格式统一、且满足"报告统计量"的要求。
    颜色沿用 `Fig6B` 的注记红（与 F2 的 CLD 字母同色）。
    """
    ax.text(xy[0], xy[1], '$P$ = %.3f' % p, transform=ax.transAxes,
            fontsize=fontsize, ha='right', va='top', color=C_SIG)


def bar_scatter(ax, df, col, color=None, temp_colors=False, jitter_w=0.14):
    """逐鱼散点 + mean ± SEM 折线。

    `temp_colors=True` 时散点按**温度梯度**着色（与 `Fig6B` 嵌图同），折线用 `color`；
    否则散点与折线统一用 `color`。
    """
    agg = df.groupby('temp')[col].agg(['mean', 'sem']).reindex(TEMPS)
    for i, t in enumerate(TEMPS):
        y = df.loc[df['temp'] == t, col].to_numpy(float)
        ax.scatter(np.full(len(y), i) + np.linspace(-jitter_w, jitter_w, len(y)),
                   y, s=26, color=(TEMP_COLORS[t] if temp_colors else color),
                   alpha=0.9, zorder=3, edgecolor='black', linewidth=0.4)
    ax.errorbar(range(len(TEMPS)), agg['mean'], yerr=agg['sem'], fmt='o-',
                color=color, linewidth=1.4, capsize=3, markersize=5,
                markerfacecolor='white', markeredgewidth=1.2, zorder=4)
    ax.set_xticks(range(len(TEMPS)))
    ax.set_xticklabels([str(t) for t in TEMPS])
    return agg


def save(fig, name, supp=False):
    """统一落盘（PNG @900 DPI）。

    `supp=False` → `P.FREQ/<name>`（阶段5，F2）；`supp=True` → `P.SUPP/<name>`（阶段6）。
    """
    out = OUT_SUPP if supp else OUT
    p = os.path.join(out, name)
    fig.savefig(p, dpi=900, bbox_inches='tight')
    plt.close(fig)
    print('[OK]', p)
    return p
