"""Fig6 (model performance) — G_H1_img960 训练曲线（3 面板）。

- 数据源: 04_Outputs/01_Result_train/G_H1_img960/results.csv
          （120 epoch；train/val 的 box·cls·dfl loss、P/R/mAP50/mAP50-95、lr×3）
- 配色  : 项目"橙灰红"——训练 #F4A460 / 验证·mAP #D62728 / 次要 #708090 / 网格 #E0E0E0
- 输出  : PNG @900 DPI -> 04_Outputs/05_模型作图/Fig6_training_curves.png
- 面板  : a Total Loss(train/val) | b mAP50 + mAP50-95 | c Precision / Recall

⚠ 学习率面板已移除（原 2×2 的面板 d）。原因：`results.csv` 的 `lr/pg2` 在 E1–E4 为
   bias 组的 warmup（0.0802 → 0，是 pg0 峰值 4.83e-4 的 166 倍），只画 `lr/pg0`
   会漏掉该信息、易误导；且学习率属超参设定而非实验结果，故改由图注/Methods 陈述：

   优化器 AdamW；初始学习率 lr0 = 5e-4；最终学习率因子 lrf = 5e-5
   （线性衰减，末轮实测 4.19e-6，与 ultralytics 公式
    lr(x) = lr0·[(1 − x/epochs)(1 − lrf) + lrf] 逐位吻合）；
   前 5 个 epoch 为线性 warmup；weight_decay = 1e-3；momentum = 0.937；
   batch = 16；imgsz = 960；epochs = 120；box/cls/dfl = 0.05/0.6/0.1；
   close_mosaic = 10；AMP 开启；seed = 0。

⚠ 图注必须声明（数据源 `G_H1_img960/来源.md`）：
  1) 训练期峰值 mAP50 = 0.9386 @E52、mAP50-95 = 0.6919 @E85；
     而交付的 `best.pt`（最优 fitness 轮）在同一 val 上实测 mAP50 = 0.9266（图中虚线），
     二者不可混引。
用法  : D:/Deep_Learning/anaconda_envs/fish_CV/python.exe fig6_training_curves.py
"""
import json
import os
import sys

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（阶段3）

CSV = P.TRAIN_CSV              # 换模型设 GYO_TRAIN_TAG / GYO_TRAIN
OUT = P.MODEL_FIG              # 阶段3 图根：04_Outputs/05_模型作图
# 指标 json 由 fig6_confusion.py 落盘，文件名带当前模型 tag。
# ⚠ 不要回退到别的 tag 的 json —— 那会把**另一个模型**的 best.pt mAP 标到本图上。
METRICS = os.path.join(OUT, '%s_val_VOCdevkit_metrics.json' % P.TRAIN_TAG)
os.makedirs(OUT, exist_ok=True)

DPI = 900
C_TRAIN = '#F4A460'   # 橙 —— 训练
C_VAL = '#D62728'     # 红 —— 验证 / mAP
C_GREY = '#708090'    # 灰 —— 次要曲线
C_GRID = '#E0E0E0'

plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['axes.spines.right'] = False
plt.rcParams['axes.spines.top'] = False


def main():
    df = pd.read_csv(CSV)
    df.columns = df.columns.str.strip()
    df['total_train_loss'] = (df['train/box_loss'] + df['train/cls_loss']
                              + df['train/dfl_loss'])
    df['total_val_loss'] = (df['val/box_loss'] + df['val/cls_loss']
                            + df['val/dfl_loss'])

    ep = df['epoch']
    m50 = df['metrics/mAP50(B)']
    m5095 = df['metrics/mAP50-95(B)']
    e50, v50 = int(df.loc[m50.idxmax(), 'epoch']), m50.max()
    e95, v95 = int(df.loc[m5095.idxmax(), 'epoch']), m5095.max()
    n_ep = int(ep.max())

    # best.pt 实测值（由 fig6_confusion.py 落盘；缺失则跳过该标注）
    bp = None
    if os.path.exists(METRICS):
        with open(METRICS, encoding='utf-8') as f:
            bp = json.load(f).get('mAP50')

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13.6, 3.8))

    # ---- a. Total Loss ----
    ax1.plot(ep, df['total_train_loss'], color=C_TRAIN, lw=1.6, label='Training')
    ax1.plot(ep, df['total_val_loss'], color=C_VAL, lw=1.6, ls='--', label='Validation')
    ax1.set_xlabel('Epochs', fontweight='bold')
    ax1.set_ylabel('Total Loss', fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.set_xlim(0, n_ep)

    # ---- b. mAP ----
    ax2.plot(ep, m50, color=C_VAL, lw=2.0, label='mAP@0.5')
    ax2.plot(ep, m5095, color=C_GREY, lw=1.6, label='mAP@0.5:0.95')
    ax2.scatter([e50], [v50], color=C_VAL, zorder=5, s=24)
    ax2.scatter([e95], [v95], color=C_GREY, zorder=5, s=24)
    ax2.annotate('max %.4f @E%d' % (v50, e50), xy=(e50, v50),
                 xytext=(e50 + 8, v50 - 0.14), fontsize=9, fontweight='bold',
                 color=C_VAL, arrowprops=dict(arrowstyle='->', color=C_VAL))
    ax2.annotate('max %.4f @E%d' % (v95, e95), xy=(e95, v95),
                 xytext=(e95 + 8, v95 - 0.30), fontsize=9, fontweight='bold',
                 color=C_GREY, arrowprops=dict(arrowstyle='->', color=C_GREY))
    if bp is not None:
        ax2.axhline(bp, color='#444444', lw=1.0, ls=':')
        ax2.text(2, bp + 0.03, 'best.pt measured %.4f' % bp,
                 fontsize=8.5, color='#444444')
    ax2.set_xlabel('Epochs', fontweight='bold')
    ax2.set_ylabel('mAP', fontweight='bold')
    ax2.set_xlim(0, n_ep)
    ax2.set_ylim(0, 1.05)
    ax2.legend(loc='lower right')

    # ---- c. Precision / Recall ----
    ax3.plot(ep, df['metrics/precision(B)'], color=C_TRAIN, lw=1.6, label='Precision')
    ax3.plot(ep, df['metrics/recall(B)'], color=C_VAL, lw=1.6, ls='--', label='Recall')
    ax3.set_xlabel('Epochs', fontweight='bold')
    ax3.set_ylabel('Score', fontweight='bold')
    ax3.set_xlim(0, n_ep)
    ax3.set_ylim(0, 1.05)
    ax3.legend(loc='lower right')

    # 项目出图规范（2026-09-15）：不加面板字母 a/b/c，不加额外标题。
    # 面板信息由坐标轴标签与图注承载。
    for ax in (ax1, ax2, ax3):
        ax.grid(True, ls=':', color=C_GRID, lw=0.8)

    out = os.path.join(OUT, 'Fig6_training_curves.png')
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print('[OK] saved:', out)
    print('   epochs=%d  best mAP50=%.4f @E%d  best mAP50-95=%.4f @E%d'
          % (n_ep, v50, e50, v95, e95))


if __name__ == '__main__':
    main()
