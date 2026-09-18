# Training and quantification pipeline

Notes on the detector, the quantification step and the tables that the analysis is based on.
All values below are taken from `model/args.yaml`, `model/results.csv` and the quantification
output.

## 1. Environment

| Item | Value |
|---|---|
| Python | 3.10 |
| PyTorch | 2.6.0 (CUDA 12.4) |
| Ultralytics | 8.4.6 |
| Task | object detection (YOLO) |

## 2. Dataset

The detector was trained on keyframes extracted from the recordings at every fifth frame, with
blurred and occluded frames removed by hand. Annotations are given in VOC XML
(`annotations/Annotations/`) and in YOLO txt format (`annotations/labels/`), with 8 classes
over three body regions plus a whole-fish class used for localisation only.

| Subset | Images | Labels | Instances |
|---|---|---|---|
| train | 3,017 | 3,017 | 12,068 |
| validation | 755 | 755 | 3,020 |
| total | 3,772 | 3,772 | 15,088 |

The split is a random 8:2 division of the keyframes; the file names of each subset are listed
in `split/train.txt` and `split/val.txt`.

The recordings themselves are available from the corresponding author (see the repository README). Fifteen
recordings are used, three at each of 16, 19, 21, 23 and 25 degrees Celsius, named `16-1` to
`25-3`. Each is 1920 x 1080 at 30 frames per second and about 10 minutes long, giving 278,970
frames in total.

## 3. Detector training

Standard YOLO11n (pretrained weights, no architectural change): 2,591,400 parameters,
6.4 GFLOPs. The training script is
`code/00_training/randomsplit_VOCdevkit/train_G0_yolo11n_unified.py`, and the arguments are
recorded in `model/args.yaml`:

| Setting | Value | Setting | Value |
|---|---|---|---|
| epochs | 200 | imgsz | 640 |
| batch | 16 | patience | 0 (no early stopping) |
| optimizer | AdamW | seed | 0 |
| lr0 | 5e-4 | lrf | 5e-5 |
| momentum | 0.937 | weight decay | 0.001 |
| warmup epochs | 5 | close_mosaic | 10 |
| loss weights | box 0.05, cls 0.6, dfl 0.1 | AMP | on |

Augmentation used the Ultralytics defaults: mosaic 1.0 (disabled for the final 10 epochs),
horizontal flip 0.5, translation 0.1, scale 0.5, HSV jitter (h 0.015, s 0.7, v 0.4),
RandAugment and random erasing 0.4; rotation, shear, perspective and vertical flip were off.
NMS used IoU 0.7 with at most 300 detections.

Training results (`model/results.csv`): best mAP@0.5 = 0.9347 at epoch 84 (precision 0.8576,
recall 0.8865) and best mAP@0.5:0.95 = 0.6916 at epoch 147; mAP@0.5 at the last epoch was
0.9053. The released checkpoint is the best one, `model/best.pt`.

## 4. Quantification

Every recording is processed frame by frame with `model/best.pt` at imgsz 640, with test-time
augmentation enabled, a confidence threshold of 0.25, NMS IoU 0.7 and at most 300 detections.
Confidence and NMS thresholds are the Ultralytics defaults; the input size matches training.

Test-time augmentation is used for the quantification step because it recovers frames in which
no box would otherwise be detected: over the fifteen recordings it lowers the fraction of empty
frames from 3.5% to 1.3% and raises the number of boxes from 1,099,344 to 1,301,182, while the
mean confidence changes from 0.686 to 0.683. The detection metrics are the plain
(non-augmented) validation values recorded in `model/results.csv`.

Per recording, the script writes one row per detected box and a table of per-class counts. The
columns are:

| Column | Meaning |
|---|---|
| frame | frame index, starting at 1 |
| timestamp | time of the frame in HH:MM:SS |
| time_s | the same time in seconds |
| class | class index from the detector (0 to 7) |
| confidence | box confidence |
| x1, y1, x2, y2 | bounding box in the 1920 x 1080 frame |
| centroid_x, centroid_y | box centre |

Across the fifteen recordings the detector returned 1,301,182 boxes over 278,970 frames
(4.72 boxes per frame) and detected at least one box in 98.7% of frames. Box counts per class
were 280,178, 148,097, 180,248, 159,027, 204,607, 94,074, 153,100 and 81,851 for classes 1 to 8.

## 5. Tables derived downstream

`code/01_tables_kinematics` assembles the per-recording boxes into one workbook, splits it into
the four region tables, and computes per-frame kinematics (dt, displacement, speed, cumulative
displacement) and 10 s block summaries. The factors are 30 frames per second and 0.03125 cm per
pixel.

`code/02_frequency` turns the region tables into the three action rates with the counting rules
in `02_frequency/postproc.py`, merges the per-fish tables and builds
`tables/per_fish_metrics.csv`. The rates are descriptive indices: across the five temperatures
the pectoral and caudal rates show no detectable effect (p = 0.34 and p = 0.25) and the
opercular rate is non-monotonic (p = 0.015). Agreement with the manual counts of fish 21-1 over
30 windows of 10 s is AR 94.2% (operculum), 81.2% (pectoral) and 82.7% (caudal).
