# 03_Code 目录索引（5 阶段归口规范）

> 整理日期：2026-09-14（**2026-09-15 更新：单口径收口 + 频率作图拆为阶段5**）　规范来源：`03_Code/gyo_paths.py`
> 原则：**一切路径由 `gyo_paths.py` 解析，任何脚本不得写绝对路径。**

## 目录结构

```
03_Code/
├── gyo_paths.py            ★ 统一路径入口（唯一真源，环境变量可切换数据源）
├── run_downstream.py       ★ 5 阶段一键执行
├── README.md               ← 本文件
│
├── 00_模型训练/            训练入口（非下游链）
│   └── randomsplit_VOCdevkit/   data.yaml + train_G0 / train_G_H1 / train_G_H2
│
├── 01_提取表与运动学/        【阶段1】提取表 + 运动学
├── 02_行为频率/             【阶段2】三部位频率**计算** + 指标（postproc 唯一实现）
├── 03_模型作图/             【阶段3】混淆矩阵 / 训练曲线
├── 04_行为作图/             【阶段4】**仅**运动学(速度/位移) + 轨迹
├── 05_频率作图/             【阶段5】三部位频率**全部图**（F1–F6；freq_style 唯一实现）
└── 99_历史脚本/             已归档（不在现行链）
    ├── _debug/             调试残留
    └── _历史数据/           历史数据表（不应放在代码目录）
```

## 五阶段：脚本 → 输入 → 输出（输出目录全部由 `gyo_paths` 决定）

