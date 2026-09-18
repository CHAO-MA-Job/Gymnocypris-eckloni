# -*- coding: utf-8 -*-
"""gyo_paths.py - single source of truth for file locations.

Every script in this repository resolves its paths through this module; no script
hard-codes an absolute path. The defaults below describe the layout of the released
repository, and every entry can be redirected through an environment variable, so the
same scripts can be pointed at a private working copy without editing any code.

Released layout
---------------
    <repo>/annotations/          VOC XML labels and YOLO txt labels
    <repo>/split/                train.txt, val.txt (the 8:2 random split)
    <repo>/model/                best.pt, args.yaml, results.csv
    <repo>/quantification/       per-fish action-rate tables, one directory per body part
        opercular/stats/             16-1_respiration_stats.xlsx ... 25-3_...
        pectoral/stats/              16-1_pectoral_stats.xlsx    ... 25-3_...
        caudal/stats/                16-1_caudal_stats.xlsx      ... 25-3_...
    <repo>/tables/               derived kinematic and summary tables

What is *not* in the repository
-------------------------------
Raw recordings and keyframes are not hosted here (see README); obtain them from the first author. The scripts therefore
expect a working directory that also holds the per-video detector output
(``MP4/<recording>/bbox_data.xlsx``) and the intermediate tables produced by
``01_tables_kinematics``. Point ``GYO_WORK`` at such a directory to run the full chain.

Environment variables (all optional; values are absolute paths)
--------------------------------------------------------------
    GYO_BASE       repository root      default: parent of this file's directory
    GYO_WORK       working data root    default: <BASE>/quantification
    GYO_MP4        per-video tables     default: <WORK>/MP4
    GYO_TABLES     derived tables       default: <BASE>/tables
    GYO_WEIGHTS    detector weights     default: <BASE>/model/best.pt
    GYO_MODEL      model directory      default: <BASE>/model
    GYO_IMGSZ      inference size       default: 640 (must match training)
    GYO_DATA_YAML  dataset descriptor   default: <BASE>/dataset.yaml
    GYO_VIDEO_SRC  raw recordings       default: <BASE>/videos

Conventions
-----------
The historical helper names are kept so that the scripts read naturally:

    P.QUANT              working data root (per-part tables live under it)
    P.q('8_velocity_displacement.xlsx')     a file inside the working root
    P.RES                derived-table root;  P.res(...)
    P.MP4 / P.mp4(...)   per-video detector output
    P.WEIGHTS, P.IMGSZ, P.DATA_YAML, P.VIDEO_SRC
    P.show()             print the effective configuration (useful when debugging)
"""
import os
import sys

# ---------------------------------------------------------------- roots
_DEFAULT_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE = os.environ.get('GYO_BASE') or _DEFAULT_BASE
WORK = os.environ.get('GYO_WORK') or os.path.join(BASE, 'quantification')
MP4 = os.environ.get('GYO_MP4') or os.path.join(WORK, 'MP4')
TABLES = os.environ.get('GYO_TABLES') or os.path.join(BASE, 'tables')
MODEL = os.environ.get('GYO_MODEL') or os.path.join(BASE, 'model')
ANNOTATIONS = os.path.join(BASE, 'annotations')
SPLIT = os.path.join(BASE, 'split')

# Working root alias: step 1 and step 2 of the pipeline share one data root.
QUANT = WORK
# Derived tables (summary, 1 Hz centroid tracks, velocity/displacement, human counts).
RES = TABLES

# Model and training records.
TRAIN = MODEL
TRAIN_TAG = os.environ.get('GYO_TRAIN_TAG') or 'model'
WEIGHTS = os.environ.get('GYO_WEIGHTS') or os.path.join(MODEL, 'best.pt')
TRAIN_CSV = os.path.join(MODEL, 'results.csv')
IMGSZ = int(os.environ.get('GYO_IMGSZ') or 640)
DATA_YAML = os.environ.get('GYO_DATA_YAML') or os.path.join(BASE, 'dataset.yaml')

