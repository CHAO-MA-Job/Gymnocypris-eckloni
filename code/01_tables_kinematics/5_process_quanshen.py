"""Kinematics on the whole-body table: per-frame velocity and displacement.

Formulas (the legacy version wrote Excel formulas; here the values are computed directly):
    dt      = (frame_i - frame_{i-1}) / FPS                 inter-frame interval (s)
    d_px    = sqrt((d centroid X)^2 + (d centroid Y)^2)      pixel displacement
    v_px    = d_px / dt                                      pixel speed
    v_cm    = v_px * SCALE                                   cm/s
    s_step  = d_px * SCALE                                   cm per frame
    s_total = cumsum(s_step)                                 cm, cumulative
    10 s block (300 frames at 30 fps): block time = last frame of the block / 30;
                                       block speed = mean v_cm within the block
Constants: FPS = 30, SCALE = 0.03125 cm/px.

The whole-body table has exactly one row per frame, so each row is one point on the track; the
first row has no predecessor, so its dt, speed and displacement are NaN.

Input : <work root>/whole_body.xlsx
Output: <work root>/5_formula_whole_body.xlsx"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # unified path entry point (environment variables redirect the data root)

SRC = Path(P.q('1_whole_body.xlsx'))
OUT = Path(P.q('5_5_formula_whole_body.xlsx'))

FPS = 30
SCALE = 0.03125     # cm per pixel
BLOCK = 300         # 300 frames = 10 s at 30 fps

def process_sheet(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values('frame', kind='stable').reset_index(drop=True)
    cx = df['centroid_x'].to_numpy(float)
    cy = df['centroid_y'].to_numpy(float)
    frame = df['frame'].to_numpy(int)
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
    v_px[mask] = dist[mask] / dt[mask]      # keep NaN where dt == 0 (two fish in one frame), as the original spreadsheet did
    v_cm = v_px * SCALE
    s_single = dist * SCALE
    s_total = np.nan_to_num(s_single, nan=0.0).cumsum()

    coord = [f"({cx[i]:.2f}, {cy[i]:.2f})" for i in range(n)]

    # 10 s block aggregation (aligned with the recording start: block b covers frames 1+300b to 300+300b)
    time10 = np.full(n, np.nan)
    v10 = np.full(n, np.nan)
    s10 = np.full(n, np.nan)
    for b0 in range(0, n, BLOCK):
        e0 = min(b0 + BLOCK, n)
        time10[b0:e0] = frame[e0 - 1] / FPS          # time at the end of the block (s)
        v10[b0:e0] = np.nanmean(v_cm[b0:e0])          # mean speed within the block
        s10[b0:e0] = s_total[e0 - 1]                  # cumulative displacement at the end of the block

    out = df.copy()
    out['position'] = coord
    out['cm_per_px'] = SCALE
    out['dt_s'] = dt.round(6)
    out['v/px'] = np.round(v_px, 4)
    out['v/cm'] = np.round(v_cm, 4)
    out['S/step_displacement'] = np.round(s_single, 4)
    out['S/displacement'] = np.round(s_total, 4)
    out['time/10s'] = np.round(time10, 3)
    out['v/10s'] = np.round(v10, 4)
    out['time/10s'] = np.round(time10, 3)
    out['v/10s'] = np.round(v10, 4)
    out['S/10s'] = np.round(s10, 4)
    return out

def main():
    assert SRC.exists(), f'source table not found: {SRC}'
    sheets = pd.read_excel(SRC, sheet_name=None)
    with pd.ExcelWriter(OUT, engine='openpyxl') as writer:
        for name, df in sheets.items():
            out = process_sheet(df)
            out.to_excel(writer, sheet_name=name, index=False)
            print(f'  [{name}] rows={len(out)}  mean v/cm={out["v/cm"].mean():.4f}  final S/displacement={out["S/displacement"].iloc[-1]:.2f}cm')
    print(f'written: {OUT}')

if __name__ == '__main__':
    main()
