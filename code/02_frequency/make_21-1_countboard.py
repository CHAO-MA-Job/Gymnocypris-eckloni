# -*- coding: utf-8 -*-
"""Human agreement for fish 21-1: compare the automated counts with the manual counts.

The event detection itself comes from postproc.py; this script aligns the counts with the human
reference and, when the recording is available, renders a side-by-side video that shows the
detected states together with the running counts (one panel per body part).

Reference : tables/human_validation_21-1.xlsx, recounted from the original recording
Windows   : 180-470 s (30 windows of 10 s)
Metrics   : relative error per window, averaged as MAPE, with AR = 100 - MAPE; the correlation r
            between the model and the human series. Windows with a human count of zero are
            ignored.
Output    : tables/21-1_countboard_data.xlsx (model versus human, per window) and the video.
            A module flag skips the rendering and only refreshes the table, which avoids
            re-encoding the 8,700 frames of the segment."""
import os, sys, math, bisect
import numpy as np
import pandas as pd
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postproc as pp   # counting logic comes from postproc.py; this script must not duplicate it

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # unified path entry point

SRC = P.QUANT                  # step 1 output root (contains MP4/<recording>/)
RES = P.RES                    # human reference table and countboard outputs
SRC_VIDEO = os.path.join(SRC, "MP4", "21-1", "21-1.mp4")
OUT_VIDEO = os.path.join(RES, "21-1_countboard.mp4")
OUT_XLSX = os.path.join(RES, "21-1_countboard_data.xlsx")

FPS = 30
SEG0, SEG1 = 180, 470
F0, F1 = SEG0 * FPS, SEG1 * FPS
WIN = 10
PANEL_W = 760
# set to 1 to refresh only the comparison table and skip rendering the 8,700 frames
SKIP_VIDEO = os.environ.get("COUNTBOARD_SKIP_VIDEO") == "1"


# ---------- event detection comes from postproc.py and is not reimplemented here ----------
def load_events(part):
    """Event anchor frames of one body part, read from the 21-1 table (see postproc.PARTS)."""
    d = pd.read_excel(pp.src_path(part), sheet_name="21-1")
    return pp.detect_events(d, part)


g_ev = load_events("operculum")
p_ev = load_events("pectoral")
c_ev = load_events("caudal")


def per_window(events):
    return {t: bisect.bisect_right(events, (t + WIN) * FPS - 1) -
               bisect.bisect_left(events, t * FPS)
            for t in range(SEG0, SEG1 + 1, WIN)}


def disp(events, fn, wsec):
    """Events of the current 10 s window up to the present frame (reset at the window start)."""
    return bisect.bisect_right(events, fn) - bisect.bisect_left(events, wsec * FPS)


def disp_final(events, fn, wsec, total):
    """Last second of a window: the first half holds the final count and the second half resets early; otherwise the count accumulates live."""
    lf = fn - wsec * FPS
    if lf >= 270:                 # last second
        return total if lf < 285 else 0   # first 15 frames hold the final count, last 15 frames reset early
    return disp(events, fn, wsec)


gw, pw, cw = per_window(g_ev), per_window(p_ev), per_window(c_ev)
windows = list(range(SEG0, SEG1 + 1, WIN))

# ---- agreement: window counts versus the merged rate table and the human reference ----
def load_counts(fname, col):
    # the merged rate table lives in the work root; the older location is a fallback
    path = P.pick(P.q(fname), os.path.join(RES, fname))
    d = pd.read_excel(path, sheet_name="21-1").rename(columns={"start_time_s": "t"})
    return {int(t): float(c) for t, c in zip(d["t"], d[col])}

gill = load_counts("respiration.xlsx", "respiration")
pect = load_counts("pectoral_rate.xlsx", "pectoral_rate")
caudal = load_counts("caudal_rate.xlsx", "caudal_rate")
# human reference: the copy in tables/ is authoritative; an older copy is a fallback
HV_XLSX = P.pick(P.q("21-1_human.xlsx"), os.path.join(RES, "21-1_human.xlsx"))
hv = pd.read_excel(HV_XLSX)
_hv = {int(t): r for t, r in zip(hv["start_time_s"], hv.index)}   # time in seconds -> row index


def hv_col(col):
    """Align with the human table over the windows of 180-470 s; missing times become NaN."""
    return np.array([float(hv.at[_hv[t], col]) if t in _hv else np.nan for t in windows])


def mape(model, human):
    """MAPE = mean(|model-human|/human)*100  over the windows; zero or missing human counts are ignored."""
    m = np.asarray(model, float)
    h = np.asarray(human, float)
    ok = ~(np.isnan(m) | np.isnan(h)) & (h != 0)
    return 100.0 * np.mean(np.abs(m[ok] - h[ok]) / h[ok])


m_g = [gill.get(t) for t in windows]; m_p = [pect.get(t) for t in windows]; m_c = [caudal.get(t) for t in windows]
e_g = [gw[t] for t in windows]; e_p = [pw[t] for t in windows]; e_c = [cw[t] for t in windows]
h_g, h_p, h_c = hv_col("operculum_human"), hv_col("pectoral_human"), hv_col("caudal_human")
print("window counts versus merged rate table  MAE:",
      round(float(np.mean(np.abs(np.array(e_g) - np.array(m_g)))), 3),
      round(float(np.mean(np.abs(np.array(e_p) - np.array(m_p)))), 3),
      round(float(np.mean(np.abs(np.array(e_c) - np.array(m_c)))), 3))

print("model versus human (reference = %s):" % os.path.basename(HV_XLSX))
for _cn, _m, _h in (("operculum", m_g, h_g), ("pectoral", m_p, h_p), ("caudal", m_c, h_c)):
    _mm = np.asarray(_m, float); _hh = np.asarray(_h, float)
    _ok = ~(np.isnan(_mm) | np.isnan(_hh)) & (_hh != 0)
    _r = float(np.corrcoef(_mm[_ok], _hh[_ok])[0, 1]) if _ok.sum() > 2 else float("nan")
    print("   %-10s MAE=%5.2f  MAPE=%6.2f%%  AR=%6.2f%%  r=%+.2f  n=%d"
          % (_cn, np.mean(np.abs(_mm[_ok] - _hh[_ok])), mape(_mm, _hh),
             100 - mape(_mm, _hh), _r, int(_ok.sum())))

# ---- render the video (skipped when the recording is unavailable) ----
if SKIP_VIDEO:
    cap = out = None
    W = H = 0
else:
    cap = cv2.VideoCapture(SRC_VIDEO)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not cap.isOpened() or W == 0 or H == 0:
        print(f"[WARN] source recording unavailable: {SRC_VIDEO} -> rendering skipped; comparison table written")
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

    # full time axis
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
    print("[SKIP] rendering skipped; the comparison table is still written.")
else:
    n = 0
    for fn in range(F0, F1):
        ret, frame = cap.read()
        if not ret:
            break
        out.write(build_canvas(frame, fn))
        n += 1
        if n % 1000 == 0:
            print(f"  processed {n}/{F1 - F0} frames ...")
    cap.release(); out.release()
    print(f"[OK] recording: {OUT_VIDEO}  frames={n}  size={W + PANEL_W}x{H}  duration={n / FPS:.1f}s")

pd.DataFrame({
    "start_time_s": windows,
    "operculum_model": e_g, "pectoral_model": e_p, "caudal_model": e_c,
    "operculum_human": h_g, "pectoral_human": h_p, "caudal_human": h_c,
}).to_excel(OUT_XLSX, index=False)
print(f"[OK] comparison table: {OUT_XLSX}")
