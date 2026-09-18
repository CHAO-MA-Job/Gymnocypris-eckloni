# -*- coding: utf-8 -*-
"""Action rate for the pectoral fins (classes 3 and 4), step F1 of the pipeline.

Reads  : <work root>/pectoral.xlsx
Writes : <work root>/pectoral/stats/<sheet>_pectoral_stats.xlsx

The counting rule comes from postproc.py: the per-frame state sequence is run-length
compressed, and a cycle 3 -> 4 -> 3 counts once when the intermediate state lasts at least two
frames. No temporal smoothing is applied.

Agreement with the manual counts of fish 21-1 over the 30 windows of 10 s between 180 and
470 s: MAE 1.77, MAPE 18.84%, AR 81.16%, r = +0.78. This is the weakest of the three body parts,
in counting agreement as well as in class separability: the diagonal recall of the pectoral
states is 0.78 and 0.83, the lowest of the eight classes.

The rate is a descriptive index. Across the five temperatures the one-way ANOVA gives p = 0.34,
so it is not used to support a conclusion about temperature."""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline  # smoothed curve

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postproc as pp  # noqa: E402

PART = "pectoral"
input_path = pp.src_path(PART)
output_base_dir = pp.part_out_dir(PART)   # step 2 output: <work root>/pectoral/
output_plot_dir = os.path.join(output_base_dir, "pectoral_figure")
output_excel_dir = os.path.join(output_base_dir, "pectoral_ratestats")
os.makedirs(output_plot_dir, exist_ok=True)
os.makedirs(output_excel_dir, exist_ok=True)

xls = pd.ExcelFile(input_path)

for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name)
    if not {'frame', 'class'}.issubset(df.columns):
        raise ValueError(f"Table '{sheet_name}'must contain the 'frame' and 'class' columns.")

    # === action rate (counting logic from postproc.py) ===
    result_df, _ = pp.compute(df, PART)

    output_excel = os.path.join(output_excel_dir, f"{sheet_name}_pectoral_ratestats.xlsx")
    output_plot = os.path.join(output_plot_dir, f"{sheet_name}_pectoral_figure.png")
    result_df.to_excel(output_excel, index=False)

    # === plot ===
    x = result_df['start_time_s']
    y = result_df['pectoral_rate']
    if len(x) >= 4:
        x_new = np.linspace(x.min(), x.max(), 300)
        y_smooth = make_interp_spline(x, y, k=3)(x_new)
    else:
        x_new, y_smooth = x, y

    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    plt.plot(x_new, y_smooth, linestyle='-', color='black')
    plt.title(f'Pectoral fin oscillation frequency - {sheet_name}')
    plt.xlabel('Time (s)')
    plt.ylabel('Pectoral fin oscillation frequency')
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.grid(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    plt.tight_layout()
    plt.savefig(output_plot, dpi=300)
    plt.close()

    print(f"[OK] '{sheet_name}' pectoral_ratestatstable -> {output_excel}")
    print(f"[OK] '{sheet_name}' pectoral_rate figure   -> {output_plot}")
