# -*- coding: utf-8 -*-
"""fig7_trajectory_heatmap.py —— 全身轨迹热图（停留密度 KDE + 同色轨迹）

**一幅图**（2026-09-15 合并版）：3 行 × 5 列
  · 行 = 平行号（1/2/3），列 = 温度（16/19/21/23/25 ℃）
  · 底色 = KDE 停留密度（OrRd）；上层轨迹线**按该点局部密度上色** —— 与热图同一网格取值，
    颜色含义一致（浅橙=路过，深红=久留），故不需要再单出一张"纯轨迹"图。
  · 起点 橙 `#F4A460` / 终点 红 `#D62728`；5 cm 比例尺（仅首格）。

口径（用户指定 2026-09-15）
--------------------------
  · `NORM='per_fish'` —— **每尾各自归一**，看**活动范围形态**；
    （另一口径 `global` = 全库同标度、看强度差异，改常量即可复现。）
  · 统一坐标轴（全体并集 + 外扩）、KDE 共用网格 + 固定带宽 → 跨鱼/跨温度可比。
  · 轨迹在时间缺口（> `GAP_S` 秒）处断开，避免画出虚假连线。

版式（总览 §9，2026-09-15 规则）
-------------------------------
  **不加面板字母、不加额外标题（含 suptitle / set_title）**。
  行/列身份由**坐标轴标签**承载：底部一行温度刻度 + `Temperature (°C)`；
  左侧一列平行号 + `Replicate`。色标保留 colorbar 及其轴标签。

数据源：`P.QUANT/5_公式计算后_全身.xlsx`（逐帧，含 时间S/中心点X/中心点Y）
输出  ：`P.FIG/Fig7_trajectory_heatmap.png`（PNG @900 DPI，落在 `04_行为作图/` 根下）
用法  ：python fig7_trajectory_heatmap.py
"""
import io
import os
import re

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from scipy.stats import gaussian_kde

import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口

SRC_FRAME = P.q("5_公式计算后_全身.xlsx")             # 逐帧（读取慢）
SRC_1HZ = P.q("7_中心点轨迹_全身.xlsx")                # 1 Hz（秒读）
OUT = P.FIG                                        # 阶段4 图根（04_行为作图 根下）
os.makedirs(OUT, exist_ok=True)
CACHE = os.path.join(OUT, "_traj_cache.npz")             # 逐帧数据缓存（源表更新后自动失效）

SRC_MODE = 'frame'               # 'frame'（逐帧，轨迹更连续）| '1hz'（秒读，快速迭代）

# ---------------- 可调参数 ----------------
DPI = 900
GRID_ROWS, GRID_COLS = 3, 5      # 行 = 平行号(1/2/3)，列 = 温度(16→25)
# ★ 最终版式尺寸（出版口径）：183 mm = 双栏整页宽（Nature 规格），不是屏幕预览尺寸。
#   这样 900 DPI 下落到 7.2 in 宽 → 6480 px，缩到正文宽度时字号即为设计值。
FIG_W, FIG_H = 7.2, 3.15
NORM = 'per_fish'                # 'per_fish'（每尾各自归一：看形态）| 'global'（看强度差异）
GRID_N = 200                     # KDE 网格分辨率
BW = 0.18                        # gaussian_kde 带宽（None = Scott 自适应）
KDE_STRIDE = 5                   # KDE 每隔 5 帧取 1 点（逐帧相邻近重复，等时抽样等价）
KDE_CHUNK = 4000                 # KDE 分块求值的网格点数（控内存）
PAD = 0.05                       # 坐标外扩比例
GAP_S = 1.5                      # 时间间隔 > 该值(秒)则断开轨迹线
SCALE = 0.03125                  # cm/px（项目常量）
BAR_CM = 5.0                     # 比例尺长度

# ---- 字号层级（密排期刊图：正文 7 pt / 轴标签 8.5 pt）----
FS_BASE = 7
FS_LABEL = 8.5
FS_TICK = 7
FS_ANN = 6.5

