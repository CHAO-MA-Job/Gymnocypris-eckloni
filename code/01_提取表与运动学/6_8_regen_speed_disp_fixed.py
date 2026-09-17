"""6_8_regen_speed_disp_fixed.py
重算并修复 速度位移_全身.xlsx:

⚠ 列名口径（勿误读）: 输出列 `v/10s` / `v/10秒` 与 `v/cm_mean` **数值完全相同**——
  三者都是**块内逐帧 `v/cm` 的均值，单位 cm/s（每秒速度）**。
  列名里的 "10s" 指"每 10 秒一块"（分块粒度），**不是**"速度 ÷ 10 秒"。
  表内自证: `S/10s` ≈ `v/10s` x 10 s（16℃-1 第 1 块 2.2403 x 10 = 22.403 ≈ 22.2544 cm）。
 问题1修复: 原 5 个10秒聚合列(time/10s,v/10s,time/10秒,v/10秒,S/10s) 直接照搬源表,
            而源表按300帧一块广播, 与"每10秒(时间S//10)"分块边界错开1帧, 导致相邻块数值重复.
            现改为用每块内逐帧数据重新计算, 与块边界严格一致.
 问题2新增: 每10秒加速度
            - 加速度_mean/std (cm/s²): 块内逐帧 a=dv/dt 的均值/标准差 (瞬时加速度的块内统计)
            - 加速度_块间差分 (cm/s²): 相邻块平均 Speed 之差 / 10s (整体速度趋势的加速度)
输出: 04_Outputs/02_模型量化数据_GH1/8_速度位移_全身.xlsx (覆盖)
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源）

SRC = Path(P.q('5_公式计算后_全身.xlsx'))
# 一并修复: 速度位移(原版已删, 写回原名) 与 总结版(同样有重复bug)
OUTS = [
    Path(P.q('8_速度位移_全身.xlsx')),
    Path(P.q('6_总结版_全身.xlsx')),
]

xls = pd.ExcelFile(SRC)
sheets = xls.sheet_names

def summarize(g: pd.DataFrame) -> pd.Series:
    g = g.sort_values('帧编号').copy()
    first = g.iloc[0]; last = g.iloc[-1]
    b = int(g['时间S'].iloc[0] // 10)
    s = {}
    s['块序号'] = b + 1
    s['时间区间S'] = f'{b*10}-{(b+1)*10}'
    s['起始帧编号'] = int(first['帧编号']); s['结束帧编号'] = int(last['帧编号'])
    s['时间戳_起始'] = first['时间戳']; s['类别'] = int(g['类别'].mode().iloc[0])
    s['坐标_起始'] = first['坐标']; s['坐标_结束'] = last['坐标']
    s['中心点X_mean'] = g['中心点X'].mean(); s['中心点Y_mean'] = g['中心点Y'].mean()
    s['中心点X_std'] = g['中心点X'].std(); s['中心点Y_std'] = g['中心点Y'].std()
    s['x1_mean'] = g['x1'].mean(); s['y1_mean'] = g['y1'].mean()
    s['x2_mean'] = g['x2'].mean(); s['y2_mean'] = g['y2'].mean()
    s['换算比例'] = first['换算比例']
    s['置信度_mean'] = g['置信度'].mean(); s['置信度_std'] = g['置信度'].std()
    for col in ['v/cm', 'v/像素点', 'S/单次位移']:
        s[f'{col}_mean'] = g[col].mean(); s[f'{col}_std'] = g[col].std()
        s[f'{col}_min'] = g[col].min(); s[f'{col}_max'] = g[col].max()
    s['S/单次位移_总和'] = g['S/单次位移'].sum()
    s['S/总位移_起始'] = first['S/总位移']; s['S/总位移_结束'] = last['S/总位移']
    s['S/总位移_块内增量'] = last['S/总位移'] - first['S/总位移']
    # 块内逐帧瞬时加速度 a = dv/dt (cm/s²); v/cm 已为 cm/s
    a = g['v/cm'].diff() / g['帧间dt(s)']
    s['加速度_mean (cm/s²)'] = a.mean(); s['加速度_std (cm/s²)'] = a.std()
    s['加速度_max (cm/s²)'] = a.max(); s['加速度_min (cm/s²)'] = a.min()
    # 重新计算的10秒聚合列(严格对齐本块边界, 不再照搬源表广播值)
    s['time/10s'] = (b + 1) * 10
    s['time/10秒'] = (b + 1) * 10
    s['v/10s'] = g['v/cm'].mean()          # 块内平均速度 cm/s
    s['v/10秒'] = g['v/cm'].mean()
    s['S/10s'] = g['S/单次位移'].sum()     # 块内总位移 cm
    s['帧间dt(s)'] = first['帧间dt(s)']
    return pd.Series(s)

ordered = [
    '块序号','时间区间S','起始帧编号','结束帧编号','时间戳_起始','类别',
    '坐标_起始','坐标_结束',
    '中心点X_mean','中心点Y_mean','中心点X_std','中心点Y_std',
    'x1_mean','y1_mean','x2_mean','y2_mean',
    '换算比例','置信度_mean','置信度_std',
    'v/cm_mean','v/cm_std','v/cm_min','v/cm_max',
    'v/像素点_mean','v/像素点_std','v/像素点_min','v/像素点_max',
    'S/单次位移_mean','S/单次位移_std','S/单次位移_min','S/单次位移_max','S/单次位移_总和',
    'S/总位移_起始','S/总位移_结束','S/总位移_块内增量',
    '加速度_mean (cm/s²)','加速度_std (cm/s²)','加速度_min (cm/s²)','加速度_max (cm/s²)',
    '帧间dt(s)','time/10s','v/10s','time/10秒','v/10秒','S/10s',
]

out = {}
for sh in sheets:
    df = pd.read_excel(SRC, sheet_name=sh)
    if df.empty:
        out[sh] = pd.DataFrame(columns=ordered); continue
    summ = df.groupby(df['时间S'] // 10, group_keys=False).apply(summarize, include_groups=False).reset_index(drop=True)
    # 块间加速度差分: (本块平均速度 - 上块平均速度)/10s
    summ['加速度_块间差分 (cm/s²)'] = summ['v/10s'].diff() / 10.0
    summ = summ[ordered + ['加速度_块间差分 (cm/s²)']]
    out[sh] = summ
    print(f'[{sh}] 块数={len(summ)}  头两块的 v/10s={summ["v/10s"].head(2).round(4).tolist()}  S/10s={summ["S/10s"].head(2).round(3).tolist()}')

for OUT in OUTS:
    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        for sh, d in out.items():
            d.to_excel(w, sheet_name=sh, index=False)
    print('已写出:', OUT)
