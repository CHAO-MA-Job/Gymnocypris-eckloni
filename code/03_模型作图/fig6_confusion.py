"""Fig6 (model performance) — 现行模型实测混淆矩阵。

（本脚本由 fig5_confusion.py 更名而来：图号从 Fig5「人眼验证」中拆出，
 统一归入 Fig6「模型性能」，与训练曲线同目录。）

- Model : `P.WEIGHTS` —— **现行 `G0_yolo11n_640`**（2026-09-15 统一裁定）
- Data  : 02_process_data/VOCdevkit  (val split, 755 images)
- imgsz : `P.IMGSZ`（默认 **640**，与 G0 训练尺寸一致）
- 配色  : 项目橙红渐变 `OrRd`（统一到项目"橙灰红"体系）
- 标签  : 保持数字 1–8（不做行为语义命名，按用户确认）
- 主图  : 8×8（去掉 background 行/列，正文用）
- 补充  : 9×9 含 background（`*_withbg.png`，可放补充材料）
- 标题  : **只显示主标题**（"Normalized / Raw Counts Confusion Matrix"），
          模型、数据口径等限定条件一律写进图注，不进图内

⚠ 口径声明（写进图注）：
  1) `best.pt` 是最优 fitness 轮，其 mAP50 ≠ 训练期峰值；两者不可混引。
     （具体数值随模型而变 → 以本脚本落盘的 `*_val_VOCdevkit_metrics.json` 为准，
       勿在脚本或图注里硬编码。）

Output: PNG only, 900 DPI -> 04_Outputs/05_模型作图/
用法  : D:/Deep_Learning/anaconda_envs/fish_CV/python.exe fig6_confusion.py
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（阶段3）

MODEL_TAG = P.TRAIN_TAG                          # 现行 G0_yolo11n_640；换模型设 GYO_TRAIN_TAG
DATA_YAML = P.DATA_YAML                          # 默认 03_模型作图/data_val.yaml
BEST = P.WEIGHTS                                 # 换模型设 GYO_WEIGHTS
IMGSZ = P.IMGSZ                                  # 与权重训练尺寸一致（现行 640，勿硬编码）
OUT = P.MODEL_FIG                                # 阶段3 图根：04_Outputs/05_模型作图
os.makedirs(OUT, exist_ok=True)

DPI = 900
CMAP = "OrRd"          # 项目"橙灰红"体系的橙红渐变
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 13
plt.rcParams['axes.linewidth'] = 1.2


def plot_cm(mat, labels, title, save_name, fmt, cbar_label, vmax=None):
    fig, ax = plt.subplots(figsize=(8.6, 7.2))
    vmax = mat.max() if vmax is None else vmax
    im = ax.imshow(mat, cmap=CMAP, vmin=0, vmax=vmax)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel('Predicted Class', fontweight='bold', fontsize=15)
    ax.set_ylabel('True Class', fontweight='bold', fontsize=15)
    ax.set_title(title, fontweight='bold', fontsize=16, pad=14)

    thr = vmax * 0.55
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if mat[i, j] == 0 and fmt == '.0f':
                continue
            ax.text(j, i, format(mat[i, j], fmt), ha='center', va='center',
                    color='white' if mat[i, j] > thr else 'black', fontsize=11)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(cbar_label, fontweight='bold', fontsize=13)
    fig.tight_layout()
    fig.savefig(save_name, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print('saved:', save_name)


def main():
    from ultralytics import YOLO

    model = YOLO(BEST)
    # plots=True 才会填充 res.confusion_matrix.matrix
    res = model.val(data=DATA_YAML, split='val', imgsz=IMGSZ,
                    plots=True, workers=0)

    cm9 = np.asarray(res.confusion_matrix.matrix, dtype=float)   # 含 background
    names = [str(v) for v in model.names.values()]               # ["1".."8"]
    n_cls = len(names)
    cm = cm9[:n_cls, :n_cls]                                     # 8×8（去背景）

    def rownorm(m):
        rs = m.sum(axis=1, keepdims=True)
        return np.divide(m, rs, out=np.zeros_like(m), where=rs != 0)

    # ---- 主图：8×8，标签 1–8（标题只留主标题，限定条件一律放图注） ----
    plot_cm(rownorm(cm), names, 'Normalized Confusion Matrix',
            os.path.join(OUT, 'Fig6_confusion_normalized.png'),
            '.2f', 'Recall Rate', vmax=1.0)
    plot_cm(cm, names, 'Raw Counts Confusion Matrix',
            os.path.join(OUT, 'Fig6_confusion_raw.png'),
            '.0f', 'Count')

    # ---- 补充图：9×9，含 background ----
    lab9 = names + ['background']
    plot_cm(rownorm(cm9), lab9, 'Normalized Confusion Matrix',
            os.path.join(OUT, 'Fig6_confusion_normalized_withbg.png'),
            '.2f', 'Recall Rate', vmax=1.0)

    # ---- 指标落盘 ----
    metrics = {'model': MODEL_TAG, 'imgsz': IMGSZ, 'data': 'VOCdevkit/val (755)'}
    try:
        mp, mr, map50, mapp = res.box.mp, res.box.mr, res.box.map50, res.box.map
        metrics.update({'P': float(mp), 'R': float(mr),
                        'mAP50': float(map50), 'mAP50-95': float(mapp)})
        print('Precision=%.4f  Recall=%.4f  mAP@0.5=%.4f  mAP@0.5:0.95=%.4f'
              % (mp, mr, map50, mapp))
        try:
            maps = list(res.box.maps) if res.box.maps is not None else []
            if maps and len(maps) == n_cls:
                metrics['per_class_mAP50-95'] = {n: float(v)
                                                 for n, v in zip(names, maps)}
        except Exception as e:
            print('per-class unavailable:', e)
    except Exception as e:
        print('metrics unavailable:', e)
    out_metrics = os.path.join(OUT, '%s_val_VOCdevkit_metrics.json' % MODEL_TAG)
    with open(out_metrics, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print('saved metrics:', out_metrics)


if __name__ == '__main__':
    main()
