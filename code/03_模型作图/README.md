# 03_模型作图（阶段3）— 模型性能出图

**产出目录**：`04_Outputs/03_模型作图/`（`gyo_paths.P.MODEL_FIG`；2026-09-15 由 `05_模型作图` 改名）
**路径真源**：`03_Code/gyo_paths.py` —— 本目录所有脚本一律 `import gyo_paths as P`，**禁止写绝对路径**。

---

## 1. 现行口径（2026-09-15）

| 项 | 值 |
|---|---|
| 模型 | `P.WEIGHTS` = `04_Outputs/01_Result_train/G0_yolo11n_640/weights/best.pt` |
| 推理尺寸 | `P.IMGSZ` = **640**（须与训练尺寸一致） |
| 训练曲线数据 | `P.TRAIN_CSV` = `.../G0_yolo11n_640/results.csv`（200 epochs） |
| 验证集 | `data_val.yaml` → `VOCdevkit/val`（755 张，8 类） |
| 指标 JSON | `P.MODEL_FIG/<P.TRAIN_TAG>_val_VOCdevkit_metrics.json`（由 `fig6_confusion.py` 落盘） |

> ⚠ `G_H1_img960`（yolo11n @960）已于 2026-09-15 移除，其指标 JSON 一并清理。
> 训练曲线脚本**不再回退**到其它 tag 的 JSON —— 那会把别的模型的 mAP 标到本图上。

## 2. 文件 → 产出映射

| 脚本 | 产出（`P.MODEL_FIG/`） | 说明 |
|---|---|---|
| `fig6_confusion.py` | `Fig6_confusion_normalized.png`、`Fig6_confusion_raw.png`、`Fig6_confusion_normalized_withbg.png`、`<tag>_val_VOCdevkit_metrics.json` | 实测混淆矩阵（8×8 正文版 + 9×9 含 background 补充版）；配色 `OrRd` |
| `fig6_training_curves.py` | `Fig6_training_curves.png` | 3 面板（Total Loss / mAP / Precision&Recall）；读 `P.TRAIN_CSV` + 上表 JSON |
| `fig6_validation_curve.py` | `Fig6_validation_curve.png`、`Fig6_validation_curve_smooth.png` | 21-1 模型 vs 人眼两版：原始=3 面板横排；平滑=竖排 3 行 + B 样条 k=3 + 显著标记。两版 AR/r **均按原始逐窗值**计算 |
| `data_val.yaml` | ——（输入） | 验证集契约，供 `fig6_confusion.py` |

**执行顺序**：`fig6_confusion.py` 必须先跑（它落盘指标 JSON，供训练曲线标注 `best.pt` 实测值）。

### 外部图（无生成脚本，不可由本目录复现）

| 文件 | 来源 | 说明 |
|---|---|---|
| `moxing.png` | **外部制作**（非本项目脚本） | 7086 × 8000 px @ **900 DPI**；2026-09-15 由 600 DPI 改标记而来（**仅改元数据，像素未动**）→ 物理尺寸 7.87 × 8.89 inch。⚠ 上游数据一变需**手工同步**，脚本链不会更新它。 |

> 外部图不进 `run_downstream.py`；引用时请在图注中注明其为外部制作。

## 3. 运行

```powershell
$env:CODEBUDDY_SAFE_DELETE_ENABLED='0'
$py = 'D:\Deep_Learning\anaconda_envs\fish_CV\python.exe'
$d  = 'D:\Deep_Learning\01_Projects\Gymnocypris eckloni\03_Code\03_模型作图'

& $py "$d\fig6_confusion.py"          # 先跑：产出混淆矩阵 + 指标 JSON
& $py "$d\fig6_training_curves.py"    # 训练曲线（需上一步的 JSON）
& $py "$d\fig6_validation_curve.py"   # 人眼对照两版
```

一键链：`python 03_Code\run_downstream.py 阶段3`

## 4. 出图规范（见 `总览.md` §9）

- 字体 `Times New Roman`；`axes.linewidth 1.2`；刻度朝内；去上/右边框；PNG @900 DPI
- 配色：模型 橙 `#F4A460` / 人工 灰 `#708090` / 强调 红 `#D62728`
- **不加面板字母 `a/b/c`，不加额外标题**（`set_title` / `suptitle`）；面板身份由**坐标轴标签**承载，
  其余说明归图注。注记类文字（AR/r、max 标注）保留，置于轴内并加白色底衬。

## 5. 已归档（2026-09-15）

| 脚本 | 去向 | 原因 |
|---|---|---|
| `fig4C.py` | `03_Code/99_历史脚本/` | 依赖已移除的 Windows 基线 CSV（`trainyolo11n_M` / `trainyolo11n`），**必崩**；且基线用 `np.random.normal` **合成**、mAP 硬设 0.915 上限 —— 非实测 |
| `模型评估.py` | `03_Code/99_历史脚本/` | 依赖已移除的 `trainyolo11n/YOLO11n-results.csv`，**必崩** |

> ⇒ 稿件图 `Figure_5_Full_Comparison` / `Figure_5A_*` **无法再复现**（输入已删 + 基线为模拟值）。
> 现行请用 `Fig6_training_curves.png`（G0 实测口径）。

## 6. 不变量

- **混淆矩阵错分只发生在部位组内**（2↔3 鳃盖、4↔5 胸鳍、6↔7↔8 尾鳍），跨部位为 0。
- 现行 G0 @640 对角召回：胸鳍 4/5 = **0.78 / 0.83**（八类最低）→ 与"胸鳍计数一致性最弱"一致。
- `best.pt` ≠ 训练期峰值轮；两者不可混引（具体值以落盘 JSON 为准，勿在脚本/图注硬编码）。
