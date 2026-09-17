"""F3_coordination.py（原 fig6B.py）—— 部位间协同性（手稿 Fig.6B）

各温度下三对部位的逐窗 Pearson r（鳃盖–胸鳍 / 鳃盖–尾鳍 / 胸鳍–尾鳍）。
来源：`P.QUANT/{呼吸频率,胸鳍摆动频率,尾鳍摆动频率}.xlsx`（各 15 sheet）。
⚠ 描述性图（§10-10）：三部位频率为辅助描述量，本图不作结论。
落点：`P.SUPP/F3_coordination.png`（PNG @900 DPI）。
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import re
import os

# ================= 1. 配置区域 =================
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口
import freq_style as S         # 阶段5 统一样式 / 配色（唯一真源）

DATA_DIR = P.QUANT   # 阶段2 归口：三张频率合并表

S.apply_rc_fig6b()          # 与 Fig6B_velocity_displacement.png 同款

TEMP_COLORS = S.TEMP_COLORS


# ================= 2. 数据读取与对齐 =================
def parse_sheet_name(sheet_name):
    match = re.search(r'(\d+)℃?-(\d+)', str(sheet_name))
    if match: return int(match.group(1)), int(match.group(2))
    return None, None


print("正在读取三部位频率表计算协同性（新表）...")


def load_part(fname, colname):
    """读取单个部位频率表，返回 Temp / Rep / Time / <colname>"""
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        print(f"【严重错误】文件不存在: {path}")
        exit()
    out = []
    for sheet_name, df in pd.read_excel(path, sheet_name=None,
                                        engine='openpyxl').items():
        m = re.search(r'(\d+)\s*℃\s*-\s*(\d+)', str(sheet_name))
        if not m:
            continue
        temp, rep = int(m.group(1)), int(m.group(2))
        tcol = [c for c in df.columns if '开始时间' in str(c)][0]
        vcol = [c for c in df.columns
                if str(c) not in ('时间段编号', str(tcol))][0]
        out.append(pd.DataFrame({
            'Temp': temp,
            'Rep': rep,
            'Time': pd.to_numeric(df[tcol], errors='coerce'),
            colname: pd.to_numeric(df[vcol], errors='coerce'),
        }))
    return pd.concat(out, ignore_index=True)


# 三个部位按 (Temp, Rep, Time) 对齐；必须同一时间点都有数据才保留
df_phys = load_part('呼吸频率.xlsx', 'Freq_Op')
df_phys = df_phys.merge(load_part('胸鳍摆动频率.xlsx', 'Freq_Pec'),
                        on=['Temp', 'Rep', 'Time'])
df_phys = df_phys.merge(load_part('尾鳍摆动频率.xlsx', 'Freq_Cau'),
                        on=['Temp', 'Rep', 'Time'])
df_phys = df_phys.dropna()

# ================= 3. 计算各温度下的相关系数 (协同性) =================
temps = sorted(df_phys['Temp'].unique())
coord_results = []

for temp in temps:
    df_temp = df_phys[df_phys['Temp'] == temp]

    r_op_pec = df_temp['Freq_Op'].corr(df_temp['Freq_Pec'])
    r_op_cau = df_temp['Freq_Op'].corr(df_temp['Freq_Cau'])
    r_pec_cau = df_temp['Freq_Pec'].corr(df_temp['Freq_Cau'])

    coord_results.append({
        'Temp': temp,
        'Operculum vs Pectoral': r_op_pec,
        'Operculum vs Caudal': r_op_cau,
        'Pectoral vs Caudal': r_pec_cau
    })

df_coord = pd.DataFrame(coord_results)

# ================= 4. 绘制协同性演变折线图 =================
plt.figure(figsize=(9, 6))
ax = plt.gca()

# 4.1 画一条 0 刻度的虚线作为参考线 (代表完全不相关)
ax.axhline(0, color='silver', linestyle='-', linewidth=1.5, alpha=0.8, zorder=1)

# 4.2 定义不同身体部位组合的线型 (采用优雅的灰黑配色，不抢温度点的风头)
styles = [
    {'column': 'Operculum vs Pectoral', 'line_color': '#333333', 'linestyle': '-', 'marker': 'o',
     'label': 'Operculum vs Pectoral'},
    {'column': 'Operculum vs Caudal', 'line_color': '#666666', 'linestyle': '--', 'marker': 's',
     'label': 'Operculum vs Caudal'},
    {'column': 'Pectoral vs Caudal', 'line_color': '#999999', 'linestyle': '-.', 'marker': '^',
     'label': 'Pectoral vs Caudal'}
]

# 4.3 绘制主线条与镶嵌温度颜色的点
for style in styles:
    # 先画底层的灰/黑连线
    ax.plot(df_coord['Temp'], df_coord[style['column']],
            color=style['line_color'], linestyle=style['linestyle'],
            linewidth=2.5, label=style['label'], alpha=0.8, zorder=2)

    # 再在每个数据点上画出带有对应温度颜色的 Marker
    for temp in temps:
        val = df_coord[df_coord['Temp'] == temp][style['column']].values[0]
        ax.plot(temp, val, marker=style['marker'], markersize=11,
                markerfacecolor=TEMP_COLORS[temp], markeredgecolor=style['line_color'],
                markeredgewidth=1.5, zorder=3)

# 4.4 样式美化
ax.set_xticks(temps)
ax.set_ylim(-0.6, 1.0)  # 预留显示空间

ax.set_xlabel('Temperature (\u00b0C)', fontsize=11)
ax.set_ylabel("Coordination (Pearson's $r$)", fontsize=11)


# 4.5 图例（线条含义；温度颜色由 x 轴承载，不需额外图例）
ax.legend(title='Part pair', fontsize=8, title_fontsize=8,
          loc='lower left', frameon=False)

# 背景网格
ax.grid(True, linestyle=':', alpha=0.4)

for spine in ax.spines.values():
    spine.set_visible(True)

plt.tight_layout()

S.save(plt.gcf(), 'F3_coordination.png', supp=True)