# -*- coding: utf-8 -*-
"""make_per_fish_metrics.py —— Step F（下游链汇总步）
================================================================
汇总"逐鱼"指标表 per_fish_metrics（供 Fig1/Fig2/Fig4 与 plot_analysis 使用）。

口径（与既有 per_fish_metrics.csv 完全一致；已用 16-1 反推验证）:
  velocity_cm_s   = mean( 8_速度位移_全身[sheet]['v/cm_mean'] )
  displacement_cm = max ( 8_速度位移_全身[sheet]['S/总位移_结束'] )
  operculum_N10s  = mean( 呼吸频率.xlsx[sheet]['呼吸频率'] )
  pectoral_N10s   = mean( 胸鳍摆动频率.xlsx[sheet]['胸鳍摆动频率'] )
  caudal_N10s     = mean( 尾鳍摆动频率.xlsx[sheet]['尾鳍摆动频率'] )
  cost_ratio      = operculum_N10s / velocity_cm_s

输入 :
  04_Outputs/02_模型量化数据_GH1/8_速度位移_全身.xlsx
  04_Outputs/03_分析结果/{呼吸频率,胸鳍摆动频率,尾鳍摆动频率}.xlsx
输出 :
  04_Outputs/03_分析结果/per_fish_metrics.csv            (15 行, 供出图)
  04_Outputs/03_分析结果/per_fish_metrics.xlsx
      sheet per_fish   : temp,fish,velocity_cm_s,displacement_cm,
                         operculum_N10s,pectoral_N10s,caudal_N10s,cost_ratio
      sheet per_window : temp,fish,region,time_sec,freq_N10s  (长表, 供 plot_analysis Fig3)
合规 : 只读输入表；只写 03_分析结果 下的 per_fish_metrics.*。
"""
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源）

KIN = P.q('8_速度位移_全身.xlsx')
RES = P.QUANT                  # 阶段2 归口：逐鱼指标与频率表同根（02_模型量化数据_GH1）

FREQ = {
    'operculum': ('呼吸频率.xlsx', '呼吸频率'),
    'pectoral':  ('胸鳍摆动频率.xlsx', '胸鳍摆动频率'),
    'caudal':    ('尾鳍摆动频率.xlsx', '尾鳍摆动频率'),
}


def fish_of(sheet):
    m = re.search(r'(\d+)\s*℃\s*-\s*(\d+)', str(sheet))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def main():
    if not os.path.exists(KIN):
        raise FileNotFoundError(f'未找到运动学表: {KIN}')
    kin = pd.ExcelFile(KIN)
    fx = {}
    for reg, (fname, _) in FREQ.items():
        p = os.path.join(RES, fname)
        fx[reg] = pd.ExcelFile(p) if os.path.exists(p) else None
        if fx[reg] is None:
            print(f'  ⚠ 缺少频率表: {p}')

    rows, win = [], []
    for sheet in kin.sheet_names:
        temp, fish = fish_of(sheet)
        if temp is None:
            continue
        k = kin.parse(sheet)
        velocity = float(pd.to_numeric(k['v/cm_mean'], errors='coerce').mean())
        disp = float(pd.to_numeric(k['S/总位移_结束'], errors='coerce').max())

        vals = {}
        for reg, (_, col) in FREQ.items():
            if fx[reg] is None or sheet not in fx[reg].sheet_names:
                vals[reg] = None
                continue
            d = fx[reg].parse(sheet)
            vals[reg] = float(pd.to_numeric(d[col], errors='coerce').mean())
            for _, r in d.iterrows():
                win.append({'temp': temp, 'fish': fish, 'region': reg,
                            'time_sec': r.get('开始时间（秒）'),
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
