"""Detector training - resolution variant (standard YOLO11n, input size 960).

Same architecture and split as the G0 baseline, trained at 960 x 960 for the resolution
comparison reported in the manuscript. The released weights come from the G0 run.

Input    : imgsz = 960
Epochs   : 120, no early stopping
Output   : model directory
Measured : best mAP@0.5 = 0.9386 (epoch 52); best mAP@0.5:0.95 = 0.6919 (epoch 85)"""
import os

from ultralytics import YOLO

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "code"))

import gyo_paths as P                              # noqa: E402

DATA = P.DATA_YAML                                 # dataset descriptor (see dataset.yaml)
CKPT = os.environ.get("GYO_PRETRAINED", "yolo11n.pt")
OUT = P.MODEL                                      # output root
NAME = "G_H1_img960"                                                  # run name (= results directory name)

# ---- training configuration (identical across the ablation runs, for comparability) ----
CFG = dict(
    data=DATA,
    epochs=120,
    imgsz=960,
    batch=16,
    workers=8,
    device=0,                 # single GPU; pass --device when running on several
    optimizer="AdamW",
    lr0=5e-4,
    lrf=5e-5,
    momentum=0.937,
    weight_decay=0.001,
    warmup_epochs=5,
    warmup_momentum=0.8,
    warmup_bias_lr=0.1,
    box=0.05,
    cls=0.6,
    dfl=0.1,
    patience=0,               # no early stopping
    close_mosaic=10,
    seed=0,
    deterministic=True,
    amp=True,
    plots=True,
    val=True,
    project=OUT,
    name=NAME,
    exist_ok=True,
)


def main():
    print(f"\n===== {NAME} =====")
    print(f"data   : {DATA}")
    print(f"ckpt   : {CKPT}")
    print(f"imgsz  : {CFG['imgsz']} | epochs: {CFG['epochs']} | batch: {CFG['batch']}")
    print(f"output : {os.path.join(OUT, NAME)}")
    model = YOLO(CKPT)
    model.train(**CFG)
    print(f"\n===== {NAME} done; outputs: {os.path.join(OUT, NAME)} =====")


if __name__ == "__main__":
    main()
