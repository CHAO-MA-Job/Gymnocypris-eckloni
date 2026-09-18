# Provenance of the released detector weights

- **Model**: standard YOLO11n (no architectural modification), input size 640 x 640.
- **Split**: random 8:2 split of the annotated keyframes (3,017 train / 755 validation).
- **Training entry point**: `code/00_training/randomsplit_VOCdevkit/train_G0_yolo11n_unified.py`.
- **Reproduction**:

  ```bash
  python code/00_training/randomsplit_VOCdevkit/train_G0_yolo11n_unified.py
  ```

- **Key arguments**: AdamW; lr0 = 5e-4; lrf = 5e-5; weight decay = 0.001; momentum = 0.937;
  batch = 16; imgsz = 640; epochs = 200; patience = 0 (no early stopping); box = 0.05;
  cls = 0.6; dfl = 0.1; close_mosaic = 10; AMP on; seed = 0. The full record is in
  `args.yaml`, and per-epoch metrics are in `results.csv`.
- **Pretrained weights**: `yolo11n.pt` (Ultralytics), used as the starting point.
- **Result of the released checkpoint**: best mAP@0.5 = 0.9347 (epoch 84);
  best mAP@0.5:0.95 = 0.6916 (epoch 147); 200 epochs in total.
- **Inference protocol used for all quantification results**: `imgsz = 640`,
  test-time augmentation (`augment=True`), `conf = 0.25`.
