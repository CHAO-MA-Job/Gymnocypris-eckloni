# -*- coding: utf-8 -*-
"""
postproc.py —— 三部位行为频率【唯一】后处理实现（定稿：零调参；smooth_K=1，2026-09-15 起 dedupe=True）
==========================================================================
定位
----
本模块是本项目计数后处理的**唯一**实现：本目录 `类别1,2 / 类别3,4 / 类别5,6,7`、
`compute_respiration/pectoral/caudal.py`、`make_21-1_countboard.py` 全部 import 它，
禁止各自复制逻辑（避免口径漂移）。

⚠ 使用范围（2026-09-15 裁定）：**本模块产出为「辅助描述量」，不作结论**
------------------------------------------------------------------
one-way ANOVA（n = 3/温度）：胸鳍 p = 0.34、尾鳍 p = 0.25 —— **温度间无差异**；
仅鳃盖 p = 0.015。且「口径漂移 ÷ 组内 SD」在多个温度达 200–750%，
逐温度绝对值由流水线决定而非生物学决定；人眼真值仅 n = 1 尾。
⇒ **频率不写入结论、不作显著性声明**；引用时须注明为描述性指标。
   完整依据见 `README_后处理定稿.md` §0.6 与 `总览.md` §10-10。
   （注：`cost_ratio` = 鳃盖频率/速度 属频率派生量，其归属尚未裁定。）

口径决定（2026-09-14）：**零调参，采用原逻辑**
------------------------------------------------
曾尝试用「逐帧去重 + 多数表决 K + 进入态/不应期」做时序平滑，并以人眼标注标定"逐部位最优"。
**经审查不予采用**，理由：
  1) 参数是对**单尾鱼**误差的拟合，无先验依据 → 有"凑数"之嫌；
  2) **决定性证据（2026-09-14 复核）**：人眼真值改用重计数的 `21-1_人眼.xlsx` 后，
     被旧人眼值选出的"最优"（去重 + K=5 + 进入态/不应期 20 帧）**反而变成最差**：
     胸鳍 AR 由原逻辑 **73.47% 掉到 53.71%**、MAE 3.30→6.57 → **典型过拟合**，
     真值一旦修正即失效；
  3) 同类平滑对**鳃盖**始终有害（AR 95.94%→89.22%，r 0.72→0.20），须按部位开关参数 → 选择性调参。
故定稿为**原逻辑、零调参**：三部位统一 `dedupe=False / smooth_K=1`，阈值沿用既有约定。
时序平滑的全部变体仍保留在本模块内（改 `PARTS` 即可一键复现），**仅用于敏感性分析**，
不作主口径；完整扫描表见 `README_后处理定稿.md` §3。

口径修订（2026-09-15）：`dedupe=True` 且 `ffill=False`（`smooth_K` 仍为 1）
----------------------------------------------------------------------
两处改动**分开评价**，不要混为一谈。

【改动 1】`dedupe=True` —— **正确性要求**
  触发：上游量化改用 **TTA（`augment=True`）** 推理（数据根
  `04_Outputs/模型量化数据640_G0_TTA`）。TTA 对**同一帧给出多个框**，
  `dedupe=False` 会把"帧内多框"当作独立状态变化 → **胸鳍事件严重过计**。
  实测（21-1，窗 180–470 s，n=30，人眼真值同上）：

    part         dedupe    AR        r      模型均值 / 人眼
    operculum    False    92.95%   +0.63     19.83 / 18.87
    operculum    True     94.22%   +0.35     18.27 / 18.87
    pectoral     False    15.59%   +0.36     19.13 / 10.80   ← 过计 +77%，不可用
    pectoral     True     81.16%   +0.78     11.90 / 10.80
    caudal       False    82.55%   +0.83      7.97 /  7.53
    caudal       True     82.74%   +0.84      7.93 /  7.53

【改动 2】`ffill=False` —— **去伪影**
  旧 `build_signal(dedupe=True)` 顺带把未检出帧**前向填充**成稠密序列。
  前向填充会**发明数据**：缺口内被填成同一状态，使 `swing`（尾鳍）满足
  "连续两帧同态"而虚增事件。
  **对照实验（关键）**：拿**同一份 960 数据**（覆盖率完全相同）只切换 ffill，
  23℃ 尾鳍由 **6.36 → 7.87（+24%）** —— 数据未变，纯属填充制造的事件。
  故 `ffill` 独立关掉；`dedupe` 保留。

【改动 3】两者对频率的净影响（逐温度均值，3 尾）
  23℃ 尾鳍：旧 6.34 → 最终 **8.12（+28%）**。分解后：
    · 数据根 960→TTA（覆盖率 58%→77%，**帧被真正找回**）：6.34 → 8.12 ← 真实
    · 前向填充（伪影）：+0.9，已去除
  其余温度三部位变化 < 5%（覆盖率本就 ~100%，无缺口可填）。
  ⚠ 但 25℃ 鳃盖由 21.35 降到 12.10（−43%）、19℃ 鳃盖 10.59→7.33（−31%）：
  这是**去重**的效果（960 数据同样存在同帧多框），非填充。

关键澄清：2026-09-14 被否决的是「**去重 + K=5 + 进入态/不应期 20 帧**」这一
**组合**（对单尾鱼过拟合），**并非"去重"本身**。同一 `dedupe` 开关在旧 960
数据上并不劣化（鳃盖 95.9→94.8、胸鳍 73.5→78.3、尾鳍 79.6→78.1）。
故本次属**口径修正**（一帧只有一个状态 + 不发明数据），非调参。

主口径逻辑（PARTS）
-------------------
  operculum 鳃盖 (1/2)  ：周期法 cycle（a→b→a），中间态连续 >= min_dur(2) 帧
  pectoral  胸鳍 (3/4)  ：周期法 cycle（3→4→3），中间态连续 >= min_dur(2) 帧
  caudal    尾鳍 (5/6/7)：同态摆动 swing（连续两帧同为 5 或 7）+ 间隔 >= min_gap(30) 帧
均为「逐行游程压缩」口径（与手稿既有脚本逐行一致）；`fps=30`，每 300 帧(10 s) 窗计数。

人眼验证结果（21-1，主口径）
----------------------------
人眼真值源：**`P.QUANT/21-1_人眼.xlsx`**（2026-09-15 裁定为**唯一权威**，按原视频重新计数）。
⚠ `P.RES`（`03_分析结果`）下的同名副本**仅「胸鳍_人眼」列不同**（副本 13.467 vs 权威 10.800），
  以它为准会把胸鳍 AR 误算为 75.01%（正确值 **81.16%**）。鳃盖/尾鳍两列两版一致。
⚠ 旧 `99_投稿所用_文章文件/图片/视频21-1验证.xlsx` 的「人眼识别」列**已弃用**（胸鳍值 8.94 系统性偏低）。
窗 = 180–470 s（30 窗）；MAPE = mean(|模型-人眼|/人眼)×100；AR = 100 − MAPE。

**当前（2026-09-15 起）：模型 = `G0_yolo11n_640`@640+TTA，数据根 = `02_模型量化数据640_G0_TTA`，`dedupe=True/ffill=False`**

  part        MAE    MAPE      AR        r     模型均值 / 人眼   偏差
  operculum   1.13    5.78%   94.22%   +0.35    18.27 / 18.87    −3%
  pectoral    1.77   18.84%   81.16%   +0.78    11.90 / 10.80   +10%
  caudal      1.00   17.26%   82.74%   +0.84     7.93 /  7.53    +5%

⇒ **三部位一致性均可接受**：鳃盖 94.2% > 尾鳍 82.7% > 胸鳍 81.2%。
   **最弱项为胸鳍**（AR 最低、MAE 最高、类别可分性最差 0.78/0.83）。
   尾鳍按 **MAE 计为最准（1.00）**；其 AR 不最高的原因是人眼基数小（7.53）→ MAPE 被放大。

⚠ 真值源**以数据根那份为准**：`P.QUANT/21-1_人眼.xlsx`。与 `P.RES` 下同名副本的差异（已核对）：
   胸鳍_人眼 17/30 窗不同（权威 10.800 / 副本 13.467）、尾鳍_人眼 2/30 窗不同（7.533 / 7.367）；
   鳃盖与全部「模型」列一致。用副本会得到胸鳍 75.01%、尾鳍 77.38% 的**偏低**结果。
   `make_21-1_countboard.py` 已改为优先读数据根那份。

历史（2026-09-14，旧 960 量化 + `dedupe=False`）：AR 95.94 / 73.47 / 79.55%，
r +0.72 / +0.47 / +0.86。⚠ 该组数字随真值源与口径变更而变，**引用前须与当前复现值核对**。
"""
import os
import re
import sys
import bisect

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源）

