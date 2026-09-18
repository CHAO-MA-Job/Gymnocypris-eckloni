# -*- coding: utf-8 -*-
"""Action rate for the caudal peduncle (classes 5, 6 and 7; class 6 is the intermediate state).

Reads  : <work root>/caudal.xlsx
Writes : <work root>/caudal/stats/<sheet>_caudal_stats.xlsx

The counting rule comes from postproc.py: a swing counts when two consecutive frames share the
same state (5 or 7), with a minimum gap of 30 frames between events. No temporal smoothing is
applied.

Agreement with the manual counts of fish 21-1 over the 30 windows of 10 s between 180 and
470 s: MAE 1.00, MAPE 17.26%, AR 82.74%, r = +0.84.

The definition behaves as a proxy for the time spent in a swinging state (r = +0.866 with the
fraction of frames in state 5 or 7) rather than as a count of individual beats. Its relative
error is amplified by the small human baseline of 7.53 events per window; by absolute error it
agrees best of the three parts.

The rate is a descriptive index. Across the five temperatures the one-way ANOVA gives p = 0.25,
so it is not used to support a conclusion about temperature."""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline  # smoothed curve

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postproc as pp  # noqa: E402

PART = "caudal"
input_path = pp.src_path(PART)
output_base_dir = pp.part_out_dir(PART)   # step 2 output: <work root>/caudal/
output_plot_dir = os.path.join(output_base_dir, "caudal_figure")
output_excel_dir = os.path.join(output_base_dir, "caudal_ratestats")
os.makedirs(output_plot_dir, exist_ok=True)
os.makedirs(output_excel_dir, exist_ok=True)

xls = pd.ExcelFile(input_path)

for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name)
    if not {'frame', 'class'}.issubset(df.columns):
        raise ValueError(f"Table '{sheet_name}'must contain the 'frame' and 'class' columns.")

    # === action rate (counting logic from postproc.py) ===
    result_df, _ = pp.compute(df, PART)

    output_excel = os.path.join(output_excel_dir, f"{sheet_name}_caudal_ratestats.xlsx")
    output_plot = os.path.join(output_plot_dir, f"{sheet_name}_caudal_figure.png")
    result_df.to_excel(output_excel, index=False)

    # === plot ===
    x = result_df['start_time_s']
    y = result_df['caudal_rate']
    if len(x) >= 4:
        x_new = np.linspace(x.min(), x.max(), 300)
        y_smooth = make_interp_spline(x, y, k=3)(x_new)
    else:
        x_new, y_smooth = x, y

    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    plt.plot(x_new, y_smooth, linestyle='-', color='black')
    plt.title(f'Caudal fin oscillation frequency - {sheet_name}')
    plt.xlabel('Time (s)')
    plt.ylabel('Caudal fin oscillation frequency')
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.grid(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    plt.tight_layout()
    plt.savefig(output_plot, dpi=300)
    plt.close()

    print(f"[OK] '{sheet_name}' caudal_ratestatstable -> {output_excel}")
    print(f"[OK] '{sheet_name}' caudal_rate figure   -> {output_plot}")
