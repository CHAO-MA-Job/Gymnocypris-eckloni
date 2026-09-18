# Behavioural video quantification for *Gymnocypris eckloni* under warming

Code, annotations and model weights for the study of non-invasive quantification of fine-scale
behaviour in *Gymnocypris eckloni* along a warming gradient.

The **training code and the annotated training dataset** are here, together with the detector
weights and the per-fish tables. The raw video recordings and keyframe images are not hosted in a
public repository; further inquiries can be directed to the corresponding author(s).

## What is in this repository

| Path | Contents |
|---|---|
| `code/` | Scripts for detector training, video quantification and the behavioural tables |
| `annotations/Annotations/` | 3,772 VOC-format XML annotations |
| `annotations/labels/` | The same annotations in YOLO txt format |
| `split/train.txt`, `split/val.txt` | Image filenames in the 8:2 split (3,017 train / 755 validation) |
| `dataset.yaml` | Dataset descriptor used for training and validation |
| `model/best.pt` | Detector weights used for every result in the paper (mAP@0.5 = 0.9197) |
| `model/args.yaml`, `model/results.csv` | Training arguments and per-epoch metrics |
| `model/PROVENANCE.md` | How the released weights were produced |
| `quantification/opercular/stats/`, `quantification/pectoral/stats/`, `quantification/caudal/stats/` | Per-fish action-rate tables, one workbook per recording for each body part |
| `tables/per_fish_metrics.csv` | Per-fish swimming speed, cumulative displacement and the three part-movement rates |
| `tables/per_fish_summary.xlsx`, `tables/centroid_trajectory_1hz.xlsx`, `tables/velocity_displacement.xlsx` | Per-fish summary, 1 Hz centroid tracks and the velocity/displacement table |
| `tables/human_validation_21-1.xlsx` | Automated versus human counts per 10 s window for fish 21-1 |
| `docs/pipeline.md` | Training and quantification pipeline |

## Ethogram

Eight classes over three functional regions, plus a whole-fish class used for localisation only:

| Class | Region | States |
|---|---|---|
| 1 | whole fish | localisation only |
| 2, 3 | operculum | closed, open |
| 4, 5 | pectoral fins | minimal contraction, maximal expansion |
| 6, 7, 8 | caudal peduncle | left, centred, right |

States are mutually exclusive within a region and may co-occur between regions.

## Environment

Python 3, NumPy, pandas, OpenCV, matplotlib, openpyxl and Ultralytics. `requirements.txt` lists
the packages imported by `code/`; pin the versions to your own environment before use. Detector
training used Ultralytics 8.4.6 at an input size of 640 x 640.

## Reproduction outline

1. Obtain the recordings and keyframes from the corresponding author and unpack them where `code/`
   expects them (`GYO_VIDEO_SRC` for the recordings, `images/` for the keyframes).
2. Rebuild the dataset from `split/*.txt` together with `annotations/`, using `dataset.yaml`.
3. Either train the detector with `code/00_training/randomsplit_VOCdevkit/train_G0_yolo11n_unified.py`
   or reuse `model/best.pt`.
4. Run the quantification and the action-rate steps with `python code/run_downstream.py`, then
   compare the result with `tables/per_fish_metrics.csv`.

`code/README.md` lists the scripts with their inputs and outputs.

## Licence

Code: **MIT**. Annotations and tables: **CC BY 4.0**. Recordings and keyframes obtained from the authors:
**CC BY 4.0**.

## Cite

See `CITATION.cff`.
