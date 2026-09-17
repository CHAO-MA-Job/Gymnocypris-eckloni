# -*- coding: utf-8 -*-
"""run_downstream.py —— 下游链【5 阶段】一键执行（按 gyo_paths 归口规范）
================================================================
所有路径由 `03_Code/gyo_paths.py` 统一解析，**本脚本不写任何绝对路径**。

 阶段1 提取表与运动学   → 数据根 P.QUANT
     B  组装 0_Origin_data_s.xlsx（读 P.MP4 下各视频的 bbox_data.xlsx）
     C  拆分 1_全身 / 2_鳃盖 / 3_胸鳍 / 4_尾鳍
     D  运动学 5_公式计算后 / 6_总结版 / 7_中心点轨迹 / 8_速度位移
 阶段2 频率计算         → 数据根 P.QUANT（与阶段1 同根）
     E1 三部位频率（呼吸/胸鳍/尾鳍）→ <QUANT>/<部位>/{统计,图}/
     E2 15 表组合 → <QUANT>/{呼吸频率,胸鳍摆动频率,尾鳍摆动频率}.xlsx
     F  逐鱼指标 per_fish_metrics.* → <QUANT>/
     校验 compute_*（重算 vs 权威合并表，报 MAE / r）
 阶段3 模型作图         → P.MODEL_FIG (04_Outputs/03_模型作图)
     混淆矩阵（读 P.WEIGHTS + P.DATA_YAML）、训练曲线（读 P.TRAIN_CSV）
 阶段4 行为作图         → P.FIG (04_Outputs/04_行为作图) —— 运动学 + 轨迹（主图）
     全身速度/位移(Fig2 简版, Fig6B 正图) / 全身坐标轨迹(Fig7) / 温度回归(Fig8)
     + Fig11 速度一致性 / Fig12 空间使用 / Fig13 投影面积（2026-09-16 新增）
 阶段5 频率作图         → P.FREQ (04_Outputs/05_频率计算) —— 仅 F2 波形（进正文，纯量化展示）
 阶段6 补充作图         → P.SUPP (04_Outputs/06_Supplementary) —— 不进正文的描述性图
     Fig9 轨迹几何 / Fig10 PCA / F1 频率vs温度 / F3 协同 / F4 呼吸-速度 / F5 代价比
     （2026-09-16 由 阶段4/阶段5 移入）

【承接服务器新量化产物】只需设环境变量，不改任何脚本：
    set GYO_QUANT=<新数据根>        # 阶段1/2 的输入与输出（其下需有 MP4/ 与四表）
    set GYO_TRAIN_TAG=<新模型名>    # 阶段3 定位 <TRAIN>/<tag>/results.csv
    set GYO_WEIGHTS=<新 best.pt>    # 阶段3 混淆矩阵
    set GYO_IMGSZ=<训练尺寸>        # 阶段3 混淆矩阵（默认 960）
    python "03_Code\\run_downstream.py"
    （逐视频量化产物放在 <GYO_QUANT>/MP4/<视频名>/bbox_data.xlsx）

用法
    python "03_Code\\run_downstream.py"                  # 全部
    python "03_Code\\run_downstream.py" 阶段2             # 只跑名称含"阶段2"的步骤
    python "03_Code\\run_downstream.py" 混淆 训练曲线       # 按关键字选步
    set GYO_SKIP_B=1                                     # 跳过 Step B（已组装过）
    python "03_Code\\gyo_paths.py"                        # 只打印当前路径配置
"""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))   # 03_Code
sys.path.insert(0, HERE)
import gyo_paths as P          # noqa: E402

PY = sys.executable
os.environ.setdefault('CODEBUDDY_SAFE_DELETE_ENABLED', '0')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')   # 防 Windows GBK 控制台下 print 崩溃

SKIP_B = os.environ.get('GYO_SKIP_B') == '1'
SKIP_BEAUTIFY = os.environ.get('GYO_SKIP_BEAUTIFY') == '1'
# Step B 输入：若量化产物是"单个合并 15-sheet 表"，用 GYO_STEP_B_INPUT 直接指定，
# 免去逐视频 MP4/<vid>/bbox_data.xlsx 的目录约定。
STEP_B_INPUT = os.environ.get('GYO_STEP_B_INPUT') or None

