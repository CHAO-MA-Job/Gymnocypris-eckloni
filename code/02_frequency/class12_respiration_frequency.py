# -*- coding: utf-8 -*-
"""Action rate for the operculum (classes 1 and 2) - step F1 of the pipeline.

Reads  : <work root>/operculum.xlsx
Writes : <work root>/opercular/stats/<sheet>_respiration_stats.xlsx

The counting logic lives in postproc.py (smooth_K = 1, dedupe = True, ffill = False): the
per-frame state sequence is run-length compressed, and a cycle 1 -> 2 -> 1 counts once when the
intermediate state lasts at least two frames. No temporal smoothing is applied.

Human agreement on fish 21-1: MAE 1.13, MAPE 5.78%, AR 94.22%, r = +0.35.

The rate is a descriptive index rather than a conclusion: one-way ANOVA across the five
temperatures gives p = 0.015 with a non-monotonic trend, so it is reported without a
significance claim."""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline  # smoothed curve

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postproc as pp  # noqa: E402

PART = "operculum"
input_path = pp.src_path(PART)
output_base_dir = pp.part_out_dir(PART)   # step 2 output: <work root>/opercular/
output_plot_dir = os.path.join(output_base_dir, "respiration_figure")
output_excel_dir = os.path.join(output_base_dir, "respirationstats")
os.makedirs(output_plot_dir, exist_ok=True)
os.makedirs(output_excel_dir, exist_ok=True)

xls = pd.ExcelFile(input_path)

for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name)
    if not {'frame', 'class'}.issubset(df.columns):
        raise ValueError(f"Table '{sheet_name}'must contain the 'frame' and 'class' columns.")

    # === action rate (counting logic from postproc.py) ===
    result_df, _ = pp.compute(df, PART)

    output_excel = os.path.join(output_excel_dir, f"{sheet_name}_respirationstats.xlsx")
    output_plot = os.path.join(output_plot_dir, f"{sheet_name}_respiration_figure.png")
    result_df.to_excel(output_excel, index=False)

    # === plot ===
    x = result_df['start_time_s']
    y = result_df['respiration']
    if len(x) >= 4:
        x_new = np.linspace(x.min(), x.max(), 300)
        y_smooth = make_interp_spline(x, y, k=3)(x_new)
    else:
        x_new, y_smooth = x, y

    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    plt.plot(x_new, y_smooth, linestyle='-', color='black')
    plt.title(f'Breathing Frequency - {sheet_name}')
    plt.xlabel('Time (s)')
    plt.ylabel('Breathing Frequency')
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.grid(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    plt.tight_layout()
    plt.savefig(output_plot, dpi=300)
    plt.close()

    print(f"[OK] '{sheet_name}' respirationstatstable -> {output_excel}")
    print(f"[OK] '{sheet_name}' respiration figure   -> {output_plot}")