# ---------------------------------------------------------------- 常量
FPS = 30
INTERVAL = 10          # 每 10 s 统计一次

# 阶段1/2 数据根：由 gyo_paths 统一解析（环境变量 GYO_QUANT 可整体切换到新量化产物）
SRC_DIR = P.QUANT

# ---------------------------------------------------------------- 主口径参数（2026-09-15 修订：dedupe=True, ffill=False）
# 说明：dedupe=True / ffill=False / smooth_K=1
#       · 去重：每帧只取最高置信度框 —— TTA 下每帧多框，不去重会把"帧内多框"
#         误判为状态变化（胸鳍 AR 由 75% 崩到 43%）。
#       · 不填充：未检出帧**不**用前一帧状态填 —— 填充会发明数据、虚增 swing 事件
#         （同数据同覆盖率下，23℃ 尾鳍 6.36 → 7.87，+24% 纯伪影）。
#       仅保留手稿既有的游程压缩与阈值（min_dur=2 帧 / min_gap=30 帧）。
#       时序平滑变体（smooth_K>1、mode='entry'）保留供敏感性分析。
PARTS = {
    "operculum": dict(
        file="2_鳃盖.xlsx", col="呼吸频率", title="呼吸频率",
        mode="cycle", states=(1, 2),
        dedupe=True, ffill=False, smooth_K=1, min_dur=2,
    ),
    "pectoral": dict(
        file="3_胸鳍.xlsx", col="胸鳍摆动频率", title="胸鳍摆动频率",
        mode="cycle", states=(3, 4),
        dedupe=True, ffill=False, smooth_K=1, min_dur=2,
    ),
    "caudal": dict(
        file="4_尾鳍.xlsx", col="尾鳍摆动频率", title="尾鳍摆动频率",
        mode="swing", majority_states=(5, 6, 7), swing_states=(5, 7),
        dedupe=True, ffill=False, smooth_K=1, min_gap=30,
    ),
}

