"""完整训练脚本 — G0_yolo11n_unified

模型   : 标准 YOLO11n（yolo11n.pt，无任何魔改）—— 消融基线 G0
数据   : 02_process_data/VOCdevkit（随机 8:2，train 3017 / val 755）
分辨率 : imgsz = 640
轮数   : epochs = 200
输出   : 04_Outputs/randomsplit_VOCdevkit/G0_yolo11n_unified
实测   : best mAP50 = 0.9347 @E84 | best mAP50-95 = 0.6916 @E147

本文件由 03_Code/common/train_ablation.py 的配置固化而来（2026-09-14），可独立运行：
    cd "/data02/machao/01_Projects/Gymnocypris eckloni"
    /data02/machao/anaconda_envs/fish_CV/bin/python "03_Code/randomsplit_VOCdevkit/train_G0_yolo11n_unified.py"
"""
import os

from ultralytics import YOLO

ROOT = "/data02/machao/01_Projects/Gymnocypris eckloni"

# ---- 数据 / 权重 / 输出 ----
DATA = os.path.join(ROOT, "02_process_data/VOCdevkit/data.yaml")      # 随机 8:2 口径
CKPT = os.path.join(ROOT, "03_Code/common/yolo11n.pt")                # 标准 YOLO11n 预训练权重
OUT = os.path.join(ROOT, "04_Outputs/randomsplit_VOCdevkit")          # 输出根目录
NAME = "G0_yolo11n_unified"                                           # 运行名（= 结果目录名）

# ---- 训练配置（与 train_ablation.py 的 UNIFIED 完全一致，保证可比）----
CFG = dict(
    data=DATA,
    epochs=200,
    imgsz=640,
    batch=16,
    workers=8,
    device=0,                 # 单卡；多卡并行时按需修改
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
    patience=0,               # 不早停
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
    print(f"\n===== {NAME} 完成，产物: {os.path.join(OUT, NAME)} =====")


if __name__ == "__main__":
    main()