# Raw recordings (too large for GitHub and not part of the repository; obtain them from the first author).
VIDEO_SRC = os.environ.get('GYO_VIDEO_SRC') or os.path.join(BASE, 'videos')

# Historical table names -> names used in the released repository. Scripts may keep
# referring to the intermediate names; the helpers below translate them on the fly.
TABLE_ALIASES = {
    '6_6_summary_whole_body.xlsx': os.path.join(TABLES, 'per_fish_summary.xlsx'),
    '7_7_centroid_trajectory.xlsx': os.path.join(TABLES, 'centroid_trajectory_1hz.xlsx'),
    '8_8_velocity_displacement.xlsx': os.path.join(TABLES, 'velocity_displacement.xlsx'),
    '21-1_human.xlsx': os.path.join(TABLES, 'human_validation_21-1.xlsx'),
    'respiration.xlsx': os.path.join(WORK, 'opercular', 'respiration.xlsx'),
    'pectoral_rate.xlsx': os.path.join(WORK, 'pectoral', 'pectoral.xlsx'),
    'caudal_rate.xlsx': os.path.join(WORK, 'caudal', 'caudal.xlsx'),
    'per_fish_metrics.csv': os.path.join(TABLES, 'per_fish_metrics.csv'),
    'per_fish_metrics.xlsx': os.path.join(TABLES, 'per_fish_metrics.xlsx'),
}


# ---------------------------------------------------------------- helpers
def _resolve(root, parts):
    """Join ``parts`` onto ``root``, translating released table names."""
    if len(parts) == 1 and parts[0] in TABLE_ALIASES:
        return TABLE_ALIASES[parts[0]]
    return os.path.join(root, *parts)


def q(*parts):
    """Path inside the working data root (per-part tables, merged tables)."""
    return _resolve(WORK, parts)


def mp4(*parts):
    """Path inside the per-video detector-output directory."""
    return os.path.join(MP4, *parts)


def res(*parts):
    """Path inside the derived-table root."""
    return _resolve(TABLES, parts)


def train(*parts):
    """Path inside the model directory (weights, results.csv, args.yaml)."""
    return os.path.join(MODEL, *parts)


def part(region, *parts):
    """Path inside one body-part directory of the released quantification tables."""
    return os.path.join(WORK, region, *parts)


def stats(region, *parts):
    """Path inside the per-fish statistics directory of one body part."""
    return os.path.join(WORK, region, 'stats', *parts)


def pick(*candidates):
    """Return the first existing candidate, else the last one.

    Used where a file may live in either of two locations (new first, old as fallback).
    """
    for p in candidates[:-1]:
        if p and os.path.exists(p):
            return p
    return candidates[-1]


def ensure(*dirs):
    """Create output directories if they do not exist."""
    for d in dirs:
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------- diagnostics
def show(stream=None):
    """Print the effective path configuration."""
    stream = stream or sys.stdout
    print('[gyo_paths] effective configuration', file=stream)
    for k, v, is_path in (('BASE', BASE, 1), ('WORK (=QUANT)', WORK, 1),
                          ('MP4', MP4, 1), ('TABLES (=RES)', TABLES, 1),
                          ('MODEL (=TRAIN)', MODEL, 1), ('ANNOTATIONS', ANNOTATIONS, 1),
                          ('SPLIT', SPLIT, 1), ('TRAIN_TAG', TRAIN_TAG, 0),
                          ('IMGSZ', IMGSZ, 0), ('WEIGHTS', WEIGHTS, 1),
                          ('TRAIN_CSV', TRAIN_CSV, 1), ('DATA_YAML', DATA_YAML, 1),
                          ('VIDEO_SRC', VIDEO_SRC, 1)):
        # Non-path entries (TRAIN_TAG / IMGSZ) are printed without an existence marker.
        mark = ('   [missing]' if (is_path and not os.path.exists(v)) else '')
        print('   %-18s = %s%s' % (k, v, mark), file=stream)


if __name__ == '__main__':
    show()
