# -*- coding: utf-8 -*-
"""
make_21-1_countboard.py —— 21-1 视频 三部位计数板 (v3: 动态, 真实切换才+1)
==========================================================================
调整点:
  1) 不遮挡视频: 画布加宽, 左侧完整 1920x1080 原视频, 右侧新增面板.
  2) 界面英文: Operculum / Pectoral fin / Caudal fin.
  3) 完整时间轴: 180-470s 整条; 当前 10s 实线高亮, 前后虚线, 青色播放头.
  4) 动态计数: 数字"随视频里状态切换"才 +1 —— 用逐帧检测事件帧,
     取当前 10s 窗口内(帧号<=当前帧)的事件数; 窗口起点归零, 窗口末达到该窗总次数.
输入  : 视频 + P.QUANT/{2_鳃盖,3_胸鳍,4_尾鳍}.xlsx (sheet "21℃-1")
        人眼真值: **P.QUANT/21-1_人眼.xlsx** ← 2026-09-15 裁定为**唯一权威**
                  （分析中间物 P.RES 下的同名文件作兼容回退，但**不要以它为准** ——
                    实测两者仅「胸鳍_人眼」列不同：权威 10.800 vs 旧 13.467）
                  旧 视频21-1验证.xlsx 的「人眼识别」列已弃用
输出  : P.RES/21-1_countboard.mp4
        P.RES/21-1_countboard_data.xlsx (逐窗 模型 vs 人眼)
"""
import os, sys, math, bisect
import numpy as np
import pandas as pd
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postproc as pp   # 统一后处理（逐部位最优逻辑）；本脚本禁止自行复制检测逻辑

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口

SRC = P.QUANT                  # 阶段1 产物根（含 MP4/<视频>/）
RES = P.RES                    # 分析中间物：21-1_人眼.xlsx 与 countboard 产物
SRC_VIDEO = os.path.join(SRC, "MP4", "21-1", "21-1.mp4")
OUT_VIDEO = os.path.join(RES, "21-1_countboard.mp4")
OUT_XLSX = os.path.join(RES, "21-1_countboard_data.xlsx")

FPS = 30
SEG0, SEG1 = 180, 470
F0, F1 = SEG0 * FPS, SEG1 * FPS
WIN = 10
PANEL_W = 760
# 仅刷新对照表(21-1_countboard_data.xlsx)时设为 1，跳过 8700 帧视频渲染
SKIP_VIDEO = os.environ.get("COUNTBOARD_SKIP_VIDEO") == "1"


# ---------- 事件检测：统一走 postproc（逐部位最优逻辑），本脚本不再自行实现 ----------
def load_events(part):
    """按部位读 21℃-1 表并返回事件锚点帧；逻辑/参数见 postproc.PARTS。"""
    d = pd.read_excel(pp.src_path(part), sheet_name="21℃-1")
    return pp.detect_events(d, part)


g_ev = load_events("operculum")
p_ev = load_events("pectoral")
c_ev = load_events("caudal")


def per_window(events):
    return {t: bisect.bisect_right(events, (t + WIN) * FPS - 1) -
               bisect.bisect_left(events, t * FPS)
            for t in range(SEG0, SEG1 + 1, WIN)}


def disp(events, fn, wsec):
    """当前 10s 窗口内、帧号<=当前帧的事件数 (窗口起点归零)。"""
    return bisect.bisect_right(events, fn) - bisect.bisect_left(events, wsec * FPS)


def disp_final(events, fn, wsec, total):
    """窗口最后一秒(30帧): 前15帧定格显示最终总数, 后15帧提前归零; 其余实时累计。"""
    lf = fn - wsec * FPS
    if lf >= 270:                 # 最后一秒
        return total if lf < 285 else 0   # 前15帧定格 / 后15帧归零
    return disp(events, fn, wsec)


gw, pw, cw = per_window(g_ev), per_window(p_ev), per_window(c_ev)
windows = list(range(SEG0, SEG1 + 1, WIN))

