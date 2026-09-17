"""F4_resp_velocity.py（原 fig6C.py）—— 呼吸频率 vs 速度（手稿 Fig.6C）

来源：`P.QUANT/per_fish_metrics.csv`（5 温度 × 3 尾，含速度与鳃盖频率）。
每点 = 1 尾鱼，按温度着色；**纯描述性散点，不加拟合线、不加标题**。
落点：`P.SUPP/F4_resp_velocity.png`（PNG @900 DPI）。
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ================= 1. 配置区域 =================
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口
import freq_style as S         # 阶段5 统一样式 / 配色（唯一真源）

DATA_DIR = P.QUANT   # 阶段2 归口：per_fish_metrics

S.apply_rc_fig6b()          # 与 Fig6B_velocity_displacement.png 同款

PALETTE = S.TEMP_COLORS

# ================= 2. 数据读取 (新表 per_fish_metrics.csv) =================
csv_path = os.path.join(DATA_DIR, 'per_fish_metrics.csv')
if not os.path.exists(csv_path):
    print(f"【严重错误】文件不存在: {csv_path}")
    exit()

df_macro = pd.read_csv(csv_path).rename(columns={
    'temp': 'Temp',
    'fish': 'Rep',
    'velocity_cm_s': 'Mean_Velocity',
    'operculum_N10s': 'Mean_Freq_Op',
})

# ================= 3. 绘制纯客观散点分布图 =================
plt.figure(figsize=(8.5, 7))
ax = plt.gca()

# 仅绘制 15 个独立个体的散点 (去除了所有人为引导线)
sns.scatterplot(data=df_macro, x='Mean_Velocity', y='Mean_Freq_Op',
                hue='Temp', palette=PALETTE, s=220, edgecolor='black',
                linewidth=1.2, alpha=0.9, ax=ax, zorder=2)

# 样式美化与客观标签（**沿用用户既有风格**：粗体大字号 + 面板题 + 四边边框）
ax.set_xlabel('Mean velocity (cm / s)', fontsize=11)
ax.set_ylabel('Opercular rate (beats / 10 s)', fontsize=11)
ax.set_title('Respiration\u2013velocity distribution', fontsize=10, pad=8)

# 图例设置
handles, labels = ax.get_legend_handles_labels()
# 图例置于**轴内右上角**：该象限无数据点
# （x > ~3.3 且 y > ~14 处为空 —— 最快的 23 ℃ 点在 y ≈ 7–10，最靠右的 25 ℃-1 在 x = 3.1）
# 之前重叠是因为旧版图例为 fontsize=12 / title=13（过大），已缩到 8。
ax.legend(handles=handles, labels=labels, title='Temperature (\u00b0C)',
          fontsize=8, title_fontsize=8, loc='upper right',
          borderaxespad=0.5, frameon=True, framealpha=0.92,
          edgecolor='gray', borderpad=0.6, labelspacing=0.85,
          handletextpad=0.6)

# 保留四周实线边框
for spine in ax.spines.values():
    spine.set_visible(True)

plt.tight_layout()

S.save(plt.gcf(), 'F4_resp_velocity.png', supp=True)