"""7_center_trajectory_1hz.py
基于 5_公式计算后_全身.xlsx, 生成「7_中心点轨迹_全身.xlsx」用于绘制轨迹图:
 - 沿用 15 个同名 sheet
 - 每秒(时间S)取一个中心点: 该秒内 中心点X/Y 的均值, 作为该秒代表点
 - 只保留中心点坐标相关列: 时间S, 中心点X, 中心点Y, 坐标(格式化)
输出: 04_Outputs/02_模型量化数据_GH1/7_中心点轨迹_全身.xlsx
"""
import os
import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源）

SRC = Path(P.q('5_公式计算后_全身.xlsx'))
OUT = Path(P.q('7_中心点轨迹_全身.xlsx'))

xls = pd.ExcelFile(SRC)
sheets = xls.sheet_names

rows_cols = ['时间S', '中心点X', '中心点Y', '坐标']
out = {}
for sh in sheets:
    df = pd.read_excel(SRC, sheet_name=sh)
    if df.empty:
        out[sh] = pd.DataFrame(columns=rows_cols)
        continue
    g = df.groupby('时间S')
    cx = g['中心点X'].mean()
    cy = g['中心点Y'].mean()
    traj = pd.DataFrame({'时间S': cx.index, '中心点X': cx.values, '中心点Y': cy.values})
    traj['坐标'] = traj.apply(lambda r: f"({r['中心点X']:.2f}, {r['中心点Y']:.2f})", axis=1)
    traj = traj[rows_cols].reset_index(drop=True)
    out[sh] = traj
    print(f'[{sh}] 共 {len(traj)} 秒中心点 (原表 {len(df)} 行)')

with pd.ExcelWriter(OUT, engine='openpyxl') as w:
    for sh, d in out.items():
        d.to_excel(w, sheet_name=sh, index=False)
print('\n已写出:', OUT)
