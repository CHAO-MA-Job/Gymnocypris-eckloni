# -*- coding: utf-8 -*-
"""gyo_paths.py —— 项目【统一路径入口】（唯一真源）
================================================================
所有下游脚本一律 `import gyo_paths as P` 取路径，**禁止再写绝对路径**。
默认值 = 项目现行目录结构（默认不改变任何现有行为）；
设环境变量即可整体切换到"服务器新量化产物"，实现一键承接。

目录归口（2026-09-15 更新）
------------------------
  阶段1 提取表      → P.QUANT   (`04_Outputs/02_模型量化数据640_G0_TTA`)
      0_Origin_data_s.xlsx、1_全身 / 2_鳃盖 / 3_胸鳍 / 4_尾鳍、
      5_公式计算后_全身、6_总结版_全身、7_中心点轨迹_全身、8_速度位移_全身
  阶段2 三部位频率  → P.QUANT   （`呼吸频率/`、`胸鳍摆动频率/`、`尾鳍摆动频率/`
                               及三张 15-sheet 合并表、per_fish_metrics.*）
  阶段3 模型作图    → P.MODEL_FIG (`04_Outputs/03_模型作图`) —— 混淆矩阵 / 训练曲线
  阶段4 行为作图    → P.FIG      (`04_Outputs/04_行为作图`) —— **仅**运动学(速度/位移) + 轨迹
  阶段5 频率作图    → P.FREQ     (`04_Outputs/05_频率计算`) —— 仅 F2 波形（进正文，2026-09-16 收窄）
  阶段6 补充作图    → P.SUPP     (`04_Outputs/06_Supplementary`) —— F1/F3/F4/F5 + Fig9/Fig10（不进正文）
  分析中间物        → P.RES      (`04_Outputs/03_分析结果`) —— 人眼真值、countboard 等

数据根与模型口径（2026-09-15 统一裁定，详见 `总览.md` §10-11 / §12）
--------------------------------------------------------------
  **模型 = `G0_yolo11n_640`（yolo11n + imgsz=640）；推理 = `imgsz=640` + TTA(`augment=True`)；conf=0.25**
  数据根 = `02_模型量化数据640_G0_TTA`（与模型/协议同名，自洽）。

  变更史：`02_模型量化数据_GH1` → `02_模型量化数据_960`（G_H1 @960，无 TTA）→ **现行**。
  原因：23℃ 三条视频在 960 输入下仅检出 48–58% 的帧（鱼贴近水面 → 尺度不匹配）；
  `imgsz=640 + TTA` 把缺口恢复率由 0–5% 提到 22.5%，23℃ 全身覆盖 68.5% → **90.5%**。

  ⚠ 已知且**已接受**的取舍：同一套 `640+TTA` 下，`G_H1_img960` 权重对 23℃ 缺口的
    恢复率为 70.8%（G0 为 22.5%）。本项目选择 **G0**，以换取「模型 ↔ 目录名 ↔ 记录」三者一致
    （`agents.md` 亦以 G0 为下游基线）。若日后改用 H1，目录名 `_G0_` 须同步改名。

环境变量（全部可选，值为绝对路径）
--------------------------------
  GYO_BASE       项目根           默认 D:\\Deep_Learning\\01_Projects\\Gymnocypris eckloni
  GYO_QUANT      阶段1/2 数据根    默认 <BASE>\\04_Outputs\\02_模型量化数据640_G0_TTA
  GYO_MP4        逐视频量化产物根  默认 <QUANT>\\MP4          （Step B 的输入）
  GYO_MODELFIG   阶段3 图根        默认 <BASE>\\04_Outputs\\03_模型作图
  GYO_FIG        阶段4 图根        默认 <BASE>\\04_Outputs\\04_行为作图
  GYO_FREQ       阶段5 图根        默认 <BASE>\\04_Outputs\\05_频率计算
  GYO_RES        分析中间物根      默认 <BASE>\\04_Outputs\\03_分析结果
  GYO_TRAIN      训练结果根        默认 <BASE>\\04_Outputs\\01_Result_train
  GYO_WEIGHTS    YOLO 权重 .pt     （阶段3 混淆矩阵）；默认 <TRAIN>\\G0_yolo11n_640\\weights\\best.pt
  GYO_TRAIN_TAG  训练结果子目录名   默认 G0_yolo11n_640（用于定位 results.csv）
  GYO_IMGSZ      推理尺寸          默认 640（须与训练尺寸一致）
  GYO_DATA_YAML  数据 yaml         默认 03_Code/03_模型作图/data_val.yaml

用法（所有脚本统一开头）
----------------------
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import gyo_paths as P

    P.QUANT            # 阶段1/2 数据根
    P.q('1_全身.xlsx')  # 阶段1/2 数据根下的文件
    P.FIG / P.fig('Fig7') / P.FREQ / P.freq('F2_waveform.png')
    P.SUPP / P.supp('Fig9_trajectory_metrics.png')
    P.mfig('Fig6_confusion.png')

    P.show()           # 打印当前生效配置（排错用）
"""
import os
import sys

# ---------------------------------------------------------------- 根目录
_DEFAULT_BASE = r'D:\Deep_Learning\01_Projects\Gymnocypris eckloni'

