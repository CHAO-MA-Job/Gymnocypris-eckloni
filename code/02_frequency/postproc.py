# -*- coding: utf-8 -*-
"""Counting rules shared by the action-rate scripts in this directory.

One event definition per body part, applied to the per-frame state sequence:

    operculum  classes 1/2   a cycle 1 -> 2 -> 1, counted when the intermediate state lasts
                             at least two frames
    pectoral   classes 3/4   a cycle 3 -> 4 -> 3, counted when the intermediate state lasts
                             at least two frames
    caudal     classes 5/6/7 a swing, counted when two consecutive frames share the same state
                             (5 or 7), with a minimum gap of 30 frames between events

The sequence is run-length compressed before counting. Recordings run at 30 frames per second
and events are counted in 300-frame (10 s) windows. Where a frame carries several boxes only the
most confident one is kept, and undetected frames are left unfilled.

The rates are descriptive indices. Across the five temperatures the pectoral and caudal rates
show no detectable effect (one-way ANOVA, p = 0.34 and p = 0.25) and the opercular rate is
non-monotonic (p = 0.015), so none of them is used to support a conclusion about temperature.

Agreement with the manual counts of fish 21-1 over the 30 windows of 10 s between 180 and 470 s
(reference: tables/human_validation_21-1.xlsx):

    part        MAE    MAPE      AR      r
    operculum   1.13    5.78%   94.22%   +0.35
    pectoral    1.77   18.84%   81.16%   +0.78
    caudal      1.00   17.26%   82.74%   +0.84"""
import os
import re
import sys
import bisect

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # unified path entry point (environment variables redirect the data root)

# ---------------------------------------------------------------- constants
FPS = 30
INTERVAL = 10          # counted once per 10 s window

# working data root, resolved by gyo_paths (GYO_WORK redirects it)
SRC_DIR = P.QUANT

# ---------------------------------------------------------------- main caliper (dedupe=True, ffill=False)
# caliper: dedupe=True / ffill=False / smooth_K=1
# dedupe: keep only the highest-confidence box per frame; under TTA several boxes share a
# frame, and without deduplication they are read as state changes (pectoral AR drops to 43%).
# no filling: undetected frames are not forward-filled, which would invent data and add events
# (same data and coverage, 23 C caudal rate 6.36 -> 7.87, +24% pure artefact).
# only the run-length compression and thresholds of the main analysis are kept (min_dur = 2 frames, min_gap = 30 frames).
# temporal smoothing variants (smooth_K > 1, mode='entry') are kept for sensitivity analysis only.
PARTS = {
    "operculum": dict(
        file="2_operculum.xlsx", col="respiration", title="respiration",
        mode="cycle", states=(1, 2),
        dedupe=True, ffill=False, smooth_K=1, min_dur=2,
    ),
    "pectoral": dict(
        file="3_pectoral.xlsx", col="pectoral_rate", title="pectoral_rate",
        mode="cycle", states=(3, 4),
        dedupe=True, ffill=False, smooth_K=1, min_dur=2,
    ),
    "caudal": dict(
        file="4_caudal.xlsx", col="caudal_rate", title="caudal_rate",
        mode="swing", majority_states=(5, 6, 7), swing_states=(5, 7),
        dedupe=True, ffill=False, smooth_K=1, min_gap=30,
    ),
}

# expected sheet name, such as "21-1"
SHEET_RE = re.compile(r"(\d+)\D+(\d+)")


# ================================================================ signal preparation
def build_signal(df, dedupe=True, ffill=False, conf_col="confidence"):
    """Per-frame table to arrays of frame indices and classes.

    dedupe=True : keep only the most confident box per frame (test-time augmentation gives several);
    ffill=True  : fill undetected frames from the previous state to obtain a dense sequence.
                  Default False: filling would invent data, since a detection gap becomes one state,
                  which adds swing events.
                  
                  
    dedupe=False: keep the raw per-row sequence.
    """
    d = df.sort_values("frame").reset_index(drop=True)
    if dedupe:
        if conf_col in d.columns:
            d = d.sort_values(conf_col).groupby("frame", as_index=False).last()
            d = d.sort_values("frame").reset_index(drop=True)
        if not ffill:
            return d["frame"].to_numpy(int), d["class"].to_numpy(int)
        f = d["frame"].to_numpy(int)
        grid = np.arange(f.min(), f.max() + 1)
        c = d.set_index("frame")["class"].reindex(grid).ffill().bfill()
        return grid.astype(int), c.to_numpy(int)
    return (d["frame"].to_numpy(int), d["class"].to_numpy(int))


