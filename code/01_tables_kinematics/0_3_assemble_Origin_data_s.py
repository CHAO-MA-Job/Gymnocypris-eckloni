# -*- coding: utf-8 -*-
"""Step B: assemble the per-recording detector output into a single workbook.

Reads  : <work root>/MP4/<recording>/bbox_data.xlsx  (15 recordings, 16-1 to 25-3)
Writes : <work root>/0_Origin_data_s.xlsx            (15 sheets, sheet name such as 21-1)

Columns: frame index, timestamp, time in seconds, class, confidence, x1, y1, x2, y2,
         centroid X, centroid Y.

The quantification step writes the time-in-seconds column as an Excel formula, which reads
back as NaN; this step recomputes the seconds from the timestamp so that downstream scripts
can use plain numbers. Only the new file is written; the per-recording tables are read-only.

Optional arguments: python 0_3_assemble_Origin_data_s.py [MP4 root] [output xlsx]"""
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # unified path entry point (environment variables redirect the data root)

GH1 = P.QUANT
# optional arguments: python 0_3_assemble_Origin_data_s.py [MP4 root] [output xlsx]
MP4 = sys.argv[1] if len(sys.argv) > 1 else P.MP4
OUT = sys.argv[2] if len(sys.argv) > 2 else P.q('0_Origin_data_s.xlsx')
# keep only the highest-confidence whole-fish box per frame; set 0 to disable
DEDUP_CLS0 = os.environ.get('GYO_DEDUP_CLS0', '1') == '1'
COLS = ['frame', 'timestamp', 'time_s', 'class', 'confidence', 'x1', 'y1', 'x2', 'y2', 'centroid_x', 'centroid_y']


def parse_ts(t):
    """Timestamp to integer seconds:
    taken from Timedelta.total_seconds() when available, otherwise 'H:MM:SS' / 'MM:SS' / 'SS' text is parsed. Returns None on failure."""
    if t is None or (isinstance(t, float) and pd.isna(t)):
        return None
    if hasattr(t, 'total_seconds'):
        try:
            return int(t.total_seconds())
        except Exception:
            return None
    s = str(t).strip().split('.')[0]
    if not s:
        return None
    try:
        parts = [int(float(p)) for p in s.split(':')]
    except Exception:
        return None
    if len(parts) == 3:
        h, m, sec = parts
    elif len(parts) == 2:
        h, m, sec = 0, parts[0], parts[1]
    elif len(parts) == 1:
        h = m = 0
        sec = parts[0]
    else:
        return None
    return h * 3600 + m * 60 + sec


def sort_key(vid):
    m = re.match(r'(\d+)\D+(\d+)', vid)
    return (int(m.group(1)), int(m.group(2))) if m else (9999, 9999)


def find_data_xlsx(vdir):
    """Data table of one recording, from its directory: state_counts.xlsx is skipped, 
    bbox_data.xlsx is preferred, otherwise the largest .xlsx in the directory."""
    cands = [f for f in os.listdir(vdir)
             if f.lower().endswith('.xlsx') and 'state_counts' not in f.lower()]
    if not cands:
        return None
    pref = [f for f in cands if 'bbox_data' in f.lower()]
    pick = pref[0] if pref else max(cands, key=lambda f: os.path.getsize(os.path.join(vdir, f)))
    return os.path.join(vdir, pick)


def load_merged(path):
    """Read and normalise an already merged 15-sheet workbook: 
    sheet name -> {temp}--{rep} (accepts '16-1' / '16--1'); timestamp recomputed from time_s."""
    xl = pd.ExcelFile(path)
    sheets = {}
    for sh in xl.sheet_names:
        m = re.match(r'(\d+)\D+(\d+)', str(sh))
        if not m:
            print(f'  skip (cannot parse sheet name): {sh}')
            continue
        name = f'{int(m.group(1))}--{int(m.group(2))}'
        df = xl.parse(sh)
        if 'timestamp' in df.columns:
            df['time_s'] = df['timestamp'].map(parse_ts)
        cols = [c for c in COLS if c in df.columns]
        sheets[name] = df[cols]
        print(f'  {sh} -> sheet {name}: rows={len(df)}')
    return sheets


def dedupe_cls0(df):
    """Where one frame carries several whole-fish boxes, only the most confident one is kept.

    The whole-body table holds exactly one row per frame: a duplicate gives
    dt = 0, which turns v/cm into NaN and adds that displacement twice.
    Classes 1 to 7 keep their multiple boxes, which does not affect the rate tables.
    Returns the new table and the number of duplicated frames.
    """
    if 'class' not in df.columns or 'frame' not in df.columns:
        return df, 0
    is0 = df['class'] == 0
    if not is0.any():
        return df, 0
    sub = df[is0]
    dup = int((sub['frame'].value_counts() > 1).sum())
    if dup == 0:
        return df, 0
    keep = sub.sort_values('confidence', ascending=False).groupby('frame').head(1)
    out = pd.concat([df[~is0], keep]).sort_values(['frame', 'class']).reset_index(drop=True)
    return out, dup


def main():
    if os.path.isfile(MP4) and MP4.lower().endswith('.xlsx'):
        print(f'merged workbook given; normalising it to the 15-sheet layout: {MP4}')
        sheets = load_merged(MP4)
        if DEDUP_CLS0:
            for name in list(sheets):
                sheets[name], n = dedupe_cls0(sheets[name])
                if n:
                    print(f'  [dedupe] {name}: class 0: {n} duplicated frames merged')
    else:
        if not os.path.isdir(MP4):
            raise FileNotFoundError(f'quantification directory not found: {MP4}')
        vids = [d for d in os.listdir(MP4) if os.path.isdir(os.path.join(MP4, d))]
        vids.sort(key=sort_key)
        sheets = {}
        for vid in vids:
            f = find_data_xlsx(os.path.join(MP4, vid))
            if f is None:
                print(f'  skip (no data table in the directory): {vid}')
                continue
            m = re.match(r'(\d+)\D+(\d+)', vid)
            if not m:
                print(f'  skip (cannot parse temperature and replicate): {vid}')
                continue
            sheet = f'{int(m.group(1))}--{int(m.group(2))}'
            df = pd.read_excel(f, sheet_name=0)
            if 'timestamp' in df.columns:
                df['time_s'] = df['timestamp'].map(parse_ts)
            if DEDUP_CLS0:
                df, n = dedupe_cls0(df)
                if n:
                    print(f'  [dedupe] {sheet}: class 0: {n} duplicated frames merged')
            cols = [c for c in COLS if c in df.columns]
            sheets[sheet] = df[cols]
            print(f'  {vid} -> sheet {sheet}: rows={len(df)}')

    if not sheets:
        print('[skip] no per-recording table collected (check that {vid}/bbox_data.xlsx exists); nothing written.')
        return

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        for sh, df in sheets.items():
            df.to_excel(w, sheet_name=sh, index=False)
    print(f'[OK] {OUT}  sheets={len(sheets)}: {list(sheets.keys())}')


if __name__ == '__main__':
    main()