# ---- 线宽（Nature 风格：细而清）----
AXES_LW = 0.6
FRAME_C = '#cccccc'              # 子图边框（浅灰，仅作分格用，避免重框）

# ===== 统一到项目「橙灰红」体系（总览 §9）：橙 #F4A460 / 灰 #708090 / 红 #D62728 =====
C_START = '#F4A460'              # 起点（橙）
C_END = '#D62728'                # 终点（红）
C_FACE = '#ffffff'               # 子图底色（留白，衬托 OrRd）
C_GRID = '#767676'               # 中性灰（共享图例文字）
CMAP = 'OrRd'                    # 唯一色标（橙红）
TRAJ_VMIN = 0.28                 # 轨迹画布颜色下限（保证低密度段仍可见）
TRAJ_LW = 0.28                   # 热图画布线宽（密排小图，需细）
TRAJ_MS = 3.0                    # 起终点标记尺寸
try:                             # matplotlib >= 3.5 的现代取色标 API
    _cmap = matplotlib.colormaps[CMAP]
except Exception:                # 兼容更老版本
    _cmap = plt.get_cmap(CMAP)

# 可编辑矢量（若另出 SVG/PDF）：文字保持 <text> 节点
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = FS_BASE
plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['axes.linewidth'] = AXES_LW


def save_png(fig, path, dpi):
    """先渲染到内存、再以二进制落盘。

    规避本机 matplotlib.imsave → PIL 在**超大画布**上抛
    `OSError: [Errno 22] Invalid argument` 的问题（目标文件本身并未被占用）。
    """
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi)
    data = buf.getvalue()
    buf.close()
    with open(path, 'wb') as f:
        f.write(data)
    print('   %s  %.2f MB' % (os.path.basename(path), len(data) / 1e6))


def skey(name):
    """行 = 平行号、列 = 温度（与历史版排序一致）。"""
    m = re.search(r'(\d+)\s*℃\s*-\s*(\d+)', str(name))
    return (int(m.group(2)), int(m.group(1))) if m else (9999, 9999)


def load():
    """返回 (names, {sheet: (t, x, y)})。逐帧模式带 npz 缓存（源表更新后自动失效）。"""
    src = SRC_FRAME if SRC_MODE == 'frame' else SRC_1HZ

    if SRC_MODE == 'frame' and os.path.exists(CACHE) \
            and os.path.getmtime(CACHE) >= os.path.getmtime(src):
        z = np.load(CACHE, allow_pickle=True)
        names = [str(s) for s in z['names']]
        data = {sh: (z['t%d' % i], z['x%d' % i], z['y%d' % i])
                for i, sh in enumerate(names)}
        print('从缓存读取 (%d 条鱼): %s' % (len(names), CACHE))
        return names, data

    xl = pd.ExcelFile(src)
    names = sorted(xl.sheet_names, key=skey)
    data = {}
    for sh in names:
        d = pd.read_excel(src, sheet_name=sh,
                          usecols=['时间S', '中心点X', '中心点Y'])
        d = d.dropna(subset=['中心点X', '中心点Y']).sort_values('时间S')
        data[sh] = (d['时间S'].to_numpy(float),
                    d['中心点X'].to_numpy(float),
                    d['中心点Y'].to_numpy(float))
        print('  已读 %s (%d 点)' % (sh, len(d)))

    if SRC_MODE == 'frame':
        payload = {'names': np.array(names, dtype=object)}
        for i, v in enumerate(data.values()):
            payload['t%d' % i] = v[0]
            payload['x%d' % i] = v[1]
            payload['y%d' % i] = v[2]
        np.savez_compressed(CACHE, **payload)
        print('已写缓存:', CACHE)
    return names, data


