"""Postprocess regional detections and count events in 10-second windows."""
import os
import re
import sys
import bisect
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P
FPS = 30
INTERVAL = 10
SRC_DIR = P.QUANT
PARTS = {'operculum': dict(file='2_鳃盖.xlsx', col='呼吸频率', title='呼吸频率', mode='cycle', states=(1, 2), dedupe=True, ffill=False, smooth_K=1, min_dur=2), 'pectoral': dict(file='3_胸鳍.xlsx', col='胸鳍摆动频率', title='胸鳍摆动频率', mode='cycle', states=(3, 4), dedupe=True, ffill=False, smooth_K=1, min_dur=2), 'caudal': dict(file='4_尾鳍.xlsx', col='尾鳍摆动频率', title='尾鳍摆动频率', mode='swing', majority_states=(5, 6, 7), swing_states=(5, 7), dedupe=True, ffill=False, smooth_K=1, min_gap=30)}
SHEET_RE = re.compile('(\\d+)\\s*℃\\s*-?\\s*(\\d+)')

def build_signal(df, dedupe=True, ffill=False, conf_col='置信度'):
    d = df.sort_values('帧编号').reset_index(drop=True)
    if dedupe:
        if conf_col in d.columns:
            d = d.sort_values(conf_col).groupby('帧编号', as_index=False).last()
            d = d.sort_values('帧编号').reset_index(drop=True)
        if not ffill:
            return (d['帧编号'].to_numpy(int), d['类别'].to_numpy(int))
        f = d['帧编号'].to_numpy(int)
        grid = np.arange(f.min(), f.max() + 1)
        c = d.set_index('帧编号')['类别'].reindex(grid).ffill().bfill()
        return (grid.astype(int), c.to_numpy(int))
    return (d['帧编号'].to_numpy(int), d['类别'].to_numpy(int))

def majority(classes, states, K):
    if not K or K <= 1:
        return np.asarray(classes, int)
    sig = np.asarray(classes, int)
    h = K // 2
    n = len(sig)
    lo = np.maximum(0, np.arange(n) - h)
    hi = np.minimum(n, np.arange(n) + h + 1)
    counts = []
    for s in states:
        cs = np.concatenate([[0], np.cumsum((sig == s).astype(float))])
        counts.append(cs[hi] - cs[lo])
    return np.asarray(states, int)[np.argmax(np.stack(counts), axis=0)].astype(int)

def compress(frames, classes):
    runs, rf, rd = ([], [], [])
    prev, cnt, sf = (None, 0, None)
    for f, c in zip(frames, classes):
        if c == prev:
            cnt += 1
        else:
            if prev is not None:
                runs.append(prev)
                rf.append(sf)
                rd.append(cnt)
            prev, cnt, sf = (c, 1, f)
    if prev is not None:
        runs.append(prev)
        rf.append(sf)
        rd.append(cnt)
    return (runs, rf, rd)

def events_cycle(frames, classes, a, b, min_dur):
    runs, rf, rd = compress(frames, classes)
    ev = []
    if not runs:
        return ev
    start = runs[0]
    i = 0
    while i < len(runs) - 2:
        if start == a and runs[i] == a and (runs[i + 1] == b) and (rd[i + 1] >= min_dur) and (runs[i + 2] == a):
            ev.append(rf[i])
            i += 2
        elif start == b and runs[i] == b and (runs[i + 1] == a) and (rd[i + 1] >= min_dur) and (runs[i + 2] == b):
            ev.append(rf[i])
            i += 2
        else:
            i += 1
    return sorted(ev)

def events_entry(frames, classes, a, b, refractory):
    ev, last = ([], -10 ** 9)
    for i in range(1, len(classes)):
        if classes[i - 1] == a and classes[i] == b:
            f = int(frames[i])
            if f - last >= refractory:
                ev.append(f)
                last = f
    return ev

def events_swing(frames, classes, states, min_gap):
    ev, last = ([], -min_gap)
    for i in range(len(classes) - 1):
        if classes[i] in states and classes[i + 1] == classes[i]:
            f = int(frames[i])
            if f - last >= min_gap:
                ev.append(f)
                last = f
    return ev

def detect_events(df, part, cfg=None):
    cfg = cfg or PARTS[part]
    frames, classes = build_signal(df, cfg.get('dedupe', True), cfg.get('ffill', False))
    maj_states = cfg.get('majority_states') or cfg.get('states')
    classes = majority(classes, maj_states, cfg.get('smooth_K', 1))
    mode = cfg['mode']
    if mode == 'cycle':
        a, b = cfg['states']
        return events_cycle(frames, classes, a, b, cfg.get('min_dur', 2))
    if mode == 'entry':
        a, b = cfg['states']
        return events_entry(frames, classes, a, b, cfg.get('refractory', 20))
    if mode == 'swing':
        return events_swing(frames, classes, cfg['swing_states'], cfg.get('min_gap', 30))
    raise ValueError(f'未知 mode: {mode}')

def count_windows(events, max_frame, fps=FPS, interval=INTERVAL):
    events = sorted(events)
    rows = []
    for t in range(0, int(max_frame) // fps + 1, interval):
        c = bisect.bisect_right(events, (t + interval) * fps - 1) - bisect.bisect_left(events, t * fps)
        rows.append((t // interval, t, int(c)))
    return rows

def compute(df, part, cfg=None):
    cfg = cfg or PARTS[part]
    frames, classes = build_signal(df, cfg.get('dedupe', True), cfg.get('ffill', False))
    ev = detect_events(df, part, cfg)
    rows = count_windows(ev, int(frames[-1]) if len(frames) else 0)
    return (pd.DataFrame(rows, columns=['时间段编号', '开始时间（秒）', cfg['col']]), ev)
PART_CN = {'operculum': '呼吸频率', 'pectoral': '胸鳍摆动频率', 'caudal': '尾鳍摆动频率'}

def part_out_dir(part):
    return os.path.join(SRC_DIR, PART_CN[part])

def src_path(part):
    return os.path.join(SRC_DIR, PARTS[part]['file'])

def iter_sheets(part):
    xl = pd.ExcelFile(src_path(part))
    for sh in xl.sheet_names:
        if SHEET_RE.search(str(sh)):
            yield (sh, xl.parse(sh))

def fish_of(sheet):
    m = SHEET_RE.search(str(sheet))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)
