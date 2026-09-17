"""
补时间S_Origin_data.py —— 【补救工具】把 `时间S` 从 `时间戳` 重算填入
===================
目的: 修复 时间S 列大面积为空的问题。
原因: 量化脚本把 时间S 写成 Excel 公式(=HOUR(B)*3600+MINUTE(B)*60+SECOND(B))，
      保存时未重算，读取为 NaN。
修复: 时间戳列已是 "H:MM:SS" 文本，直接解析为秒填入 时间S，无需视频/fps。

⚠ 状态：**同一件事已在 `0_3_assemble_Origin_data_s.py`（Step B）内联完成**
   （它按时间戳重算时间S），故本脚本**不在现行一键链**中，仅在手工修表时使用。

默认输入/输出走 gyo_paths（可用环境变量覆盖）：
  GYO_TSFIX_IN   / GYO_TSFIX_OUT
合规: 只读输入、写出新文件不覆盖原表。
"""
import os
import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口

IN = Path(os.environ.get('GYO_TSFIX_IN') or P.q('0_Origin_data_s.xlsx'))
OUT = Path(os.environ.get('GYO_TSFIX_OUT') or P.q('0_Origin_data_s_tsfixed.xlsx'))


def parse_ts(t):
    if pd.isna(t):
        return None
    if isinstance(t, pd.Timedelta) or hasattr(t, 'total_seconds'):
        return int(t.total_seconds())
    s = str(t).split('.')[0]
    parts = [int(p) for p in s.split(':')]
    if len(parts) == 3:
        h, m, sec = parts
    elif len(parts) == 2:
        h, m, sec = 0, parts[0], parts[1]
    else:
        h = m = 0
        sec = parts[0]
    return h * 3600 + m * 60 + sec


def main():
    assert IN.exists(), f"输入不存在: {IN}"
    xl = pd.ExcelFile(IN)
    sheets = {}
    for s in xl.sheet_names:
        df = xl.parse(s)
        before = int(df['时间S'].notna().sum())
        df['时间S'] = df['时间戳'].apply(parse_ts)
        after = int(df['时间S'].notna().sum())
        print(f"{s:8s} 时间S: 修复前={before} 修复后={after} 总行数={len(df)} 样例={df['时间S'].iloc[:3].tolist()}")
        sheets[s] = df
    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        for s, df in sheets.items():
            df.to_excel(w, sheet_name=s, index=False)
    print(f"\n已写出(未覆盖原文件): {OUT}")


if __name__ == '__main__':
    main()
