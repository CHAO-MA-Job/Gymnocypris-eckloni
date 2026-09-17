"""5_process_quanshen.py — 对 全身.xlsx 套用运动学公式, 输出处理后表格。
公式口径(沿用 2.数据表公式.py, 但改为直接计算数值, 不再写Excel公式):
  dt       = (帧_i - 帧_{i-1}) / FPS          # 帧间时间(s)
  位移_px  = sqrt((Δ中心点X)^2 + (Δ中心点Y)^2)  # 像素位移
  v/像素点  = 位移_px / dt                      # 像素速度
  v/cm     = v/像素点 * SCALE                   # cm/s
  S/单次位移 = 位移_px * SCALE                   # cm
  S/总位移  = cumsum(S/单次位移)                # cm 累计
  10s块(300帧@30fps): time/10s = 块尾帧号/30; v/10s = 块内 v/cm 均值
常量: FPS=30, SCALE=0.03125 (cm/px)
说明: 全身表每帧恰1行, 逐行即单条轨迹; 首行无前帧, dt/速度/位移为NaN。
输入 : 04_Outputs/02_模型量化数据_GH1/1_全身.xlsx
输出 : 04_Outputs/02_模型量化数据_GH1/5_公式计算后_全身.xlsx
合规 : 只读源表, 仅写新文件(不覆盖原表)。
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源）

SRC = Path(P.q('1_全身.xlsx'))
OUT = Path(P.q('5_公式计算后_全身.xlsx'))

FPS = 30
SCALE = 0.03125     # cm per pixel
BLOCK = 300         # 300 帧 = 10s @ 30fps

def process_sheet(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values('帧编号', kind='stable').reset_index(drop=True)
    cx = df['中心点X'].to_numpy(float)
    cy = df['中心点Y'].to_numpy(float)
    frame = df['帧编号'].to_numpy(int)
    n = len(df)

    dt = np.full(n, np.nan)
    dt[1:] = (frame[1:] - frame[:-1]) / FPS

    dx = np.full(n, np.nan)
    dy = np.full(n, np.nan)
    dx[1:] = cx[1:] - cx[:-1]
    dy[1:] = cy[1:] - cy[:-1]
    dist = np.sqrt(dx**2 + dy**2)

    v_px = np.full(n, np.nan)
    mask = dt > 0
    v_px[mask] = dist[mask] / dt[mask]      # dt==0(同帧多鱼)处保持NaN, 与原Excel #DIV/0! 一致
    v_cm = v_px * SCALE
    s_single = dist * SCALE
    s_total = np.nan_to_num(s_single, nan=0.0).cumsum()

    coord = [f"({cx[i]:.2f}, {cy[i]:.2f})" for i in range(n)]

    # 10s 块聚合 (对齐视频起点: 块b = 帧 [1+300b, 300+300b])
    time10 = np.full(n, np.nan)
    v10 = np.full(n, np.nan)
    s10 = np.full(n, np.nan)
    for b0 in range(0, n, BLOCK):
        e0 = min(b0 + BLOCK, n)
        time10[b0:e0] = frame[e0 - 1] / FPS          # 块尾时间(s)
        v10[b0:e0] = np.nanmean(v_cm[b0:e0])          # 块内平均速度
        s10[b0:e0] = s_total[e0 - 1]                  # 块末累计位移(=S/10s)

    out = df.copy()
    out['坐标'] = coord
    out['换算比例'] = SCALE
    out['帧间dt(s)'] = dt.round(6)
    out['v/像素点'] = np.round(v_px, 4)
    out['v/cm'] = np.round(v_cm, 4)
    out['S/单次位移'] = np.round(s_single, 4)
    out['S/总位移'] = np.round(s_total, 4)
    out['time/10s'] = np.round(time10, 3)
    out['v/10s'] = np.round(v10, 4)
    out['time/10秒'] = np.round(time10, 3)
    out['v/10秒'] = np.round(v10, 4)
    out['S/10s'] = np.round(s10, 4)
    return out

def main():
    assert SRC.exists(), f'源表不存在: {SRC}'
    sheets = pd.read_excel(SRC, sheet_name=None)
    with pd.ExcelWriter(OUT, engine='openpyxl') as writer:
        for name, df in sheets.items():
            out = process_sheet(df)
            out.to_excel(writer, sheet_name=name, index=False)
            print(f'  [{name}] 行数={len(out)}  v/cm均值={out["v/cm"].mean():.4f}  末态S/总位移={out["S/总位移"].iloc[-1]:.2f}cm')
    print(f'已写出: {OUT}')

if __name__ == '__main__':
    main()
