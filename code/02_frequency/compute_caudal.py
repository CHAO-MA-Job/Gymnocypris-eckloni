# -*- coding: utf-8 -*-
"""Consistency check for the caudal rate: recompute it and compare with the merged table.

The counting rule comes from postproc.py (same-state swing with a minimum gap of 30 frames).
The script recomputes the rate from the region table and compares it cell by cell with the
merged workbook, which confirms that both use the same definition.

Input   : <work root>/caudal.xlsx
Against : <work root>/caudal/caudal.xlsx
Reports the per-cell MAE and r; no file is written."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postproc as pp  # noqa: E402

PART = "caudal"
RES_DIR = pp.SRC_DIR     # step 2 output root: same as the merged rate tables
FREQ_COL = pp.PARTS[PART]["col"]
REF_XLSX = os.path.join(RES_DIR, "caudal_rate.xlsx")


def main():
    ref = pd.ExcelFile(REF_XLSX) if os.path.exists(REF_XLSX) else None
    diffs, xs, ys = [], [], []
    print(f"[{FREQ_COL}] recomputed versus merged table (check only, nothing written)")
    for sh, df in pp.iter_sheets(PART):
        res, _ = pp.compute(df, PART)
        a = res[FREQ_COL].to_numpy(float)
        if ref is not None and sh in ref.sheet_names:
            v = pd.to_numeric(ref.parse(sh)[FREQ_COL], errors="coerce").to_numpy(float)
            m = min(len(a), len(v))
            diffs.append(np.abs(a[:m] - v[:m]))
            xs.append(a[:m])
            ys.append(v[:m])
            r = np.corrcoef(a[:m], v[:m])[0, 1] if m > 2 else float("nan")
            print(f"  {sh:>8} recomputed mean={a.mean():7.2f} merged mean={np.nanmean(v[:m]):7.2f} "
                  f"MAE={np.mean(np.abs(a[:m] - v[:m])):4.2f} r={r:.3f}")
        else:
            print(f"  {sh:>8} recomputed mean={a.mean():7.2f}")
    if diffs:
        D = np.concatenate(diffs)
        X = np.concatenate(xs)
        Y = np.concatenate(ys)
        r_all = np.corrcoef(X, Y)[0, 1] if X.size > 2 else float("nan")
        print("[[check] sheet=%d  per-cell MAE=%.4f  r=%.6f  max abs diff=%.4g"
              % (len(diffs), float(np.nanmean(D)), float(r_all),
                 float(np.nanmax(D))))
        print("           identical cell by cell: single implementation, no caliper drift" if np.nanmax(D) == 0
              else "           differences found, needs investigation")
    else:
        print("[warning] merged table not found; cannot compare:", REF_XLSX)


if __name__ == "__main__":
    main()