def majority(classes, states, K):
    """Sliding-window majority vote over the class sequence (odd K); frame indices are unchanged."""
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
    """Compress into runs of equal class: (class, first frame, length)."""
    runs, rf, rd = [], [], []
    prev, cnt, sf = None, 0, None
    for f, c in zip(frames, classes):
        if c == prev:
            cnt += 1
        else:
            if prev is not None:
                runs.append(prev); rf.append(sf); rd.append(cnt)
            prev, cnt, sf = c, 1, f
    if prev is not None:
        runs.append(prev); rf.append(sf); rd.append(cnt)
    return runs, rf, rd


# ================================================================ event detection
def events_cycle(frames, classes, a, b, min_dur):
    """Cycle counter: a -> b -> a (or b -> a -> b), counted when the intermediate run lasts at least min_dur frames. Returns the anchor frames."""
    runs, rf, rd = compress(frames, classes)
    ev = []
    if not runs:
        return ev
    start = runs[0]
    i = 0
    while i < len(runs) - 2:
        if (start == a and runs[i] == a and runs[i + 1] == b
                and rd[i + 1] >= min_dur and runs[i + 2] == a):
            ev.append(rf[i]); i += 2
        elif (start == b and runs[i] == b and runs[i + 1] == a
              and rd[i + 1] >= min_dur and runs[i + 2] == b):
            ev.append(rf[i]); i += 2
        else:
            i += 1
    return sorted(ev)


def events_entry(frames, classes, a, b, refractory):
    """Entry events: frames where the state changes from a to b, counted when at least refractory frames have passed since the previous event."""
    ev, last = [], -10 ** 9
    for i in range(1, len(classes)):
        if classes[i - 1] == a and classes[i] == b:
            f = int(frames[i])
            if f - last >= refractory:
                ev.append(f); last = f
    return ev


def events_swing(frames, classes, states, min_gap):
    """Same-state swing: two consecutive frames in one of the given states (the intermediate state does not count), with at least min_gap frames between events."""
    ev, last = [], -min_gap
    for i in range(len(classes) - 1):
        if classes[i] in states and classes[i + 1] == classes[i]:
            f = int(frames[i])
            if f - last >= min_gap:
                ev.append(f); last = f
    return ev


def detect_events(df, part, cfg=None):
    """Event anchor frames of one body part, from the per-frame table."""
    cfg = cfg or PARTS[part]
    frames, classes = build_signal(df, cfg.get("dedupe", True), cfg.get("ffill", False))
    maj_states = cfg.get("majority_states") or cfg.get("states")
    classes = majority(classes, maj_states, cfg.get("smooth_K", 1))
    mode = cfg["mode"]
    if mode == "cycle":
        a, b = cfg["states"]
        return events_cycle(frames, classes, a, b, cfg.get("min_dur", 2))
    if mode == "entry":
        a, b = cfg["states"]
        return events_entry(frames, classes, a, b, cfg.get("refractory", 20))
    if mode == "swing":
        return events_swing(frames, classes, cfg["swing_states"], cfg.get("min_gap", 30))
    raise ValueError(f"unknown mode: {mode}")


# ================================================================ per-10 s counting
def count_windows(events, max_frame, fps=FPS, interval=INTERVAL):
    """Returns [(window index, start time in seconds, count), ...] covering every frame."""
    events = sorted(events)
    rows = []
    for t in range(0, int(max_frame) // fps + 1, interval):
        c = (bisect.bisect_right(events, (t + interval) * fps - 1)
             - bisect.bisect_left(events, t * fps))
        rows.append((t // interval, t, int(c)))
    return rows


def compute(df, part, cfg=None):
    """Per-frame table to a rate table (columns: window index, start time in seconds, count)."""
    cfg = cfg or PARTS[part]
    frames, classes = build_signal(df, cfg.get("dedupe", True), cfg.get("ffill", False))
    ev = detect_events(df, part, cfg)
    rows = count_windows(ev, int(frames[-1]) if len(frames) else 0)
    return pd.DataFrame(rows, columns=["window_index", "start_time_s", cfg["col"]]), ev


# ================================================================ I/O helpers
# body part -> output subdirectory (rate products live under the work root)
PART_CN = {"operculum": "respiration", "pectoral": "pectoral_rate", "caudal": "caudal_rate"}


def part_out_dir(part):
    """Output directory of one body part, under the work root, with a stats subdirectory."""
    return os.path.join(SRC_DIR, PART_CN[part])


def src_path(part):
    return os.path.join(SRC_DIR, PARTS[part]["file"])


def iter_sheets(part):
    """(sheet name, DataFrame) -- only sheets named like  '21--1'  are returned."""
    xl = pd.ExcelFile(src_path(part))
    for sh in xl.sheet_names:
        if SHEET_RE.search(str(sh)):
            yield sh, xl.parse(sh)


def fish_of(sheet):
    m = SHEET_RE.search(str(sheet))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)
