# -*- coding: utf-8 -*-
"""0_3_assemble_Origin_data_s.py —— Step B（下游链第 2 步）
================================================================
把逐视频量化产物组装成 `0_Origin_data_s.xlsx`（15 个 sheet）。

输入 : 04_Outputs/02_模型量化数据_GH1/MP4/{16-1 … 25-3}/bbox_data.xlsx
输出 : 04_Outputs/02_模型量化数据_GH1/0_Origin_data_s.xlsx
           每个 sheet 名 = "{temp}℃-{rep}"（如 21℃-1），与下游频率脚本口径一致。
列    : 帧编号, 时间戳, 时间S, 类别, 置信度, x1, y1, x2, y2, 中心点X, 中心点Y
说明  : 量化脚本把 时间S 写成 Excel 公式（保存时未重算 → 读取为 NaN），
        此处按 时间戳("H:MM:SS") 重新计算秒数，保证下游可直接用数值。
合规  : 只读逐视频表；只写新文件；不覆盖源表。
"""
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源）

GH1 = P.QUANT
# 可选命令行覆盖：python 0_3_assemble_Origin_data_s.py [MP4根目录] [输出xlsx]
MP4 = sys.argv[1] if len(sys.argv) > 1 else P.MP4
OUT = sys.argv[2] if len(sys.argv) > 2 else P.q('0_Origin_data_s.xlsx')
# 同一帧多个 class 0（全身）框时只保留置信度最高的一个；设 0 关闭
DEDUP_CLS0 = os.environ.get('GYO_DEDUP_CLS0', '1') == '1'
COLS = ['帧编号', '时间戳', '时间S', '类别', '置信度', 'x1', 'y1', 'x2', 'y2', '中心点X', '中心点Y']


def parse_ts(t):
    """时间戳 -> 秒(int)。与 0_补时间S_Origin_data.py 同口径：
    ① 优先 Timedelta.total_seconds()；② 否则按 'H:MM:SS' / 'MM:SS' / 'SS' 文本解析。失败返回 None。"""
    if t is None or (isinstance(t, float) and pd.isna(t)):
        return None
    if hasattr(t, 'total_seconds'):
        try:
            return int(t.total_seconds())
        except Exception:
            return None
    s = str(t).strip().split('.')[0]
    if not s:
        return None
    try:
        parts = [int(float(p)) for p in s.split(':')]
    except Exception:
        return None
    if len(parts) == 3:
        h, m, sec = parts
    elif len(parts) == 2:
        h, m, sec = 0, parts[0], parts[1]
    elif len(parts) == 1:
        h = m = 0
        sec = parts[0]
    else:
        return None
    return h * 3600 + m * 60 + sec


def sort_key(vid):
    m = re.match(r'(\d+)\D+(\d+)', vid)
    return (int(m.group(1)), int(m.group(2))) if m else (9999, 9999)


def find_data_xlsx(vdir):
    """在每个视频目录里取"数据表"：排除 state_counts.xlsx；
    优先 bbox_data.xlsx（新量化）；否则取目录内最大的 .xlsx（兼容旧命名如 21-1.xlsx / control16-2.xlsx）。"""
    cands = [f for f in os.listdir(vdir)
             if f.lower().endswith('.xlsx') and 'state_counts' not in f.lower()]
    if not cands:
        return None
    pref = [f for f in cands if 'bbox_data' in f.lower()]
    pick = pref[0] if pref else max(cands, key=lambda f: os.path.getsize(os.path.join(vdir, f)))
    return os.path.join(vdir, pick)


def load_merged(path):
    """从"已合并的 15-sheet 表"读取并规范化：
    sheet 名 -> {temp}℃-{rep}（兼容 '16-1' / '16℃-1'）；按 时间戳 重算 时间S。"""
    xl = pd.ExcelFile(path)
    sheets = {}
    for sh in xl.sheet_names:
        m = re.match(r'(\d+)\D+(\d+)', str(sh))
        if not m:
            print(f'  skip（无法解析 sheet 名）: {sh}')
            continue
        name = f'{int(m.group(1))}℃-{int(m.group(2))}'
        df = xl.parse(sh)
        if '时间戳' in df.columns:
            df['时间S'] = df['时间戳'].map(parse_ts)
        cols = [c for c in COLS if c in df.columns]
        sheets[name] = df[cols]
        print(f'  {sh} -> sheet {name}: rows={len(df)}')
    return sheets


def dedupe_cls0(df):
    """同一帧出现多个 class 0（全身）框时，只保留置信度最高的一个。

    必要性（2026-09-14 手册必做项）：下游 `1_全身` 每帧须恰一行；重复会造成
    dt=0 → v/cm 算成 NaN，且 S/总位移 被重复累加。
    类别 1..7 保持原样多框输出，不影响频率表口径。
    返回 (新表, 重复帧数)。
    """
    if '类别' not in df.columns or '帧编号' not in df.columns:
        return df, 0
    is0 = df['类别'] == 0
    if not is0.any():
        return df, 0
    sub = df[is0]
    dup = int((sub['帧编号'].value_counts() > 1).sum())
    if dup == 0:
        return df, 0
    keep = sub.sort_values('置信度', ascending=False).groupby('帧编号').head(1)
    out = pd.concat([df[~is0], keep]).sort_values(['帧编号', '类别']).reset_index(drop=True)
    return out, dup


def main():
    if os.path.isfile(MP4) and MP4.lower().endswith('.xlsx'):
        print(f'检测到"合并文件"输入，直接规范化为标准 15-sheet 表: {MP4}')
        sheets = load_merged(MP4)
        if DEDUP_CLS0:
            for name in list(sheets):
                sheets[name], n = dedupe_cls0(sheets[name])
                if n:
                    print(f'  [去重] {name}: class0 重复帧 {n} 处已合并')
    else:
        if not os.path.isdir(MP4):
            raise FileNotFoundError(f'未找到量化目录: {MP4}')
        vids = [d for d in os.listdir(MP4) if os.path.isdir(os.path.join(MP4, d))]
        vids.sort(key=sort_key)
        sheets = {}
        for vid in vids:
            f = find_data_xlsx(os.path.join(MP4, vid))
            if f is None:
                print(f'  skip（目录内无数据表）: {vid}')
                continue
            m = re.match(r'(\d+)\D+(\d+)', vid)
            if not m:
                print(f'  skip（无法解析 temp/rep）: {vid}')
                continue
            sheet = f'{int(m.group(1))}℃-{int(m.group(2))}'
            df = pd.read_excel(f, sheet_name=0)
            if '时间戳' in df.columns:
                df['时间S'] = df['时间戳'].map(parse_ts)
            if DEDUP_CLS0:
                df, n = dedupe_cls0(df)
                if n:
                    print(f'  [去重] {sheet}: class0 重复帧 {n} 处已合并')
            cols = [c for c in COLS if c in df.columns]
            sheets[sheet] = df[cols]
            print(f'  {vid} -> sheet {sheet}: rows={len(df)}')

    if not sheets:
        print('[跳过] 未收集到任何逐视频表（检查各 {vid}/bbox_data.xlsx 是否存在），未写出文件。')
        return

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        for sh, df in sheets.items():
            df.to_excel(w, sheet_name=sh, index=False)
    print(f'[OK] {OUT}  sheets={len(sheets)}: {list(sheets.keys())}')


if __name__ == '__main__':
    main()