| 阶段 | 脚本 | 输入 | 输出 |
|---|---|---|---|
| **1** | `0_视频量化-历遍文件夹所有视频.py` / `0_视频量化_TTA修复版.py` | `P.VIDEO_SRC` 源视频 + `P.WEIGHTS` | `P.MP4/<视频>/bbox_data.xlsx` |
| **1** | `0_3_assemble_Origin_data_s.py` | `P.MP4/*/bbox_data.xlsx` | `P.QUANT/0_Origin_data_s.xlsx` |
| **1** | `1_split_origin_s_to_four.py` | `P.QUANT/0_Origin_data_s.xlsx` | `P.QUANT/{1_全身,2_鳃盖,3_胸鳍,4_尾鳍}.xlsx` |
| **1** | `5_process_quanshen.py` | `P.QUANT/1_全身.xlsx` | `P.QUANT/5_公式计算后_全身.xlsx` |
| **1** | `6_8_regen_speed_disp_fixed.py` | `5_公式计算后_全身.xlsx` | `P.QUANT/{6_总结版,8_速度位移}_全身.xlsx` |
| **1** | `7_center_trajectory_1hz.py` | `5_公式计算后_全身.xlsx` | `P.QUANT/7_中心点轨迹_全身.xlsx` |
| **1** | `10_beautify_tables.py` | `P.QUANT/*.xlsx` | 原地美化（表头/冻结首行/列宽/斑马纹）— **阶段1 收尾步** |
| **1** | `0_2.数据表公式.py`（旧版公式实现） | 需 `GYO_FORMULA_IN` | **已被 `5_process_quanshen.py` 取代**，保留作公式口径参考；无显式输入时会报错退出 |
| **1** | `0_补时间S_Origin_data.py`（补救工具） | `0_Origin_data_s.xlsx` | 重算 `时间S`（`0_3` 已内联完成同一件事，仅手工修表时用） |
| **2** | `postproc.py`（唯一后处理实现） | `P.QUANT/{2_鳃盖,3_胸鳍,4_尾鳍}.xlsx` | 供下三行 import |
| **2** | `类别1,2 / 3,4 / 5,6,7 —— …计算与绘图.py` | `postproc` | `P.QUANT/<部位>/{统计,图}/` |
| **2** | `combine_15_sheets.py` | 上行的逐鱼统计 | `P.QUANT/{呼吸频率,胸鳍摆动频率,尾鳍摆动频率}.xlsx` |
| **2** | `make_per_fish_metrics.py` | `8_速度位移_全身.xlsx` + 三张合并表 | `P.QUANT/per_fish_metrics.{csv,xlsx}` |
| **2** | `compute_{respiration,pectoral,caudal}.py` | 重算 vs 权威合并表 | **不落盘**（2026-09-15 起）：只打印逐格 `MAE / r / 最大绝对差`。原 `<部位>_重算.xlsx` 与权威表**逐格完全相同**（15 sheet × 2811 格，0 差异）且无人读取 → 已停产 |
| **2** | `make_21-1_countboard.py` | `P.QUANT` + `P.QUANT/21-1_人眼.xlsx`（**权威真值**） | `P.RES/21-1_countboard_{data.xlsx,mp4}`（`P.RES` 现 = `P.QUANT`） |
| **3** | `fig6_confusion.py` | `P.WEIGHTS` + `P.DATA_YAML` | `P.MODEL_FIG/Fig6_confusion_*.png` + `<tag>_val_VOCdevkit_metrics.json` |
| **3** | `fig6_training_curves.py` | `P.TRAIN_CSV` + 上一行的 JSON | `P.MODEL_FIG/Fig6_training_curves.png` |
| **3** | `fig6_validation_curve.py` | `P.QUANT/21-1_人眼.xlsx`（回退 countboard） | `P.MODEL_FIG/Fig6_validation_curve{,_smooth}.png` |
| **4** | `fig2_body_vs_temp.py` | `per_fish_metrics.csv` | `P.FIG/Fig2_body_vs_temp.png`（速度/累计位移简版；与 `fig6b_kinematics.py` 同源） |
| **4** | `fig6b_kinematics.py` | `per_fish_metrics.csv` | `P.FIG/Fig6B_velocity_displacement.png`（**单面板双轴**：速度柱 `a/a/a/b/a` + 位移折线/SD 带；**左上角嵌图**＝15 尾速度–位移散点、按温度着色 + 参考线（斜率读量化表逐尾 `S/v_mean`，613 s）+ `r`；图例在右上角） |
| **4** | `fig7_trajectory_heatmap.py` | `5_公式计算后_全身.xlsx`（全身坐标） | `P.FIG/Fig7_trajectory_heatmap.png`（单幅 3×5 轨迹热图；`NORM='per_fish'`） |
| **4** | `fig4A.py` | `21-1_countboard_data.xlsx` | `P.FIG/Fig5/Fig5_temporal_validation.png` |
| **4** | `plot_analysis.py` | `per_fish_metrics.xlsx` + countboard | `P.FIG/Fig1…Fig5/*_analysis.png` |
| **4** | `fig8_temp_regression.py` | `per_fish_metrics.csv` | `P.FIG/Fig8_temp_regression.png`（速度热性能曲线：二次拟合 + bootstrap 95% 带 + T\* 分布 + 效应量/置换检验） |
| **4** | `fig9_trajectory_metrics.py` | `7_中心点轨迹_全身.xlsx`（1 Hz）+ `8_速度位移_全身.xlsx`（校验参照） | `P.FIG/Fig9_trajectory_metrics.png` + `_traj_metrics.csv`（直线度/转向角/burst 占比/占用面积；**L 闭合校验不过则不出图**） |
| **4** | `fig10_metric_structure.py` | `per_fish_metrics.csv` | `P.FIG/Fig10_metric_structure.png`（相关矩阵 + PCA；显示 6 指标实为约 3 个自由度） |
| **5** | `freq_style.py`（**统一样式与取数，唯一实现**） | `P.QUANT` 三张合并表 / `per_fish_metrics.csv` | 供下六行 import |
| **5** | `F1_freq_vs_temp.py` | `per_fish_metrics.csv` | `P.FREQ/F1_freq_vs_temp.png`（1×3；**不显著者标 `n.s.`**） |
| **5** | `F2_waveform.py` | 三张频率合并表 | `P.FREQ/F2_waveform.png`（每温度一格，三部位叠加 mean±SEM） |
| **5** | `F3_coordination.py` | 三张频率合并表 | `P.FREQ/F3_coordination.png`（三对部位逐窗 Pearson r vs 温度） |
| **5** | `F4_resp_velocity.py` | `per_fish_metrics.csv` | `P.FREQ/F4_resp_velocity.png`（呼吸频率 vs 速度，逐鱼散点） |
| **5** | `F5_cost_ratio.py` | `呼吸频率.xlsx` + `8_速度位移_全身.xlsx` | `P.FREQ/F5_cost_ratio.png`（代价比箱线 + 原始点） |
| **5** | `F6_caliber_scan.py` | `P.QUANT` 四表 + `postproc`（参数扫描） | `P.FREQ/F6_caliber_scan.png`（**口径漂移 ÷ 组内 SD**；补充材料） |

