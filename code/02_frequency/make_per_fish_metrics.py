# -*- coding: utf-8 -*-
"""Step F3: build the per-fish metric table that the summary tables are based on.

Definitions (identical to the published table):
    velocity_cm_s   = mean of the block speeds in the whole-body speed/displacement table
    displacement_cm = cumulative displacement at the end of the recording
    operculum_N10s  = mean opercular rate over the 10 s windows
    pectoral_N10s   = mean pectoral-fin rate over the 10 s windows
    caudal_N10s     = mean caudal rate over the 10 s windows
    cost_ratio      = opercular rate divided by swimming speed

Input : <work root>/8_velocity_displacement.xlsx and the three merged rate tables
Output: tables/per_fish_metrics.csv (15 rows, one per fish) and tables/per_fish_metrics.xlsx,
        with a per_fish sheet (one row per fish) and a per_window sheet in long format
        (temperature, fish, region, time in seconds, rate). The inputs are read-only."""
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # unified path entry point (environment variables redirect the data root)

KIN = P.q('8_8_velocity_displacement.xlsx')
RES = P.QUANT                  # step 2 output: per-fish metrics share the root with the rate tables

FREQ = {
    'operculum': ('respiration.xlsx', 'respiration'),
    'pectoral':  ('pectoral_rate.xlsx', 'pectoral_rate'),
    'caudal':    ('caudal_rate.xlsx', 'caudal_rate'),
}


def fish_of(sheet):
    m = re.search(r'(\d+)\D+(\d+)', str(sheet))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def main():
    if not os.path.exists(KIN):
        raise FileNotFoundError(f'kinematic table not found: {KIN}')
    kin = pd.ExcelFile(KIN)
    fx = {}
    for reg, (fname, _) in FREQ.items():
        p = os.path.join(RES, fname)
        fx[reg] = pd.ExcelFile(p) if os.path.exists(p) else None
        if fx[reg] is None:
            print(f'  rate table missing: {p}')

    rows, win = [], []
    for sheet in kin.sheet_names:
        temp, fish = fish_of(sheet)
        if temp is None:
            continue
        k = kin.parse(sheet)
        velocity = float(pd.to_numeric(k['v/cm_mean'], errors='coerce').mean())
        disp = float(pd.to_numeric(k['S/displacement_end'], errors='coerce').max())

        vals = {}
        for reg, (_, col) in FREQ.items():
            if fx[reg] is None or sheet not in fx[reg].sheet_names:
                vals[reg] = None
                continue
            d = fx[reg].parse(sheet)
            vals[reg] = float(pd.to_numeric(d[col], errors='coerce').mean())
            for _, r in d.iterrows():
                win.append({'temp': temp, 'fish': fish, 'region': reg,
                            'time_sec': r.get('start_time_s'),
                            'freq_N10s': pd.to_numeric(r.get(col), errors='coerce')})

        oper = vals.get('operculum')
        rows.append({
            'temp': temp, 'fish': fish,
            'velocity_cm_s': velocity, 'displacement_cm': disp,
            'operculum_N10s': oper, 'pectoral_N10s': vals.get('pectoral'),
            'caudal_N10s': vals.get('caudal'),
            'cost_ratio': (oper / velocity) if (oper is not None and velocity) else None,
        })

    pf = pd.DataFrame(rows).sort_values(['temp', 'fish']).reset_index(drop=True)
    pw = pd.DataFrame(win)
    os.makedirs(RES, exist_ok=True)
    pf.to_csv(os.path.join(RES, 'per_fish_metrics.csv'), index=False)
    with pd.ExcelWriter(os.path.join(RES, 'per_fish_metrics.xlsx'), engine='openpyxl') as w:
        pf.to_excel(w, sheet_name='per_fish', index=False)
        pw.to_excel(w, sheet_name='per_window', index=False)
    print(f'[OK] per_fish rows={len(pf)} | per_window rows={len(pw)}')
    print(pf.to_string())


if __name__ == '__main__':
    main()