def main():
    names, data = load()

    # ---- 行列身份（从 sheet 名解析，稳健）----
    keys = [skey(n) for n in names]
    row_reps = sorted({k[0] for k in keys})
    col_temps = sorted({k[1] for k in keys})

    # ---- ① 统一坐标轴：全体并集 + 外扩 ----
    ax_x0 = min(d[1].min() for d in data.values())
    ax_x1 = max(d[1].max() for d in data.values())
    ax_y0 = min(d[2].min() for d in data.values())
    ax_y1 = max(d[2].max() for d in data.values())
    dx, dy = (ax_x1 - ax_x0) * PAD, (ax_y1 - ax_y0) * PAD
    ax_x0, ax_x1 = ax_x0 - dx, ax_x1 + dx
    ax_y0, ax_y1 = ax_y0 - dy, ax_y1 + dy
    gx, gy = np.mgrid[ax_x0:ax_x1:GRID_N * 1j, ax_y0:ax_y1:GRID_N * 1j]
    print('统一坐标轴  x: %.0f~%.0f  y: %.0f~%.0f' % (ax_x0, ax_x1, ax_y0, ax_y1))

    # ---- ② KDE：共用网格 + 固定带宽（抽样 + 分块求值，控内存）----
    pts = np.vstack([gx.ravel(), gy.ravel()])
    dens = {}
    for n_done, (sh, (t, x, y)) in enumerate(data.items(), 1):
        k = gaussian_kde(np.vstack([x[::KDE_STRIDE], y[::KDE_STRIDE]]),
                         bw_method=BW)
        out = np.empty(pts.shape[1])
        for i in range(0, pts.shape[1], KDE_CHUNK):
            out[i:i + KDE_CHUNK] = k(pts[:, i:i + KDE_CHUNK])
        dens[sh] = out.reshape(gx.shape)
        print('  KDE %d/%d  %s' % (n_done, len(data), sh), flush=True)
    vmax = max(z.max() for z in dens.values()) if NORM == 'global' else 1.0

    # ---- 数据质量报告 ----
    print('\n== 数据质量 ==')
    for sh in names:
        t = data[sh][0]
        gaps = np.where(np.diff(t) > GAP_S)[0]
        miss = int(np.sum(np.diff(t)[np.diff(t) > GAP_S] - 1))
        print('  %-8s 点数=%4d  时长=%3.0f s  断段=%d 处  缺 %d s'
              % (sh, len(t), t.max() - t.min(), len(gaps), miss))

    # ---- ③ 绘图（单一幅）----
    fig, axes = plt.subplots(GRID_ROWS, GRID_COLS, figsize=(FIG_W, FIG_H))
    im = None
    for i, sh in enumerate(names):
        if i >= GRID_ROWS * GRID_COLS:
            break
        r, c = divmod(i, GRID_COLS)
        t, x, y = data[sh]
        z = dens[sh] / (dens[sh].max() if NORM == 'per_fish' else vmax)

        # 轨迹每点的局部停留密度：与热图**同一网格**取值 → 颜色含义一致
        ix = np.clip(((x - ax_x0) / (ax_x1 - ax_x0) * (GRID_N - 1)).round().astype(int),
                     0, GRID_N - 1)
        iy = np.clip(((y - ax_y0) / (ax_y1 - ax_y0) * (GRID_N - 1)).round().astype(int),
                     0, GRID_N - 1)
        v = z[iy, ix]

        # 轨迹线段（缺口处断开：仅保留 dt <= GAP_S 的相邻点对）
        keep = np.diff(t) <= GAP_S
        if keep.any():
            segs = np.stack([np.column_stack([x[:-1], y[:-1]])[keep],
                             np.column_stack([x[1:], y[1:]])[keep]], axis=1)
            cols = _cmap(TRAJ_VMIN + (1 - TRAJ_VMIN) * v[:-1][keep])
        else:
            segs, cols = None, None

        ax = axes[r, c]
        im = ax.pcolormesh(gx, gy, z, shading='auto', cmap=CMAP, vmin=0, vmax=1)
        if segs is not None:
            ax.add_collection(LineCollection(segs, colors=cols,
                                             linewidths=TRAJ_LW, zorder=3))
        ax.scatter(x[0], y[0], color=C_START, s=TRAJ_MS ** 2, zorder=5,
                   edgecolors='white', linewidths=0.5)
        ax.scatter(x[-1], y[-1], color=C_END, s=TRAJ_MS ** 2, zorder=5,
                   edgecolors='white', linewidths=0.5)
        ax.set_facecolor(C_FACE)
        ax.set_xlim(ax_x0, ax_x1)
        ax.set_ylim(ax_y1, ax_y0)      # 图像 y 向下
        ax.set_aspect('equal')

        # 分格线：浅灰细线（仅用于切分白色瓦片，非装饰性重框）
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_linewidth(AXES_LW)
            sp.set_color(FRAME_C)

        # ---- 行列身份改用轴标签（不加标题、不加面板字母）----
        ax.set_xticks([(ax_x0 + ax_x1) / 2])
        ax.set_yticks([(ax_y0 + ax_y1) / 2])
        ax.set_xticklabels([str(col_temps[c])] if r == GRID_ROWS - 1 else [],
                           fontsize=FS_TICK)
        ax.set_yticklabels([str(row_reps[r])] if c == 0 else [], fontsize=FS_TICK)
        ax.tick_params(length=0, pad=2)

        # ---- 比例尺（仅首个面板；须在图内才能标定）----
        if i == 0:
            L = BAR_CM / SCALE
            bx, by = ax_x0 + dx * 0.6, ax_y1 - dy * 1.2
            ax.plot([bx, bx + L], [by, by], color='black', lw=1.8,
                    solid_capstyle='butt', zorder=6)
            # 文字抬高到黑条上方（y 轴已被反转，较小 y 在屏幕上更高）
            ax.text(bx + L / 2, by - dy * 1.0, '%g cm' % BAR_CM,
                    ha='center', va='bottom', fontsize=FS_ANN, zorder=6)

    # 空位隐藏
    for i in range(len(names), GRID_ROWS * GRID_COLS):
        r, c = divmod(i, GRID_COLS)
        axes[r, c].axis('off')

    lab = ('Relative density (per fish)' if NORM == 'per_fish'
           else 'Relative density (shared scale)')

    # 版式：底部留出共享轴标签 + 共享图例条；**不加 suptitle / 面板字母**
    fig.tight_layout(rect=(0.030, 0.065, 0.905, 0.955))
    cax = fig.add_axes([0.922, 0.20, 0.010, 0.70])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label(lab, fontsize=FS_LABEL)
    cb.outline.set_linewidth(AXES_LW)
    cb.outline.set_edgecolor(FRAME_C)
    cb.ax.tick_params(length=0, labelsize=FS_TICK)

    fig.supxlabel('Temperature (\u00b0C)', fontsize=FS_LABEL, y=0.028)
    fig.supylabel('Replicate', fontsize=FS_LABEL, x=0.012)

    # 共享图例条（frameless，置于网格下方）—— 取代各格内图例，避免遮挡数据
    handles = [Line2D([], [], marker='o', ls='', ms=3.5, mfc=C_START,
                      mec='white', mew=0.5, label='Start'),
               Line2D([], [], marker='o', ls='', ms=3.5, mfc=C_END,
                      mec='white', mew=0.5, label='End')]
    fig.legend(handles=handles, loc='upper center',
               bbox_to_anchor=(0.465, 1.002), ncol=2, frameon=False,
               fontsize=FS_TICK, handletextpad=0.35, columnspacing=1.4)

    p = os.path.join(OUT, 'Fig7_trajectory_heatmap.png')
    save_png(fig, p, DPI)
    if os.environ.get('FIG7_SVG') == '1':     # 按需另出可编辑矢量（项目默认只出 PNG）
        svg = os.path.join(OUT, 'Fig7_trajectory_heatmap.svg')
        fig.savefig(svg, bbox_inches='tight')
        print('   %s (矢量，文字可编辑)' % os.path.basename(svg))
    plt.close(fig)
    print('[OK]', p)


if __name__ == '__main__':
    main()
