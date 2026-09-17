# -*- coding: utf-8 -*-
"""combine_15_sheets.py —— Step E2（15 表组合）
================================================================
把"逐鱼/逐视频"的分表合并成**单个 15-sheet 工作簿**（下游 fig3/fig4/plot_analysis
与 Step F 读取的合并表口径）。

当前用于三部位频率：
  输入 : 03_分析结果/呼吸频率/      **/*统计.xlsx     (15 个: 16℃-1 … 25℃-3)
         03_分析结果/胸鳍摆动频率/  **/*统计.xlsx
         03_分析结果/尾鳍摆动频率/  **/*统计.xlsx
  输出 : 03_分析结果/呼吸频率.xlsx
         03_分析结果/胸鳍摆动频率.xlsx
         03_分析结果/尾鳍摆动频率.xlsx      (各 15 sheet, sheet 名 = {temp}℃-{rep})

规则:
  - sheet 名 = 文件名去掉 "_<部位>统计.xlsx" 后缀（如 "16℃-1_呼吸频率统计.xlsx" -> "16℃-1"）。
  - sheet 顺序按 (温度, 平行) 排序。
  - 逐鱼文件列 = [时间段编号, 开始时间（秒）, <频率列>]，合并后原样保留。

合规: 只读逐鱼表；只写 03_分析结果 下的合并表；不覆盖源文件。
"""
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源）

# 阶段2 归口：逐部位统计与合并表同放在 02_模型量化数据_GH1
RES = P.QUANT

# 需要合并的部位（= 子目录名 = 输出文件名）
PARTS = ['呼吸频率', '胸鳍摆动频率', '尾鳍摆动频率']


def parse_sheet(fname):
    stem = re.sub(r'\.xlsx$', '', fname, flags=re.I)
    stem = re.sub(r'_[^_]*统计$', '', stem)   # 去掉 "_呼吸频率统计" 等后缀
    return stem.strip()


def skey(name):
    m = re.search(r'(\d+)\s*℃?\s*-\s*(\d+)', str(name))
    return (int(m.group(1)), int(m.group(2))) if m else (9999, 9999)


def main():
    for part in PARTS:
        base = os.path.join(RES, part)
        if not os.path.isdir(base):
            print(f'  [跳过] {part}: 目录不存在 {base}')
            continue
        files = []
        for root, _, fs in os.walk(base):
            for f in fs:
                if f.lower().endswith('.xlsx') and '统计' in f:
                    files.append(os.path.join(root, f))
        if not files:
            print(f'  [跳过] {part}: 未找到逐鱼统计文件（{base} 下）')
            continue

        sheets = {}
        for fp in files:
            sh = parse_sheet(os.path.basename(fp))
            if not sh:
                print('    skip(无法解析 sheet 名):', fp)
                continue
            sheets[sh] = pd.read_excel(fp)

        order = sorted(sheets.keys(), key=skey)
        out = os.path.join(RES, f'{part}.xlsx')
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            for sh in order:
                sheets[sh].to_excel(w, sheet_name=sh, index=False)
        print(f'  [OK] {out}  sheets={len(order)}: {order}')


if __name__ == '__main__':
    main()
