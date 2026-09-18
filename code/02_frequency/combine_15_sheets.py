# -*- coding: utf-8 -*-
"""Merge the per-fish action-rate tables of one body part into a single 15-sheet workbook.

Input : <work root>/<region>/stats/*_stats.xlsx   (15 files, 16-1 to 25-3)
Output: <work root>/respiration.xlsx, pectoral.xlsx, caudal.xlsx
        (15 sheets each, sheet name such as 21-1)

Rules: the sheet name is the file name without the trailing "_stats" suffix; sheets are ordered
by temperature and then by replicate; the per-fish columns (window index, start time in seconds,
event count) are carried over unchanged. The per-fish tables are read-only and the merged
workbooks are new files."""
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # unified path entry point (environment variables redirect the data root)

# step 2 output: per-fish statistics and merged tables share the work root
RES = P.QUANT

# regions to merge (= subdirectory name = output file name)
PARTS = ['respiration', 'pectoral_rate', 'caudal_rate']


def parse_sheet(fname):
    stem = re.sub(r'\.xlsx$', '', fname, flags=re.I)
    stem = re.sub(r'_[^_]*stats$', '', stem)   # drop the trailing "_stats" suffix
    return stem.strip()


def skey(name):
    m = re.search(r'(\d+)\D+(\d+)', str(name))
    return (int(m.group(1)), int(m.group(2))) if m else (9999, 9999)


def main():
    for part in PARTS:
        base = os.path.join(RES, part)
        if not os.path.isdir(base):
            print(f'  [skip] {part}: directory not found: {base}')
            continue
        files = []
        for root, _, fs in os.walk(base):
            for f in fs:
                if f.lower().endswith('.xlsx') and 'stats' in f:
                    files.append(os.path.join(root, f))
        if not files:
            print(f'  [skip] {part}: no per-fish stats file under {base}')
            continue

        sheets = {}
        for fp in files:
            sh = parse_sheet(os.path.basename(fp))
            if not sh:
                print('    skip(cannot parse sheet name):', fp)
                continue
            sheets[sh] = pd.read_excel(fp)

        order = sorted(sheets.keys(), key=skey)
        out = os.path.join(RES, f'{part}.xlsx')
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            for sh in order:
                sheets[sh].to_excel(w, sheet_name=sh, index=False)
        print(f'  [OK] {out}  sheets={len(order)}: {order}')


if __name__ == '__main__':
    main()