# ---- 一致性核对: 事件法逐窗 vs 频率合并表(模型) vs 人眼真值表 ----
def load_counts(fname, col):
    # 频率合并表已归口到 P.QUANT（阶段2）；旧位置 P.RES 作兼容回退
    path = P.pick(P.q(fname), os.path.join(RES, fname))
    d = pd.read_excel(path, sheet_name="21℃-1").rename(columns={"开始时间（秒）": "t"})
    return {int(t): float(c) for t, c in zip(d["t"], d[col])}

gill = load_counts("呼吸频率.xlsx", "呼吸频率")
pect = load_counts("胸鳍摆动频率.xlsx", "胸鳍摆动频率")
caudal = load_counts("尾鳍摆动频率.xlsx", "尾鳍摆动频率")
# 人眼真值：**以数据根那份为准**（2026-09-15 裁定）；分析中间物为兼容回退
HV_XLSX = P.pick(P.q("21-1_人眼.xlsx"), os.path.join(RES, "21-1_人眼.xlsx"))
hv = pd.read_excel(HV_XLSX)
_hv = {int(t): r for t, r in zip(hv["开始时间（秒）"], hv.index)}   # 时间(s) -> 行号


def hv_col(col):
    """按 windows(180-470) 对齐人眼表；缺该时间给 NaN。"""
    return np.array([float(hv.at[_hv[t], col]) if t in _hv else np.nan for t in windows])


def mape(model, human):
    """MAPE = mean(|模型-人眼|/人眼)*100（逐窗相对误差再平均）；忽略人眼为 0 / 缺失的窗。"""
    m = np.asarray(model, float)
    h = np.asarray(human, float)
    ok = ~(np.isnan(m) | np.isnan(h)) & (h != 0)
    return 100.0 * np.mean(np.abs(m[ok] - h[ok]) / h[ok])


m_g = [gill.get(t) for t in windows]; m_p = [pect.get(t) for t in windows]; m_c = [caudal.get(t) for t in windows]
e_g = [gw[t] for t in windows]; e_p = [pw[t] for t in windows]; e_c = [cw[t] for t in windows]
h_g, h_p, h_c = hv_col("鳃盖_人眼"), hv_col("胸鳍_人眼"), hv_col("尾鳍_人眼")
print("事件法  vs 频率合并表(模型)  MAE:",
      round(float(np.mean(np.abs(np.array(e_g) - np.array(m_g)))), 3),
      round(float(np.mean(np.abs(np.array(e_p) - np.array(m_p)))), 3),
      round(float(np.mean(np.abs(np.array(e_c) - np.array(m_c)))), 3))

print("模型 vs 人眼（人眼源 = %s）:" % os.path.basename(HV_XLSX))
for _cn, _m, _h in (("operculum", m_g, h_g), ("pectoral", m_p, h_p), ("caudal", m_c, h_c)):
    _mm = np.asarray(_m, float); _hh = np.asarray(_h, float)
    _ok = ~(np.isnan(_mm) | np.isnan(_hh)) & (_hh != 0)
    _r = float(np.corrcoef(_mm[_ok], _hh[_ok])[0, 1]) if _ok.sum() > 2 else float("nan")
    print("   %-10s MAE=%5.2f  MAPE=%6.2f%%  AR=%6.2f%%  r=%+.2f  n=%d"
          % (_cn, np.mean(np.abs(_mm[_ok] - _hh[_ok])), mape(_mm, _hh),
             100 - mape(_mm, _hh), _r, int(_ok.sum())))

# ---- 视频合成（无源视频时跳过，避免 VideoWriter 拿到 0 尺寸）----
if SKIP_VIDEO:
    cap = out = None
    W = H = 0
else:
    cap = cv2.VideoCapture(SRC_VIDEO)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not cap.isOpened() or W == 0 or H == 0:
        print(f"[WARN] 源视频不可用: {SRC_VIDEO} -> 跳过视频合成，仅输出对照表")
        cap = out = None
        W = H = 0
    else:
        cap.set(cv2.CAP_PROP_POS_FRAMES, F0 - 1)
        out = cv2.VideoWriter(OUT_VIDEO, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W + PANEL_W, H))


