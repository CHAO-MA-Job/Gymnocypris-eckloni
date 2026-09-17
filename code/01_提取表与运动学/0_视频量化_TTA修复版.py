# -*- coding: utf-8 -*-
"""0_视频量化_TTA修复版.py —— 修复 23℃ 视频检测覆盖率不足（帧质量问题）

问题（2026-09-14 实测）
----------------------
原 `0_视频量化-历遍文件夹所有视频.py`（imgsz=960, augment=False, conf=0.25）的
**整帧检出覆盖率**：

    16/19/21℃  100.0%      25℃  98.3~100%      **23℃  65.4 / 68.7 / 71.3%**

23℃ 三条鱼缺失 29~35% 的帧，最长连续缺口 **7.5 / 12.83 / 7.43 s**。已排除的原因：
  - 分辨率/fps 完全相同（15 条均为 1920×1080@30）
  - 不是置信度阈值问题：缺口帧在 conf=0.01 下仍然多数「一个框都没有」（中位数 0.000）
  - 不是运动模糊：缺口帧与检出帧的 Laplacian 方差无差异（9.0~10.4）
  - 画面正常：全帧亮度统计一致（mean≈131.7 / std≈50.2）
  → 真因是**目标尺度不匹配**：23℃ 鱼在画面中偏大，960 输入下偏离训练尺度。

修复（依据实测对照，n=40 帧 × 3 条鱼）
-------------------------------------
  imgsz=640 + augment=True(TTA)：23℃ 缺口帧恢复 75~95%（中位 conf 0.50~0.60）；
  对正常视频几乎无影响（16-1/21-1 中心点偏差中位仅 5.7 / 7.1 px，框面积变化 ±1.4%）。
  → 因此**全库统一换协议**，避免按温度差异化推理带来的协议混淆。

附带修正（原脚本两处缺陷）
  - 原脚本分两段并 `cap.set(POS_FRAMES, split)` 重新定位，某些编码下会重复读帧；
    本版改为**单次顺序遍历**（不 seek）。
  - 同一帧出现 2 个 class 0（全身）框时会写出重复「帧编号」，导致下游 dt=0、
    v/cm 被算成 NaN；本版**每帧只保留置信度最高的 class 0 框**（单尾鱼只有一个全身框）。
    其余类别（1..8）保持原样多框输出，以免改变频率链路。

输入 : 01_Orgin_data/实验所用视频/*.mp4
输出 : 04_Outputs/02_模型量化数据_GH1_v2/MP4/{name}/bbox_data.xlsx  (+ state_counts.xlsx)
       —— 写到 **_v2** 新根目录，不覆盖现行产物；验证通过后再切换。
用法 : python 0_视频量化_TTA修复版.py                # 全部 15 条
       python 0_视频量化_TTA修复版.py 23-1 23-2      # 只跑指定视频
"""
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

# ---------------- 参数配置 ----------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源/模型）

MODEL = P.WEIGHTS                                              # 换模型设 GYO_WEIGHTS
SRC = P.VIDEO_SRC                                              # 源视频目录
OUT_ROOT = os.environ.get('GYO_TTA_OUT') or P.MP4              # 默认写回阶段1 产物根

IMGSZ = 640          # ★ 修复：原 960 → 640（目标偏大，需下采样到训练尺度）
AUGMENT = True       # ★ 修复：Test-Time Augmentation，恢复率 2.5% → 75~95%
CONF = 0.25          # 与现行一致（ultralytics 默认）
DEDUP_CLS0 = True    # ★ 修复：每帧仅保留置信度最高的 class 0 框（消除重复帧号）
EMPTY_CACHE_EVERY = 300

TARGETS = sys.argv[1:]   # 空 = 全部


def process(video_path):
    name = os.path.splitext(os.path.basename(video_path))[0]
    out_dir = os.path.join(OUT_ROOT, name)
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError('无法打开视频: %s' % video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    model = YOLO(MODEL)
    status_counts = defaultdict(int)
    rows = []
    n_det_frame = 0          # 有 class 0 的帧数
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

        # ---- 去重：同帧多个 class 0 只留最高置信度 ----
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
                '帧编号': n_read, '时间戳': ts, '时间S': int(n_read / fps),
                '类别': c, '置信度': float(cf[i]),
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                '中心点X': (x1 + x2) / 2, '中心点Y': (y1 + y2) / 2,
            })
        n_det_frame += int(got0)

        if n_read % EMPTY_CACHE_EVERY == 0:
            torch.cuda.empty_cache()
            gc.collect()
            el = time.time() - t0
            print('  %s  %6d/%d 帧  覆盖率=%.1f%%  %.1f 帧/s  已用 %.1f min'
                  % (name, n_read, total, n_det_frame / n_read * 100,
                     n_read / el, el / 60), flush=True)

    cap.release()

    pd.DataFrame({'状态ID': list(range(1, 9)),
                  '出现次数': [status_counts.get(i, 0) for i in range(1, 9)]}
                 ).to_excel(os.path.join(out_dir, 'state_counts.xlsx'), index=False)
    pd.DataFrame(rows).to_excel(os.path.join(out_dir, 'bbox_data.xlsx'), index=False)

    print('[OK] %s  读入=%d 帧  有全身框=%d 帧  覆盖率=%.1f%%  行数=%d  耗时=%.1f min'
          % (name, n_read, n_det_frame, n_det_frame / max(n_read, 1) * 100,
             len(rows), (time.time() - t0) / 60), flush=True)
    return n_read, n_det_frame


def main():
    if not os.path.exists(MODEL):
        raise FileNotFoundError('模型未找到: %s' % MODEL)
    vids = sorted(f for f in os.listdir(SRC) if f.lower().endswith('.mp4'))
    if TARGETS:
        vids = [f for f in vids if os.path.splitext(f)[0] in TARGETS]
    print('IMGSZ=%d AUGMENT=%s CONF=%.2f DEDUP_CLS0=%s | %d 条视频 → %s'
          % (IMGSZ, AUGMENT, CONF, DEDUP_CLS0, len(vids), OUT_ROOT), flush=True)
    for f in vids:
        process(os.path.join(SRC, f))


if __name__ == '__main__':
    main()