# 期望 sheet 名，如 "21℃-1"
SHEET_RE = re.compile(r"(\d+)\s*℃\s*-?\s*(\d+)")


# ================================================================ 预处理
def build_signal(df, dedupe=True, ffill=False, conf_col="置信度"):
    """把逐框表 -> (帧号数组, 类别数组)。

    dedupe=True : 每帧只保留置信度最高的框（TTA 下同帧多框必须去重）；
    ffill=True  : 再把未检出帧用前一帧状态**前向填充**成稠密序列。
                  ⚠ 默认 False —— 前向填充会**发明数据**：缺口内被填成同一状态，
                  使 swing（尾鳍）满足"连续两帧同态"而虚增事件。
                  实测（23℃ 尾鳍，960 数据、覆盖率完全相同）：
                  ffill=False = 6.36 → ffill=True = 7.87（+24% 纯伪影）。
    dedupe=False: 保留原始逐行序列（与旧脚本行为一致，仅用于对照）。
    """
    d = df.sort_values("帧编号").reset_index(drop=True)
    if dedupe:
        if conf_col in d.columns:
            d = d.sort_values(conf_col).groupby("帧编号", as_index=False).last()
            d = d.sort_values("帧编号").reset_index(drop=True)
        if not ffill:
            return d["帧编号"].to_numpy(int), d["类别"].to_numpy(int)
        f = d["帧编号"].to_numpy(int)
        grid = np.arange(f.min(), f.max() + 1)
        c = d.set_index("帧编号")["类别"].reindex(grid).ffill().bfill()
        return grid.astype(int), c.to_numpy(int)
    return (d["帧编号"].to_numpy(int), d["类别"].to_numpy(int))


def majority(classes, states, K):
    """滑动窗多数表决（K 为奇数），仅作用于类别序列，不改帧号。"""
    if not K or K <= 1:
        return np.asarray(classes, int)
    sig = np.asarray(classes, int)
    h = K // 2
    n = len(sig)
    lo = np.maximum(0, np.arange(n) - h)
    hi = np.minimum(n, np.arange(n) + h + 1)
    counts = []
    for s in states:
        cs = np.concatenate([[0], np.cumsum((sig == s).astype(float))])
        counts.append(cs[hi] - cs[lo])
    return np.asarray(states, int)[np.argmax(np.stack(counts), axis=0)].astype(int)


def compress(frames, classes):
    """压缩为「连续同类游程」-> (游程类别, 游程起始帧, 游程持续帧数)。"""
    runs, rf, rd = [], [], []
    prev, cnt, sf = None, 0, None
    for f, c in zip(frames, classes):
        if c == prev:
            cnt += 1
        else:
            if prev is not None:
                runs.append(prev); rf.append(sf); rd.append(cnt)
            prev, cnt, sf = c, 1, f
    if prev is not None:
        runs.append(prev); rf.append(sf); rd.append(cnt)
    return runs, rf, rd


