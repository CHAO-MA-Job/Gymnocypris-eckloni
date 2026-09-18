"""Detector training - G0 baseline (standard YOLO11n, input size 640).

Model    : YOLO11n pretrained weights, no architectural change (ablation baseline G0)
Data     : 8:2 random split of the annotated keyframes (3,017 train / 755 validation)
Input    : imgsz = 640
Epochs   : 200, no early stopping
Output   : model directory (weights, results.csv, args.yaml)
Measured : best mAP@0.5 = 0.9347 (epoch 84); best mAP@0.5:0.95 = 0.6916 (epoch 147)

The dataset descriptor is resolved by gyo_paths (GYO_DATA_YAML, default <repo>/dataset.yaml).
Run from the repository root:
    python code/00_training/randomsplit_VOCdevkit/train_G0_yolo11n_unified.py"""
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
NAME = "G0_yolo11n_unified"                                           # run name (= results directory name)

# ---- training configuration (identical across the ablation runs, for comparability) ----
CFG = dict(
    data=DATA,
    epochs=200,
    imgsz=640,
    batch=16,
    workers=8,
    device=0,                 # single GPU; adjust when running on several
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
