"""F5_cost_ratio.py（原 fig6D.py）—— 行为代价比（手稿 Fig.6D）

代价比 = 鳃盖频率 ÷ 游泳速度（cycles / cm），按 10 s 格计算，逐温度箱线 + 原始点。
来源：`P.QUANT/呼吸频率.xlsx` + `P.QUANT/8_速度位移_全身.xlsx`（逐窗绘图）；
      `P.QUANT/per_fish_metrics.csv`（**显著性检验**用逐鱼值）。

显著性（2026-09-15 补）
----------------------
  · **单位必须选对**：图上箱线/散点是**逐 10 s 窗**的值（每温度 ~180 点），
    但观测单位是**鱼**（n = 3/温度）→ 直接在窗上做 ANOVA 属**伪重复（pseudoreplication）**，
    会人为把 P 值做小。故 one-way ANOVA + Tukey HSD 一律用
    `per_fish_metrics.csv` 的**逐鱼 cost_ratio**（15 尾）。
  · 字母标在每组最高点上方，`P` 值标于右上；具体 F / P / 显著对随脚本打印。
  · ⚠ 比值显著**主要由分母（游速）驱动** —— 游速的显著性已单独在 `Fig6B` 报告；
    分子（鳃盖频率）本身对温度并不稳健，故本图仍属**派生指标**，不作独立结论。

落点：`P.SUPP/F5_cost_ratio.png`（PNG @900 DPI）。
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import re
import os

# ================= 1. 配置区域 =================
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口
import freq_style as S         # 阶段5 统一样式 / 配色（唯一真源）

DATA_FREQ = P.QUANT   # 阶段2 归口：呼吸频率.xlsx
FILE_FREQ = '呼吸频率.xlsx'
DIR_BEH = P.QUANT     # 阶段1 归口：8_速度位移_全身.xlsx
FILE_BEH = '8_速度位移_全身.xlsx'

# 全局绘图风格
S.apply_rc_fig6b()          # 与 Fig6B_velocity_displacement.png 同款

PALETTE = S.TEMP_COLORS


# ================= 2. 数据读取与时间戳对齐修复 =================
def parse_sheet_name(sheet_name):
    """从 Sheet 名称中解析温度和重复组"""
    match = re.search(r'(\d+)℃?-(\d+)', str(sheet_name))
    if match: return int(match.group(1)), int(match.group(2))
    return None, None


print("正在读取新表并进行时间轴对齐...")


def _add_bin(df):
    """两表均为 10s 一格、每 (Temp,Rep) 61 格；按组内顺序编号做位置对齐"""
    df = df.sort_values(['Temp', 'Rep', 'Time']).copy()
    df['Bin'] = df.groupby(['Temp', 'Rep']).cumcount()
    return df


# --- 2.1 读取生理特征 (鳃盖频率) ---
phys_list = []
path_freq = os.path.join(DATA_FREQ, FILE_FREQ)
for sheet_name, df in pd.read_excel(path_freq, sheet_name=None,
                                    engine='openpyxl').items():
    temp, rep = parse_sheet_name(sheet_name)
    if temp is None:
        continue
    tcol = [c for c in df.columns if '开始时间' in str(c)][0]
    vcol = [c for c in df.columns
            if str(c) not in ('时间段编号', str(tcol))][0]
    sub = pd.DataFrame({
        'Time': pd.to_numeric(df[tcol], errors='coerce'),
        'Freq_Op': pd.to_numeric(df[vcol], errors='coerce'),
    })
    sub['Temp'], sub['Rep'] = temp, rep
    phys_list.append(sub.dropna())

# --- 2.2 读取行为特征 (游泳速度, 10s 一格) ---
beh_list = []
path_beh = os.path.join(DIR_BEH, FILE_BEH)
for sheet_name, df in pd.read_excel(path_beh, sheet_name=None,
                                    engine='openpyxl').items():
    temp, rep = parse_sheet_name(sheet_name)
    if temp is None:
        continue
    t_col = next((c for c in df.columns if str(c) == 'time/10s'), None)
    v_col = next((c for c in df.columns if str(c) == 'v/10s'), None)
    if t_col is None or v_col is None:
        continue
    sub = pd.DataFrame({
        'Time': pd.to_numeric(df[t_col], errors='coerce'),
        'Velocity': pd.to_numeric(df[v_col], errors='coerce'),
    })
    sub['Temp'], sub['Rep'] = temp, rep
    beh_list.append(sub.dropna())

# --- 2.3 数据融合 (按 10s 格位置对齐) ---
df_phys = _add_bin(pd.concat(phys_list, ignore_index=True))
df_beh = _add_bin(pd.concat(beh_list, ignore_index=True))
df_merged = pd.merge(df_phys, df_beh, on=['Temp', 'Rep', 'Bin'])

# ================= 3. 计算定量指标与数据清洗 =================
# 3.1 过滤静止点
df_valid = df_merged[df_merged['Velocity'] > 0.5].copy()

# 3.2 计算代价比率 (Cost = Frequency / Velocity)
df_valid['Cost'] = df_valid['Freq_Op'] / df_valid['Velocity']

# 3.3 剔除 95% 分位以上的离群点以获得更好的绘图效果
q95 = df_valid['Cost'].quantile(0.95)
df_plot = df_valid[df_valid['Cost'] < q95].copy()

# ================= 3.4 显著性检验（**以逐鱼值为单位**）=================
# ⚠ 关键：图上画的是逐 10 s 窗的值（每温度 ~180 个点），但**观测单位是鱼**（n = 3/温度）。
#   直接在窗上跑 ANOVA 属**伪重复（pseudoreplication）** —— 窗数不是独立样本，
#   会人为把 P 值做小。故检验一律用 `per_fish_metrics.csv` 的**逐鱼 cost_ratio**。
#   （箱线/散点仍按窗显示，仅为分布形状；图注须写明二者单位不同。）
COL_PF = 'cost_ratio'
_pf = S.load_per_fish()
_groups = [_pf.loc[_pf['temp'] == t, COL_PF].to_numpy(float) for t in S.TEMPS]
F_cost, p_cost, agg_cost = S.anova_by_temp(_pf, COL_PF)
letters_cost = S.sig_letters(_groups)
from scipy import stats as _st                                 # noqa: E402
_pv = _st.tukey_hsd(*_groups).pvalue
sig_pairs_cost = [(S.TEMPS[i], S.TEMPS[j])
                  for i in range(len(S.TEMPS)) for j in range(i + 1, len(S.TEMPS))
                  if _pv[i, j] < 0.05]

# ================= 4. 绘制纯客观能效代价量化图 (Fig 6C) =================
plt.figure(figsize=(8.5, 7))
ax = plt.gca()

# 4.1 绘制主体箱线图
sns.boxplot(data=df_plot, x='Temp', y='Cost', hue='Temp', palette=PALETTE,
            ax=ax, showfliers=False, width=0.6, dodge=False)

# 4.2 叠加半透明真实散点
sns.stripplot(data=df_plot, x='Temp', y='Cost', hue='Temp', palette=PALETTE,
              edgecolor='gray', linewidth=0.5, alpha=0.3, size=3.5, dodge=False, jitter=True)

# 移除图例
if ax.get_legend(): ax.get_legend().remove()

# 设置 Y 轴范围（在最高数据点上方留出余量，容纳显著性字母）
global_y_max = df_plot['Cost'].max()
ax.set_ylim(0, global_y_max * 1.24)

# 4.2b 显著性字母（Tukey HSD CLD，**由逐鱼值推出**）—— 置于各组最高点上方
_y_top = df_plot.groupby('Temp')['Cost'].max()
for _i, _t in enumerate(S.TEMPS):
    if _t in _y_top.index:
        ax.text(_i, float(_y_top[_t]) * 1.05, letters_cost[_i],
                ha='center', va='bottom', fontsize=9, fontweight='bold',
                color=S.C_SIG, zorder=6)
ax.text(0.97, 0.97, '$P$ = %.3f' % p_cost, transform=ax.transAxes,
        ha='right', va='top', fontsize=8, color=S.C_SIG,
        bbox=dict(facecolor='white', edgecolor='none', alpha=0.85, pad=1.2))

# 4.3 坐标轴（**沿用用户既有风格**：粗体大字号 + 面板题 + 四边边框）
ax.set_xlabel('Temperature (\u00b0C)', fontsize=11)
ax.set_ylabel('Cost ratio\n(opercular rate / velocity, cycles / cm)', fontsize=11)
ax.set_title('Behavioural cost ratio', fontsize=10, pad=8)

# 为图表加上四周完整的实线边框
for spine in ax.spines.values():
    spine.set_visible(True)

plt.tight_layout()

S.save(plt.gcf(), 'F5_cost_ratio.png', supp=True)

# ================= 5. 检验结果打印 =================
print('\n== cost ratio 显著性（**逐鱼值**，n = 3/温度；非逐窗）==')
print('   one-way ANOVA  F(4,10) = %.3f   P = %.4f' % (F_cost, p_cost))
print('   逐温度均值 ± SEM :')
for t in S.TEMPS:
    m = agg_cost.loc[t, 'mean']
    s = agg_cost.loc[t, 'sem']
    print('     %2d C  %6.3f ± %.3f' % (t, m, s))
print('   Tukey CLD 字母   : %s'
      % dict(zip(S.TEMPS, letters_cost)))
print('   Tukey 显著对     : %s'
      % (sig_pairs_cost if sig_pairs_cost else '无'))
print('   [warn] 图上箱线为**逐窗**值（每温度 ~180 点）；检验为**逐鱼**值 —— 二者单位不同，')
print('          窗值不可直接检验（伪重复）；图注须写明。')
print('   [warn] 分子（鳃盖频率）本身不显著（P = 0.344 于胸鳍 / 0.248 于尾鳍）；')
print('          本比值若显著，主要由**分母（游速）**驱动 —— 游速的显著已单独报告（Fig6B）。')