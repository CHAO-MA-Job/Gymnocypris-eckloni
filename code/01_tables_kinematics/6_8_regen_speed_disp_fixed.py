"""Regenerate the speed/displacement table (and the per-fish summary table).

Column names: the output columns v/10s, v/10seg and v/cm_mean hold exactly the same values,
namely the mean of the per-frame v_cm inside the block, in cm/s. The name refers to the block
granularity (one block per 10 s), not to a division by 10 s. This is consistent within the
table: s/10s is about 10 x v/10s (first block of 16-1: 2.2403 x 10 = 22.403 cm against
22.2544 cm).

Fix 1: the five 10 s aggregate columns of the source table were copied by broadcasting a
       300-frame block whose boundary sits one frame away from the per-second boundary, so
       adjacent blocks repeated the same values. They are recomputed here from the per-frame
       data inside each block, aligned exactly with the block boundaries.
Fix 2: acceleration per 10 s block.
       - accel_mean / accel_std (cm/s^2): block mean and standard deviation of the per-frame
         instantaneous acceleration a = dv/dt;
       - accel_block_diff (cm/s^2): mean speed of consecutive blocks, differenced and divided
         by 10 s (acceleration of the overall speed trend).

Output: <work root>/8_velocity_displacement.xlsx (overwritten)"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # unified path entry point (environment variables redirect the data root)

SRC = Path(P.q('5_5_formula_whole_body.xlsx'))
# also regenerates the summary table, which had the same duplicated-block values
OUTS = [
    Path(P.q('8_8_velocity_displacement.xlsx')),
    Path(P.q('6_6_summary_whole_body.xlsx')),
]

xls = pd.ExcelFile(SRC)
sheets = xls.sheet_names

def summarize(g: pd.DataFrame) -> pd.Series:
    g = g.sort_values('frame').copy()
    first = g.iloc[0]; last = g.iloc[-1]
    b = int(g['time_s'].iloc[0] // 10)
    s = {}
    s['block'] = b + 1
    s['block_time_s'] = f'{b*10}-{(b+1)*10}'
    s['frame_start'] = int(first['frame']); s['frame_end'] = int(last['frame'])
    s['timestamp_start'] = first['timestamp']; s['class'] = int(g['class'].mode().iloc[0])
    s['position_start'] = first['position']; s['position_end'] = last['position']
    s['centroid_x_mean'] = g['centroid_x'].mean(); s['centroid_y_mean'] = g['centroid_y'].mean()
    s['centroid_x_std'] = g['centroid_x'].std(); s['centroid_y_std'] = g['centroid_y'].std()
    s['x1_mean'] = g['x1'].mean(); s['y1_mean'] = g['y1'].mean()
    s['x2_mean'] = g['x2'].mean(); s['y2_mean'] = g['y2'].mean()
    s['cm_per_px'] = first['cm_per_px']
    s['confidence_mean'] = g['confidence'].mean(); s['confidence_std'] = g['confidence'].std()
    for col in ['v/cm', 'v/px', 'S/step_displacement']:
        s[f'{col}_mean'] = g[col].mean(); s[f'{col}_std'] = g[col].std()
        s[f'{col}_min'] = g[col].min(); s[f'{col}_max'] = g[col].max()
    s['S/step_displacement_sum'] = g['S/step_displacement'].sum()
    s['S/displacement_start'] = first['S/displacement']; s['S/displacement_end'] = last['S/displacement']
    s['S/displacement_inc'] = last['S/displacement'] - first['S/displacement']
    # per-frame instantaneous acceleration within the block, a = dv/dt (cm/s^2)
    a = g['v/cm'].diff() / g['dt_s']
    s['accel_mean (cm/s²)'] = a.mean(); s['accel_std (cm/s²)'] = a.std()
    s['accel_max (cm/s²)'] = a.max(); s['accel_min (cm/s²)'] = a.min()
    # 10 s aggregate columns recomputed inside each block instead of copied from the broadcast source values
    s['time/10s'] = (b + 1) * 10
    s['time/10s'] = (b + 1) * 10
    s['v/10s'] = g['v/cm'].mean()          # mean speed within the block (cm/s)
    s['v/10s'] = g['v/cm'].mean()
    s['S/10s'] = g['S/step_displacement'].sum()     # displacement within the block (cm)
    s['dt_s'] = first['dt_s']
    return pd.Series(s)

ordered = [
    'block','block_time_s','frame_start','frame_end','timestamp_start','class',
    'position_start','position_end',
    'centroid_x_mean','centroid_y_mean','centroid_x_std','centroid_y_std',
    'x1_mean','y1_mean','x2_mean','y2_mean',
    'cm_per_px','confidence_mean','confidence_std',
    'v/cm_mean','v/cm_std','v/cm_min','v/cm_max',
    'v/px_mean','v/px_std','v/px_min','v/px_max',
    'S/step_displacement_mean','S/step_displacement_std','S/step_displacement_min','S/step_displacement_max','S/step_displacement_sum',
    'S/displacement_start','S/displacement_end','S/displacement_inc',
    'accel_mean (cm/s²)','accel_std (cm/s²)','accel_min (cm/s²)','accel_max (cm/s²)',
    'dt_s','time/10s','v/10s','time/10s','v/10s','S/10s',
]

out = {}
for sh in sheets:
    df = pd.read_excel(SRC, sheet_name=sh)
    if df.empty:
        out[sh] = pd.DataFrame(columns=ordered); continue
    summ = df.groupby(df['time_s'] // 10, group_keys=False).apply(summarize, include_groups=False).reset_index(drop=True)
    # block-to-block acceleration: (mean speed of this block - previous block) / 10 s
    summ['accel_block_diff (cm/s²)'] = summ['v/10s'].diff() / 10.0
    summ = summ[ordered + ['accel_block_diff (cm/s²)']]
    out[sh] = summ
    print(f'[{sh}] blocks={len(summ)}  first two blocks v/10s={summ["v/10s"].head(2).round(4).tolist()}  S/10s={summ["S/10s"].head(2).round(3).tolist()}')

for OUT in OUTS:
    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        for sh, d in out.items():
            d.to_excel(w, sheet_name=sh, index=False)
    print('written:', OUT)
