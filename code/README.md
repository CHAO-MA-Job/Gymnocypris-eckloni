# Code

Scripts for the detector, for the quantification of the recordings and for the behavioural
tables. Paths are resolved by `gyo_paths.py`, which points at the layout of this repository by
default and can be redirected through environment variables.

```
code/
├── gyo_paths.py                    path configuration (see the module docstring)
├── run_downstream.py               runs the quantification steps in order
├── 00_training/
│   └── randomsplit_VOCdevkit/      detector training (baseline and the 960 variant)
├── 01_tables_kinematics/           detector output -> kinematic tables
└── 02_frequency/                   kinematic tables -> action rates and per-fish metrics
```

## Detector output and kinematic tables (`01_tables_kinematics`)

| Script | In | Out |
|---|---|---|
| `0_quantify_video_tta.py` | a recording (`GYO_VIDEO_SRC`) | `MP4/<recording>/bbox_data.xlsx`, `state_counts.xlsx` |
| `0_3_assemble_Origin_data_s.py` | the per-recording workbooks | `0_Origin_data_s.xlsx` (15 sheets) |
| `1_split_origin_s_to_four.py` | `0_Origin_data_s.xlsx` | `whole_body`, `operculum`, `pectoral`, `caudal` workbooks |
| `5_process_quanshen.py` | the whole-body table | `5_formula_whole_body.xlsx` (dt, speed, displacement) |
| `6_8_regen_speed_disp_fixed.py` | the formula table | `6_summary_whole_body.xlsx`, `8_velocity_displacement.xlsx` |
| `7_center_trajectory_1hz.py` | the formula table | `7_centroid_trajectory.xlsx`, one point per second |

## Action rates and per-fish metrics (`02_frequency`)

| Script | In | Out |
|---|---|---|
| `postproc.py` | region tables | the counting rules, imported by the scripts below |
| `class12_respiration_frequency.py` | `opercular.xlsx` | `opercular/stats/<sheet>_respiration_stats.xlsx` |
| `class34_pectoral_frequency.py` | `pectoral.xlsx` | `pectoral/stats/<sheet>_pectoral_stats.xlsx` |
| `class567_caudal_frequency.py` | `caudal.xlsx` | `caudal/stats/<sheet>_caudal_stats.xlsx` |
| `combine_15_sheets.py` | the per-fish tables | one workbook per body part, 15 sheets each |
| `make_per_fish_metrics.py` | speed table and rate tables | `tables/per_fish_metrics.{csv,xlsx}` |
| `compute_{respiration,pectoral,caudal}.py` | the same inputs | consistency check, nothing written |
| `make_21-1_countboard.py` | fish 21-1 and its human counts | `tables/21-1_countboard_data.xlsx` |

## Running the steps

```bash
python code/run_downstream.py            # every step, in order
python code/run_downstream.py F2         # only steps whose name contains F2
python code/run_downstream.py --show     # print the effective paths
```

The recordings and keyframes are not distributed with this repository, so obtain them from the corresponding author and put them where step A expects.
With the per-recording workbooks already present, the rest of the chain runs on its own:

```bash
export GYO_SKIP_QUANTIFY=1
python code/run_downstream.py
```

Environment variables: `GYO_WORK` (working data root), `GYO_TABLES`, `GYO_MP4`, `GYO_WEIGHTS`,
`GYO_IMGSZ`, `GYO_DATA_YAML`, `GYO_VIDEO_SRC`, `GYO_BASE`. See `gyo_paths.py` for the defaults.
