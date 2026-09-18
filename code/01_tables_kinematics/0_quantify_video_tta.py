# -*- coding: utf-8 -*-
"""Detector output per recording, with test-time augmentation at an input size of 640.

Walks the recordings, runs the detector frame by frame and writes one row per box to a
per-recording workbook. The input size and the augmentation follow the training configuration.
Where a frame carries several whole-fish boxes, only the most confident one is kept, so the
inter-frame time step of the downstream table cannot collapse to zero; classes 1 to 8 keep
their multiple boxes.

Input : the raw recordings, one file or a directory (GYO_VIDEO_SRC)
Output: <work root>/MP4/<recording>/bbox_data.xlsx and state_counts.xlsx

Usage : python 0_quantify_video_tta.py            # every recording
        python 0_quantify_video_tta.py 23-1 23-2  # selected recordings"""
import gc
import os
import sys
import time
from collections import defaultdict
from datetime import timedelta

import cv2
import pandas as pd
import torch
from ultralytics import YOLO

# ---------------- settings ----------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # unified path entry point (environment variables redirect data and model)

MODEL = P.WEIGHTS                                              # set GYO_WEIGHTS to use another model
SRC = P.VIDEO_SRC                                              # directory of the raw recordings
OUT_ROOT = os.environ.get('GYO_TTA_OUT') or P.MP4              # written back to the step 1 output root by default

IMGSZ = 640          # fix: 960 -> 640 (targets were too large and fell outside the training scale)
AUGMENT = True       # fix: test-time augmentation, recovery of missing frames 2.5% -> 75-95%
CONF = 0.25          # matching the library default
DEDUP_CLS0 = True    # fix: keep only the highest-confidence whole-fish box per frame (removes duplicate frame indices)
EMPTY_CACHE_EVERY = 300

TARGETS = sys.argv[1:]   # empty = all recordings


def process(video_path):
    name = os.path.splitext(os.path.basename(video_path))[0]
    out_dir = os.path.join(OUT_ROOT, name)
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError('cannot open the recording: %s' % video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    model = YOLO(MODEL)
    status_counts = defaultdict(int)
    rows = []
    n_det_frame = 0          # frames containing a whole-fish box
    n_read = 0
    t0 = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        n_read += 1
        ts = str(timedelta(seconds=n_read / fps)).split('.')[0]

        boxes = model(frame, imgsz=IMGSZ, conf=CONF, augment=AUGMENT, verbose=False)[0].boxes
        cls = boxes.cls.cpu().numpy().astype(int) if len(boxes) else []
        cf = boxes.conf.cpu().numpy() if len(boxes) else []
        xy = boxes.xyxy.cpu().numpy() if len(boxes) else []

        # ---- deduplication: keep the highest-confidence whole-fish box per frame ----
        keep = list(range(len(cls)))
        if DEDUP_CLS0 and len(cls):
            c0 = [i for i in keep if cls[i] == 0]
            if len(c0) > 1:
                best = max(c0, key=lambda i: cf[i])
                keep = [i for i in keep if cls[i] != 0 or i == best]

        got0 = False
        for i in keep:
            c = int(cls[i])
            status_counts[c] += 1
            x1, y1, x2, y2 = [float(v) for v in xy[i]]
            if c == 0:
                got0 = True
            rows.append({
                'frame': n_read, 'timestamp': ts, 'time_s': int(n_read / fps),
                'class': c, 'confidence': float(cf[i]),
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'centroid_x': (x1 + x2) / 2, 'centroid_y': (y1 + y2) / 2,
            })
        n_det_frame += int(got0)

        if n_read % EMPTY_CACHE_EVERY == 0:
            torch.cuda.empty_cache()
            gc.collect()
            el = time.time() - t0
            print('  %s  %6d/%d frames  coverage=%.1f%%  %.1f fps  elapsed %.1f min'
                  % (name, n_read, total, n_det_frame / n_read * 100,
                     n_read / el, el / 60), flush=True)

    cap.release()

    pd.DataFrame({'state_id': list(range(1, 9)),
                  'count': [status_counts.get(i, 0) for i in range(1, 9)]}
                 ).to_excel(os.path.join(out_dir, 'state_counts.xlsx'), index=False)
    pd.DataFrame(rows).to_excel(os.path.join(out_dir, 'bbox_data.xlsx'), index=False)

    print('[OK] %s  read=%d frames  with whole-fish box=%d frames  coverage=%.1f%%  rows=%d  elapsed=%.1f min'
          % (name, n_read, n_det_frame, n_det_frame / max(n_read, 1) * 100,
             len(rows), (time.time() - t0) / 60), flush=True)
    return n_read, n_det_frame


def main():
    if not os.path.exists(MODEL):
        raise FileNotFoundError('model not found: %s' % MODEL)
    vids = sorted(f for f in os.listdir(SRC) if f.lower().endswith('.mp4'))
    if TARGETS:
        vids = [f for f in vids if os.path.splitext(f)[0] in TARGETS]
    print('IMGSZ=%d AUGMENT=%s CONF=%.2f DEDUP_CLS0=%s | %d recordings -> %s'
          % (IMGSZ, AUGMENT, CONF, DEDUP_CLS0, len(vids), OUT_ROOT), flush=True)
    for f in vids:
        process(os.path.join(SRC, f))


if __name__ == '__main__':
    main()
