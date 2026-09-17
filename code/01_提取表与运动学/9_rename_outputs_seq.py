"""9_rename_outputs_seq.py — 按产出先后给 Origin_data_s_拆分 下的本次会话产出编号(保留原名)。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源）

D = Path(P.QUANT)
# (序号, 原名)  — 顺序=生产先后
mapping = [
    (1, '全身.xlsx'),                 # 拆分: 类别0
    (2, '鳃盖.xlsx'),                 # 拆分: 类别1,2
    (3, '胸鳍.xlsx'),                 # 拆分: 类别3,4
    (4, '尾鳍.xlsx'),                 # 拆分: 类别5,6,7
    (5, '公式计算后_全身.xlsx'),        # 全身逐帧公式
    (6, '总结版_全身.xlsx'),           # 每10秒统计总结版
    (7, '中心点轨迹_全身.xlsx'),        # 每秒一个中心点(轨迹)
    (8, '速度位移_全身.xlsx'),         # 速度位移+加速度
]
for n, name in mapping:
    src = D / name
    if not src.exists():
        print('跳过(不存在):', name); continue
    dst = D / f'{n}_{name}'
    os.rename(src, dst)
    print(f'{n:>2}  {name}  ->  {dst.name}')
print('\n完成。当前目录:')
for p in sorted(D.iterdir()):
    if not p.name.startswith('~$'):
        print('  ', p.name)
