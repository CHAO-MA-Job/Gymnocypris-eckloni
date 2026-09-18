# -*- coding: utf-8 -*-
"""run_downstream.py - one-command execution of the quantification pipeline.

Every path is resolved by ``gyo_paths.py``; this script writes no absolute path itself.

Step 1 - tables and kinematics          -> working data root (P.WORK / P.QUANT)
    A   detector output per recording    MP4/<recording>/bbox_data.xlsx      (needs videos)
    B   assemble                        0_Origin_data_s.xlsx                  (15 sheets)
    C   split by region                 1_whole_body / 2_operculum / 3_pectoral / 4_caudal
    D   kinematics                      5_formula / 6_summary / 7_centroid_trajectory
                                        / 8_velocity_displacement
    E   table formatting                in-place (header, freeze row, column widths)

Step 2 - action rates per body part     -> working data root
    F1  per-fish rate tables            <region>/stats/  (15 files per body part)
    F2  merge the 15 sheets             respiration.xlsx / pectoral.xlsx / caudal.xlsx
    F3  per-fish summary                tables/per_fish_metrics.{csv,xlsx}
    F4  consistency check               recompute from the region tables, compare cell by cell
    F5  human agreement                 tables/human_validation_21-1.xlsx (ground truth)

The detector step needs the raw recordings, which are not distributed with this repository rather than
shipped here; set ``GYO_SKIP_QUANTIFY=1`` when the per-video tables already exist.

Usage
-----
    python code/run_downstream.py                # all steps
    python code/run_downstream.py F2             # only steps whose name contains "F2"
    python code/run_downstream.py merge check    # select steps by keyword
    python code/run_downstream.py --show         # print the effective configuration only

Environment
-----------
    GYO_SKIP_QUANTIFY=1   skip step A (per-video detector output)
    GYO_SKIP_FORMAT=1     skip step E (in-place Excel formatting)
    GYO_PYTHON            interpreter used for the steps (default: this interpreter)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gyo_paths as P          # noqa: E402

# Windows consoles default to a legacy code page that cannot print every character.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# (step, label, script path relative to this directory)
STEPS = [
    ('A', 'detector output per recording', '01_tables_kinematics/0_quantify_video_tta.py'),
    ('B', 'assemble Origin_data_s', '01_tables_kinematics/0_3_assemble_Origin_data_s.py'),
    ('C', 'split into four region tables', '01_tables_kinematics/1_split_origin_s_to_four.py'),
    ('D1', 'kinematics: formula table', '01_tables_kinematics/5_process_quanshen.py'),
    ('D2', 'kinematics: speed and displacement', '01_tables_kinematics/6_8_regen_speed_disp_fixed.py'),
    ('D3', 'centroid trajectory at 1 Hz', '01_tables_kinematics/7_center_trajectory_1hz.py'),
    ('E', 'format tables in place', '01_tables_kinematics/10_beautify_tables.py'),
    ('F1a', 'action rate: operculum', '02_frequency/class12_respiration_frequency.py'),
    ('F1b', 'action rate: pectoral fin', '02_frequency/class34_pectoral_frequency.py'),
    ('F1c', 'action rate: caudal peduncle', '02_frequency/class567_caudal_frequency.py'),
    ('F2', 'merge the 15 sheets', '02_frequency/combine_15_sheets.py'),
    ('F3', 'per-fish metrics', '02_frequency/make_per_fish_metrics.py'),
    ('F4a', 'check: operculum recomputation', '02_frequency/compute_respiration.py'),
    ('F4b', 'check: pectoral recomputation', '02_frequency/compute_pectoral.py'),
    ('F4c', 'check: caudal recomputation', '02_frequency/compute_caudal.py'),
    ('F5', 'human agreement table', '02_frequency/make_21-1_countboard.py'),
]


def selected():
    """Steps left after applying the skip switches and the command-line keywords."""
    want = [a for a in sys.argv[1:] if not a.startswith('-')]
    if os.environ.get('GYO_SKIP_QUANTIFY'):
        want_skip = {'A'}
    else:
        want_skip = set()
    if os.environ.get('GYO_SKIP_FORMAT'):
        want_skip.add('E')
    rows = []
    for step, label, rel in STEPS:
        if step in want_skip:
            continue
        if want and not any(w.lower() in step.lower() or w.lower() in label.lower()
                            for w in want):
            continue
        rows.append((step, label, os.path.join(HERE, rel)))
    return rows


def main():
    if '--show' in sys.argv:
        P.show()
        return 0
    steps = selected()
    if not steps:
        print('[run_downstream] no step matches the selection.')
        return 1

    print('[run_downstream] %d step(s) selected' % len(steps))
    for step, label, script in steps:
        print('  %-4s %s' % (step, label))
    print()

    py = os.environ.get('GYO_PYTHON') or sys.executable
    for step, label, script in steps:
        if not os.path.exists(script):
            print('[run_downstream] %-4s skipped: script not found (%s)' % (step, script))
            continue
        print('=' * 72)
        print('[run_downstream] %-4s %s' % (step, label))
        print('=' * 72, flush=True)
        code = subprocess.call([py, script], cwd=HERE)
        if code != 0:
            print('[run_downstream] %s failed (exit %d); stopping.' % (step, code))
            return code
    print('\n[run_downstream] done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
