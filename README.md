# Behavioural video quantification for *Gymnocypris eckloni* under warming

Code, annotations and model weights for the manuscript **"Non-invasive quantification of
fine-scale behaviour in *Gymnocypris eckloni* along a warming gradient"** (submitted to
*Animals*, MDPI).

The **raw videos and keyframe images are archived on Zenodo** because of their size:
**[Zenodo DOI / link — fill in after upload]**。

## What is in this repository

| Path | Contents |
|---|---|
`code/` | All scripts: keyframe extraction, dataset construction, detector training, video quantification, frequency analysis and figure plotting |
`annotations/Annotations/` | 3,772 VOC-format XML annotations |
`annotations/labels/` | The same annotations in YOLO txt format |
`split/train.txt`, `split/val.txt` | Image filenames in the 8:2 split (3,017 train / 755 validation) |
`model/best.pt` | Detector weights used for every result in the paper (mAP@0.5 = 0.9197) |
`model/results.csv` | Per-epoch training and validation metrics |
`tables/per_fish_metrics.csv` | Per-fish velocity, cumulative displacement and the three part-movement rates |
`tables/human_validation_21-1.xlsx` | Automated versus human counts per 10 s window (fish 21-1) |

## Ethogram

Eight classes over three functional regions, plus a whole-fish class used for localisation only:

| Class | Region | States |
|---|---|---|
1 | whole fish | localisation only |
2, 3 | operculum | closed, open |
4, 5 | pectoral fins | minimal contraction, maximal expansion |
6, 7, 8 | caudal peduncle | left, centred, right |

States are mutually exclusive within a region and may co-occur between regions.

## Environment

Python 3; `requirements.txt` is generated from the imports in `code/`, so pin the versions to
your own environment before use. Detector training used Ultralytics 8.3.86 at an input size of
640 × 640, on a workstation with an NVIDIA RTX 4070 (8 GB).

## Reproduction outline

1. Download the Zenodo deposit and place `videos_raw/` (15 recordings) and `images/` (3,772
   keyframes) where `code/` expects them.
2. Rebuild the dataset from `split/*.txt` together with `annotations/`.
3. Either train the detector or reuse `model/best.pt`.
4. Run the quantification and frequency steps, then check against `tables/per_fish_metrics.csv`.

The scripts in `code/` carry their own notes on arguments and intermediate files; start from
the dataset-construction and quantification steps.

## Ethics

All procedures were approved by the Institutional Animal Care and Use Committee of Southwest
University (protocol code IACUC-20240702-09; date of approval: 2 July 2024).

## Licence

Code: **MIT**. Annotations and tables: **CC BY 4.0**. Videos and images on Zenodo: **CC BY 4.0**.

## Cite

See `CITATION.cff`. Once the Zenodo DOI is issued, add it there and to the Data Availability
Statement of the manuscript.