# (阶段, 步骤名, 阶段内脚本相对 03_Code 的路径)
_STEPS = [
    ('阶段1', 'B  组装 Origin_data_s', r'01_提取表与运动学\0_3_assemble_Origin_data_s.py'),
    ('阶段1', 'C  拆分四表',           r'01_提取表与运动学\1_split_origin_s_to_four.py'),
    ('阶段1', 'D1 运动学·公式',        r'01_提取表与运动学\5_process_quanshen.py'),
    ('阶段1', 'D2 速度位移/总结',      r'01_提取表与运动学\6_8_regen_speed_disp_fixed.py'),
    ('阶段1', 'D3 中心点轨迹',         r'01_提取表与运动学\7_center_trajectory_1hz.py'),
    ('阶段1', 'D4 表格美化',           r'01_提取表与运动学\10_beautify_tables.py'),

    ('阶段2', 'E1 呼吸频率',           r'02_行为频率\类别1,2——呼吸频率计算与绘图.py'),
    ('阶段2', 'E1 胸鳍摆动频率',        r'02_行为频率\类别3,4——胸鳍摆动频率计算与绘图.py'),
    ('阶段2', 'E1 尾鳍摆动频率',        r'02_行为频率\类别5,6,7——尾鳍摆动频率计算与绘图.py'),
    ('阶段2', 'E2 15表组合',           r'02_行为频率\combine_15_sheets.py'),
    ('阶段2', 'F  汇总逐鱼',           r'02_行为频率\make_per_fish_metrics.py'),
    ('阶段2', '校验 呼吸频率重算',      r'02_行为频率\compute_respiration.py'),
    ('阶段2', '校验 胸鳍频率重算',      r'02_行为频率\compute_pectoral.py'),
    ('阶段2', '校验 尾鳍频率重算',      r'02_行为频率\compute_caudal.py'),
    ('阶段2', 'E3 人眼对照表',         r'02_行为频率\make_21-1_countboard.py'),

    ('阶段3', '混淆矩阵',              r'03_模型作图\fig6_confusion.py'),
    ('阶段3', '训练曲线',              r'03_模型作图\fig6_training_curves.py'),
    ('阶段3', 'Fig6 人眼对照曲线',      r'03_模型作图\fig6_validation_curve.py'),

    ('阶段4', 'Fig2 速度/位移简版',     r'04_行为作图\fig2_body_vs_temp.py'),
    ('阶段4', 'Fig6B 速度位移',        r'04_行为作图\fig6b_kinematics.py'),
    ('阶段4', 'Fig7 全身坐标轨迹',      r'04_行为作图\fig7_trajectory_heatmap.py'),
    ('阶段4', 'Fig8 温度回归',         r'04_行为作图\fig8_temp_regression.py'),
    ('阶段4', 'Fig11 速度一致性',      r'04_行为作图\fig11_velocity_consistency.py'),
    ('阶段4', 'Fig12 空间使用',        r'04_行为作图\fig12_spatial_use.py'),
    ('阶段4', 'Fig13 投影面积',        r'04_行为作图\fig13_bbox_area.py'),

    ('阶段5', 'F2 频率波形',           r'05_频率作图\F2_waveform.py'),

    ('阶段6', 'Fig9 轨迹几何指标',      r'06_补充作图\fig9_trajectory_metrics.py'),
    ('阶段6', 'Fig10 指标结构 PCA',     r'06_补充作图\fig10_metric_structure.py'),
    ('阶段6', 'F1 频率vs温度',         r'06_补充作图\F1_freq_vs_temp.py'),
    ('阶段6', 'F3 部位协同性',         r'06_补充作图\F3_coordination.py'),
    ('阶段6', 'F4 呼吸-速度',          r'06_补充作图\F4_resp_velocity.py'),
    ('阶段6', 'F5 代价比',             r'06_补充作图\F5_cost_ratio.py'),
    # ⚠ F6 口径漂移扫描 / Fig4A 时序验证 / plot_analysis：2026-09-16 已移至 99_历史脚本（作废），
    #   不再执行。
]


def steps():
    """按 GYO_SKIP_B / GYO_SKIP_BEAUTIFY 过滤后的步骤表。"""
    out = []
    for ph, nm, rel in _STEPS:
        if SKIP_B and nm.startswith('B '):
            continue
        if SKIP_BEAUTIFY and '表格美化' in nm:
            continue
        out.append((ph, nm, rel))
    return out


def main():
    only = sys.argv[1:]
    P.show()
    if SKIP_B:
        print('[gyo] GYO_SKIP_B=1 → 跳过阶段1 的 Step B')
    for d in (P.QUANT, P.FIG, P.MODEL_FIG, P.FREQ, P.SUPP):
        os.makedirs(d, exist_ok=True)

    cur_phase = None
    for phase, name, rel in steps():
        if only and not any(k in name or k in phase for k in only):
            continue
        if phase != cur_phase:
            print('\n' + '=' * 60)
            print('  %s' % phase)
            print('=' * 60, flush=True)
            cur_phase = phase
        path = os.path.join(HERE, rel)
        print('\n----- %s :: %s -----' % (name, rel), flush=True)
        if not os.path.exists(path):
            print('  [跳过] 脚本不存在', flush=True)
            continue
        try:
            cmd = [PY, path]
            if STEP_B_INPUT and name.startswith('B '):
                cmd = [PY, path, STEP_B_INPUT]
            r = subprocess.run(cmd, cwd=P.BASE, env=os.environ)
            print('  exit=%d' % r.returncode, flush=True)
            if r.returncode != 0:
                print('  [中断] 该步失败，停止后续。', flush=True)
                break
        except Exception as e:
            print('  [异常] %s: %s' % (type(e).__name__, e), flush=True)
            break
    print('\n[run_downstream] 结束。', flush=True)


if __name__ == '__main__':
    main()