BASE = os.environ.get('GYO_BASE') or _DEFAULT_BASE
OUT = os.path.join(BASE, '04_Outputs')

QUANT = os.environ.get('GYO_QUANT') or os.path.join(
    OUT, '02_模型量化数据640_G0_TTA')
MP4 = os.environ.get('GYO_MP4') or os.path.join(QUANT, 'MP4')
MODEL_FIG = os.environ.get('GYO_MODELFIG') or os.path.join(OUT, '03_模型作图')
FIG = os.environ.get('GYO_FIG') or os.path.join(OUT, '04_行为作图')
# 阶段5 频率作图（2026-09-15 从 FIG 拆分：`04_行为作图` 只留运动学 + 轨迹）
FREQ = os.environ.get('GYO_FREQ') or os.path.join(OUT, '05_频率计算')
# 阶段6 补充作图（2026-09-16）：不进正文的描述性图 → 06_Supplementary
SUPP = os.environ.get('GYO_SUPP') or os.path.join(OUT, '06_Supplementary')
# 分析中间物：2026-09-15 起**并入数据根**（`21-1_人眼.xlsx`、`21-1_countboard_data.xlsx`
# 等与阶段1/2 产物同目录）；原独立的 `04_Outputs/03_分析结果` 已撤销。
RES = os.environ.get('GYO_RES') or QUANT
TRAIN = os.environ.get('GYO_TRAIN') or os.path.join(OUT, '01_Result_train')

# 原始素材 / 代码
VIDEO_SRC = os.path.join(BASE, '01_Orgin_data', '实验所用视频')
_CODE = os.path.join(BASE, '03_Code')

# 模型 / 训练
# 现行模型（2026-09-15 统一裁定）：G0_yolo11n_640 —— 与数据根 `_640_G0_TTA` 同名自洽
TRAIN_TAG = os.environ.get('GYO_TRAIN_TAG') or 'G0_yolo11n_640'
WEIGHTS = os.environ.get('GYO_WEIGHTS') or os.path.join(
    TRAIN, TRAIN_TAG, 'weights', 'best.pt')
TRAIN_CSV = os.path.join(TRAIN, TRAIN_TAG, 'results.csv')
# 推理尺寸：须与训练尺寸一致（G0_yolo11n_640 → 640）
IMGSZ = int(os.environ.get('GYO_IMGSZ') or 640)
DATA_YAML = os.environ.get('GYO_DATA_YAML') or os.path.join(
    _CODE, '03_模型作图', 'data_val.yaml')


# ---------------------------------------------------------------- 便捷拼接
def q(*parts):
    """阶段1/2 数据根下的路径。"""
    return os.path.join(QUANT, *parts)


def mp4(*parts):
    """逐视频量化产物目录下的路径。"""
    return os.path.join(MP4, *parts)


def fig(*parts):
    """阶段4 行为作图根下的路径（**仅**运动学 + 轨迹）。"""
    return os.path.join(FIG, *parts)


def freq(*parts):
    """阶段5 频率作图根下的路径。"""
    return os.path.join(FREQ, *parts)


def supp(*parts):
    """阶段6 补充作图根下的路径。"""
    return os.path.join(SUPP, *parts)


def mfig(*parts):
    """阶段3 模型作图根下的路径。"""
    return os.path.join(MODEL_FIG, *parts)


def res(*parts):
    """分析中间物根下的路径。"""
    return os.path.join(RES, *parts)


def train(*parts):
    """训练结果根下的路径。"""
    return os.path.join(TRAIN, *parts)


def pick(*candidates):
    """返回第一个存在的候选路径；都不存在则返回最后一个（便于"新位置优先、旧位置回退"）。"""
    for p in candidates[:-1]:
        if p and os.path.exists(p):
            return p
    return candidates[-1]


def ensure(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------- 排错
def show(stream=None):
    """打印当前生效的路径配置。"""
    stream = stream or sys.stdout
    print('[gyo_paths] 当前生效配置', file=stream)
    for k, v, is_path in (('BASE', BASE, 1), ('QUANT(阶段1/2)', QUANT, 1),
                          ('MP4(Step B 输入)', MP4, 1),
                          ('MODEL_FIG(阶段3)', MODEL_FIG, 1), ('FIG(阶段4)', FIG, 1),
                          ('FREQ(阶段5)', FREQ, 1), ('SUPP(阶段6)', SUPP, 1),
                          ('RES(分析中间物)', RES, 1), ('TRAIN', TRAIN, 1),
                          ('TRAIN_TAG(现行模型)', TRAIN_TAG, 0),
                          ('IMGSZ(推理尺寸)', IMGSZ, 0),
                          ('WEIGHTS', WEIGHTS, 1), ('TRAIN_CSV', TRAIN_CSV, 1),
                          ('DATA_YAML', DATA_YAML, 1), ('VIDEO_SRC', VIDEO_SRC, 1)):
        # 非路径项（TRAIN_TAG / IMGSZ）不做存在性标注
        mark = ('   [不存在]' if (is_path and not os.path.exists(v)) else '')
        print('   %-20s = %s%s' % (k, v, mark), file=stream)


if __name__ == '__main__':
    show()
