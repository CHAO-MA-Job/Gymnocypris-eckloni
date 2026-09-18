"""Split the assembled workbook into the four region tables by class.

Class mapping (the regions are mutually exclusive):
    whole body -> {0}
    operculum  -> {1, 2}
    pectoral   -> {3, 4}
    caudal     -> {5, 6, 7}

Input : <work root>/0_Origin_data_s.xlsx
Output: <work root>/{whole_body,operculum,pectoral,caudal}.xlsx
The source table is not overwritten, and all 11 columns including time in seconds are kept."""
import os
import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # unified path entry point (environment variables redirect the data root)

SRC = Path(P.q('0_Origin_data_s.xlsx'))
OUT_DIR = Path(P.QUANT)

CAT_MAP = {
    'whole_body': [0],
    'operculum': [1, 2],
    'pectoral': [3, 4],
    'caudal': [5, 6, 7],
}

def main():
    assert SRC.exists(), f'source table not found: {SRC}'
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f'reading the source table: {SRC}')
    sheets = pd.read_excel(SRC, sheet_name=None)
    print(f'  sheets={len(sheets)}: {list(sheets.keys())}')

    summary = {name: 0 for name in CAT_MAP}
    for name, cats in CAT_MAP.items():
        out_name = {'whole_body': '1_whole_body', 'operculum': '2_operculum', 'pectoral': '3_pectoral', 'caudal': '4_caudal'}[name]
        out_path = OUT_DIR / f'{out_name}.xlsx'
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            for sname, df in sheets.items():
                sub = df[df['class'].isin(cats)].copy()
                sub.to_excel(writer, sheet_name=sname, index=False)
                summary[name] += len(sub)
        print(f'  written {out_name}.xlsx -> rows {summary[name]}')

    print('\nsplit complete; rows per table:')
    for k, v in summary.items():
        print(f'  {k}: {v}')
    total = sum(summary.values())
    print(f'  total: {total} (expected: {sum(len(d) for d in sheets.values())})')
    print(f'output directory: {OUT_DIR}')

if __name__ == '__main__':
    main()
