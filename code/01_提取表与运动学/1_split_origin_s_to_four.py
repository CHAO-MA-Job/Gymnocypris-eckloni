"""1_split_origin_s_to_four.py — 将 0_Origin_data_s.xlsx 按类别规定拆分为四份子表（输出 1_全身/2_鳃盖/3_胸鳍/4_尾鳍）。
类别映射(沿用既有四子表的口径, 互斥分区):
  全身 -> 类别 {0}
  鳃盖 -> 类别 {1, 2}
  胸鳍 -> 类别 {3, 4}
  尾鳍 -> 类别 {5, 6, 7}
输入 : 04_Outputs/02_模型量化数据_GH1/0_Origin_data_s.xlsx
输出 : 04_Outputs/02_模型量化数据_GH1/{全身,鳃盖,胸鳍,尾鳍}.xlsx
       (不覆盖原表, 输出带来源目录, 可追溯)
合规 : 只读源表, 仅写新文件; 保留全部11列与时间S。
"""
import os
import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源）

SRC = Path(P.q('0_Origin_data_s.xlsx'))
OUT_DIR = Path(P.QUANT)

CAT_MAP = {
    '全身': [0],
    '鳃盖': [1, 2],
    '胸鳍': [3, 4],
    '尾鳍': [5, 6, 7],
}

def main():
    assert SRC.exists(), f'源表不存在: {SRC}'
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f'读取源表: {SRC}')
    sheets = pd.read_excel(SRC, sheet_name=None)
    print(f'  sheet数={len(sheets)}: {list(sheets.keys())}')

    summary = {name: 0 for name in CAT_MAP}
    for name, cats in CAT_MAP.items():
        out_name = {'全身': '1_全身', '鳃盖': '2_鳃盖', '胸鳍': '3_胸鳍', '尾鳍': '4_尾鳍'}[name]
        out_path = OUT_DIR / f'{out_name}.xlsx'
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            for sname, df in sheets.items():
                sub = df[df['类别'].isin(cats)].copy()
                sub.to_excel(writer, sheet_name=sname, index=False)
                summary[name] += len(sub)
        print(f'  写出 {out_name}.xlsx -> 总行数 {summary[name]}')

    print('\n拆分完成。各子表行数:')
    for k, v in summary.items():
        print(f'  {k}: {v}')
    total = sum(summary.values())
    print(f'  合计: {total} (应等于源表 {sum(len(d) for d in sheets.values())})')
    print(f'输出目录: {OUT_DIR}')

if __name__ == '__main__':
    main()
