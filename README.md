# Gymnocypris eckloni video analysis: code package

The package contains the chronological-split YOLO11n training and video inference entrypoints, regional event-counting code, agreement analysis, and scripts for Figures 3–6. The figure scripts use the accompanying processed data.

## Contents

- `01_dataset/`: images, YOLO labels, split manifests and per-video counts.
- `02_model/`: trained model, initial weights, training configuration and logs.
- `03_code/entrypoints/`: training, video inference and event counting.
- `03_code/analysis/`: agreement-statistics verification.
- `03_code/figures/`: scripts for the manuscript Figures 3–6.
- `04_analysis_data/`: processed inputs used by the figure and agreement scripts.

The split contains 2,891 training images, 635 validation images and 246 guard images from eight fish. Images and YOLO labels are included under `01_dataset/images/` and `01_dataset/labels/`; the training entrypoint accepts this dataset directory via `--dataset`. The video path is supplied to the inference entrypoint.

## Run

Install dependencies using `pip install -r requirements.txt`. The commands below are executed from this directory. Install a suitable PyTorch/CUDA build for GPU use.

```bash
python 03_code/entrypoints/train_time80.py --dataset path/to/dataset --check-only
python 03_code/entrypoints/train_time80.py --dataset path/to/dataset --device 0 --output runs
python 03_code/entrypoints/infer_video.py --video path/to/video.mp4 --output runs/video_01 --device 0
python 03_code/entrypoints/count_events.py --detections runs/video_01/bbox_data.xlsx --total-frames FRAME_COUNT --output runs/video_01/events
python 03_code/analysis/核验一致性界限和CCC.py
python 03_code/figures/Figure3_模型性能与人工定位对照.py
python 03_code/figures/Figure4_原结构_含平滑插图.py
python 03_code/figures/Figure5_按已处理数据绘制.py
python 03_code/figures/Figure6_A恢复原版点云.py
```

Inference uses the trained model, 640-pixel input and test-time augmentation by default. Event counting uses complete 300-frame windows at 30 fps. Generated figures and analysis outputs are written under `runs/`. Input and output paths can be selected for the local environment.

Model labels are YOLO indices 0–7: whole fish; operculum open; operculum closed; pectoral fins extended; pectoral fins contracted; caudal peduncle left; centred; right.

The image dataset, labels, split manifests, model weights, code and selected processed data are included in this repository. Original videos are available from the authors upon request.

## Dependency and initial-weight provenance

Training and inference use the Ultralytics package. Ultralytics documents AGPL-3.0 and Enterprise licensing at https://www.ultralytics.com/license and publishes its source license at https://github.com/ultralytics/ultralytics/blob/main/LICENSE. The included `yolo11n_pretrained.pt` was copied from the local project training assets; its SHA-256 is `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`, matching the saved training manifest.