## 路径常量速查（`gyo_paths`）

| 常量 | 默认值 | 用途 |
|---|---|---|
| `P.QUANT` | `04_Outputs/02_模型量化数据640_G0_TTA` | **阶段1+2 输入与输出（数据归口）** |
| `P.MP4` | `<QUANT>/MP4` | 逐视频量化产物（Step B 输入） |
| `P.MODEL_FIG` | `04_Outputs/03_模型作图` | **阶段3 出图** |
| `P.FIG` | `04_Outputs/04_行为作图` | **阶段4 出图** |
| `P.RES` | **= `P.QUANT`** | 分析中间物（人眼真值、countboard）——2026-09-15 起并入数据根 |
| `P.TRAIN` / `P.WEIGHTS` / `P.TRAIN_CSV` | `01_Result_train/G0_yolo11n_640/…` | 阶段3 的模型与训练记录 |
| `P.IMGSZ` | `640` | 阶段3 推理尺寸（须与训练尺寸一致） |
| `P.DATA_YAML` | `03_Code/03_模型作图/data_val.yaml` | 阶段3 验证集配置 |

## 切换数据源 / 换模型

```powershell
set GYO_QUANT=E:\server_out\02_模型量化数据_New   # 阶段1+2 数据根（其下需有 MP4/）
set GYO_TRAIN_TAG=G1_yolo11n_640                  # 阶段3 定位 <TRAIN>/<tag>/results.csv
set GYO_WEIGHTS=...\G1_yolo11n_640\weights\best.pt
set GYO_IMGSZ=640
python "03_Code\run_downstream.py"
```

## 合规

- 脚本只读输入、只写各自归口目录；不覆盖源表。
- 新增脚本必须 `import gyo_paths as P` 取路径；`99_历史脚本/` 不参与现行链。
- 详细承接流程见 `06_Docs/承接新量化数据_操作手册.md`。

## 变更（2026-09-15：单口径收口）

1. **模型**统一为 `G0_yolo11n_640`（`G_H1_img960` 已移除）→ `P.TRAIN_TAG` / `P.WEIGHTS` / `P.TRAIN_CSV` 跟随，
   新增 `P.IMGSZ = 640`。`fig6_confusion.py` 的 IMGSZ 不再硬编码 960。
2. **数据根**统一为 `04_Outputs/02_模型量化数据640_G0_TTA`（自包含阶段1+2 产物 + 人眼真值）。
3. **`04_Outputs/05_模型作图` → `03_模型作图`**；**`04_Outputs/03_分析结果` 撤销**，
   分析中间物并入数据根 → `P.RES` 现 = `P.QUANT`。
4. **`03_模型作图/` 代码目录**只保留与产出 1:1 对应的脚本（`fig6_confusion` / `fig6_training_curves` /
   `fig6_validation_curve` + `data_val.yaml`）；`fig4C.py`、`模型评估.py` **归档**至 `99_历史脚本/`
   （依赖已删除的 Windows 基线 CSV，且基线为合成值）。详见 `03_模型作图/README.md`。
5. **人眼真值**以 `P.QUANT/21-1_人眼.xlsx` 为准（`03_分析结果` 副本已撤销）。