# ================================================================ 事件检测
def events_cycle(frames, classes, a, b, min_dur):
    """周期法：a→b→a（或 b→a→b），中间游程持续 >= min_dur 记一次。返回锚点帧。"""
    runs, rf, rd = compress(frames, classes)
    ev = []
    if not runs:
        return ev
    start = runs[0]
    i = 0
    while i < len(runs) - 2:
        if (start == a and runs[i] == a and runs[i + 1] == b
                and rd[i + 1] >= min_dur and runs[i + 2] == a):
            ev.append(rf[i]); i += 2
        elif (start == b and runs[i] == b and runs[i + 1] == a
              and rd[i + 1] >= min_dur and runs[i + 2] == b):
            ev.append(rf[i]); i += 2
        else:
            i += 1
    return sorted(ev)


def events_entry(frames, classes, a, b, refractory):
    """进入态事件：由 a 转入 b 的帧；与上一事件间隔 >= refractory 帧才计数。"""
    ev, last = [], -10 ** 9
    for i in range(1, len(classes)):
        if classes[i - 1] == a and classes[i] == b:
            f = int(frames[i])
            if f - last >= refractory:
                ev.append(f); last = f
    return ev


def events_swing(frames, classes, states, min_gap):
    """同态摆动：连续两帧同为 states 中某态（中间态不计），间隔 >= min_gap 帧去重。"""
    ev, last = [], -min_gap
    for i in range(len(classes) - 1):
        if classes[i] in states and classes[i + 1] == classes[i]:
            f = int(frames[i])
            if f - last >= min_gap:
                ev.append(f); last = f
    return ev


def detect_events(df, part, cfg=None):
    """按部位配置，从逐框表得到事件锚点帧列表。"""
    cfg = cfg or PARTS[part]
    frames, classes = build_signal(df, cfg.get("dedupe", True), cfg.get("ffill", False))
    maj_states = cfg.get("majority_states") or cfg.get("states")
    classes = majority(classes, maj_states, cfg.get("smooth_K", 1))
    mode = cfg["mode"]
    if mode == "cycle":
        a, b = cfg["states"]
        return events_cycle(frames, classes, a, b, cfg.get("min_dur", 2))
    if mode == "entry":
        a, b = cfg["states"]
        return events_entry(frames, classes, a, b, cfg.get("refractory", 20))
    if mode == "swing":
        return events_swing(frames, classes, cfg["swing_states"], cfg.get("min_gap", 30))
    raise ValueError(f"未知 mode: {mode}")


# ================================================================ 逐 10 s 统计
def count_windows(events, max_frame, fps=FPS, interval=INTERVAL):
    """返回 [(时间段编号, 开始时间秒, 次数), ...]，从 0 到末帧。"""
    events = sorted(events)
    rows = []
    for t in range(0, int(max_frame) // fps + 1, interval):
        c = (bisect.bisect_right(events, (t + interval) * fps - 1)
             - bisect.bisect_left(events, t * fps))
        rows.append((t // interval, t, int(c)))
    return rows


def compute(df, part, cfg=None):
    """一步到位：逐框表 -> 频次表（列：时间段编号, 开始时间（秒）, <频率列>）。"""
    cfg = cfg or PARTS[part]
    frames, classes = build_signal(df, cfg.get("dedupe", True), cfg.get("ffill", False))
    ev = detect_events(df, part, cfg)
    rows = count_windows(ev, int(frames[-1]) if len(frames) else 0)
    return pd.DataFrame(rows, columns=["时间段编号", "开始时间（秒）", cfg["col"]]), ev


# ================================================================ I/O 便捷函数
# 部位 -> 中文子目录名（阶段2 频率产物归口到 SRC_DIR 下，与阶段1 表同根）
PART_CN = {"operculum": "呼吸频率", "pectoral": "胸鳍摆动频率", "caudal": "尾鳍摆动频率"}


def part_out_dir(part):
    """阶段2 输出根：<阶段1/2 数据根>/<中文部位名>/（其下 统计/ 与 图/ 两个子目录）。"""
    return os.path.join(SRC_DIR, PART_CN[part])


def src_path(part):
    return os.path.join(SRC_DIR, PARTS[part]["file"])


def iter_sheets(part):
    """(sheet 名, DataFrame) —— 只返回形如 '21℃-1' 的有效 sheet。"""
    xl = pd.ExcelFile(src_path(part))
    for sh in xl.sheet_names:
        if SHEET_RE.search(str(sh)):
            yield sh, xl.parse(sh)


def fish_of(sheet):
    m = SHEET_RE.search(str(sheet))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)