def dashed_line(img, p1, p2, color, thickness=2, dash=16, gap=12):
    x1, y1, x2, y2 = *p1, *p2
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist == 0:
        return
    nx, ny = (x2 - x1) / dist, (y2 - y1) / dist
    drawn = 0.0
    while drawn < dist:
        s, e = drawn, min(drawn + dash, dist)
        cv2.line(img, (int(x1 + nx * s), int(y1 + ny * s)),
                 (int(x1 + nx * e), int(y1 + ny * e)), color, thickness)
        drawn += dash + gap


def build_canvas(frame, fn):
    canvas = np.zeros((H, W + PANEL_W, 3), dtype=np.uint8)
    canvas[:, :W] = frame
    cv2.rectangle(canvas, (W, 0), (W + PANEL_W, H), (18, 18, 18), -1)
    px = W + 50
    t_abs = fn / FPS
    wsec = int(t_abs // WIN) * WIN
    gnow, pnow, cnow = (disp_final(g_ev, fn, wsec, gw[wsec]),
                        disp_final(p_ev, fn, wsec, pw[wsec]),
                        disp_final(c_ev, fn, wsec, cw[wsec]))

    cv2.putText(canvas, "Fish 21-1  Movement Count Board", (px, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.95, (255, 255, 255), 2)
    cv2.putText(canvas, f"Current window: {wsec}-{wsec + WIN} s", (px, 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (210, 210, 210), 2)
    cv2.putText(canvas, f"Operculum:    {gnow}  beats / 10s", (px, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (120, 230, 140), 2)
    cv2.putText(canvas, f"Pectoral fin: {pnow}  beats / 10s", (px, 295),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (130, 190, 255), 2)
    cv2.putText(canvas, f"Caudal fin:   {cnow}  beats / 10s", (px, 370),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 205, 130), 2)
    cv2.putText(canvas, "(ticks up at each real state switch)", (px, 430),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (170, 170, 170), 1)

    # 完整时间轴
    ax_y = H - 130
    xL, xR = W + 60, W + PANEL_W - 60
    span = xR - xL
    tx = lambda t: int(xL + (t - SEG0) / (SEG1 - SEG0) * span)
    cv2.putText(canvas, "Full timeline (180-470 s)", (px, ax_y - 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (220, 220, 220), 2)
    dashed_line(canvas, (xL, ax_y), (xR, ax_y), (120, 120, 120), thickness=2)
    cv2.line(canvas, (tx(wsec), ax_y - 14), (tx(wsec + WIN), ax_y + 14),
             (0, 220, 255), thickness=10)
    cv2.line(canvas, (tx(t_abs), ax_y - 34), (tx(t_abs), ax_y + 34), (0, 255, 255), thickness=3)
    cv2.circle(canvas, (tx(t_abs), ax_y - 34), 5, (0, 255, 255), -1)
    for t in range(SEG0, SEG1 + 1, 30):
        cv2.line(canvas, (tx(t), ax_y - 8), (tx(t), ax_y + 8), (200, 200, 200), 2)
        cv2.putText(canvas, str(t), (tx(t) - 18, ax_y + 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
    return canvas


if cap is None:
    print("[SKIP] 视频合成已跳过；对照表仍会更新。")
else:
    n = 0
    for fn in range(F0, F1):
        ret, frame = cap.read()
        if not ret:
            break
        out.write(build_canvas(frame, fn))
        n += 1
        if n % 1000 == 0:
            print(f"  已处理 {n}/{F1 - F0} 帧 ...")
    cap.release(); out.release()
    print(f"[OK] 视频: {OUT_VIDEO}  帧={n} 尺寸={W + PANEL_W}x{H} 时长={n / FPS:.1f}s")

pd.DataFrame({
    "开始时间（秒）": windows,
    "鳃盖_模型": e_g, "胸鳍_模型": e_p, "尾鳍_模型": e_c,
    "鳃盖_人眼": h_g, "胸鳍_人眼": h_p, "尾鳍_人眼": h_c,
}).to_excel(OUT_XLSX, index=False)
print(f"[OK] 对照表: {OUT_XLSX}")
