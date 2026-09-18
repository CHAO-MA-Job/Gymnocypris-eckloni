"""Build the 1 Hz centroid track from the formula table.

- keeps the 15 sheets with their original names;
- for each second of recording time (the time-in-seconds column), takes the mean centroid X
  and Y inside that second as the representative point;
- keeps only the coordinate columns: time in seconds, centroid X, centroid Y and a formatted
  coordinate pair.

Input : <work root>/5_formula_whole_body.xlsx
Output: <work root>/7_centroid_trajectory.xlsx"""
import os
import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # unified path entry point (environment variables redirect the data root)

SRC = Path(P.q('5_5_formula_whole_body.xlsx'))
OUT = Path(P.q('7_7_centroid_trajectory.xlsx'))

xls = pd.ExcelFile(SRC)
sheets = xls.sheet_names

rows_cols = ['time_s', 'centroid_x', 'centroid_y', 'position']
out = {}
for sh in sheets:
    df = pd.read_excel(SRC, sheet_name=sh)
    if df.empty:
        out[sh] = pd.DataFrame(columns=rows_cols)
        continue
    g = df.groupby('time_s')
    cx = g['centroid_x'].mean()
    cy = g['centroid_y'].mean()
    traj = pd.DataFrame({'time_s': cx.index, 'centroid_x': cx.values, 'centroid_y': cy.values})
    traj['position'] = traj.apply(lambda r: f"({r['centroid_x']:.2f}, {r['centroid_y']:.2f})", axis=1)
    traj = traj[rows_cols].reset_index(drop=True)
    out[sh] = traj
    print(f'[{sh}] {len(traj)} centroids, one per second (source table: {len(df)} rows)')

with pd.ExcelWriter(OUT, engine='openpyxl') as w:
    for sh, d in out.items():
        d.to_excel(w, sheet_name=sh, index=False)
print('\nwritten:', OUT)
