from ultralytics import YOLO
import cv2
import os
import sys
import pandas as pd
from collections import defaultdict
from tqdm import tqdm
from datetime import timedelta
import logging
import gc
import torch

# ------------- 参数配置 -------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gyo_paths as P          # 统一路径入口（环境变量可整体切换数据源/模型）

model_path = P.WEIGHTS      # 权重（换模型设 GYO_WEIGHTS）
input_path = P.VIDEO_SRC    # 源视频目录（可为单个视频或文件夹）
output_root = P.MP4         # 逐视频量化产物根（= 阶段1 Step B 的输入目录）
IMGSZ = 960   # 与 G_H1 训练分辨率一致（G_H1 训练于 imgsz=960）
TARGET = sys.argv[1] if len(sys.argv) > 1 else None  # 传视频名(如 21-1)只跑该条；不传=全部

# 判断是单个文件还是目录
if os.path.isfile(input_path):
    video_list = [input_path]
elif os.path.isdir(input_path):
    exts = (".mp4", ".avi", ".mov", ".mkv")
    video_list = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.lower().endswith(exts)]
else:
    raise FileNotFoundError(f"未找到输入路径: {input_path}")

# 只跑指定视频（验证用）
if TARGET:
    video_list = [v for v in video_list if os.path.splitext(os.path.basename(v))[0] == TARGET]
    if not video_list:
        raise FileNotFoundError(f"未找到目标视频: {TARGET}")

# ------------- 加载模型 -------------
if not os.path.exists(model_path):
    raise FileNotFoundError(f"模型权重文件未找到：{model_path}")
model = YOLO(model_path)
print(f"模型加载完成: {model_path}")
print(f"imgsz={IMGSZ} | 待处理视频 {len(video_list)} 条 | 输出根: {output_root}")

# ------------- 遍历处理视频 -------------
for video_path in video_list:
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    output_path = os.path.join(output_root, video_name)
    os.makedirs(output_path, exist_ok=True)

    # ------------- 日志初始化 -------------
    log_path = os.path.join(output_path, 'process.log')
    logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(message)s')
    logging.info(f"开始处理视频：{video_name}")

    # ------------- 视频读取 -------------
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"无法打开视频文件：{video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    split_point = total_frames // 2

    # ------------- 视频写入器初始化 -------------
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output_video_path = os.path.join(output_path, f"{video_name}.mp4")
    video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    # ------------- 统计变量初始化 -------------
    status_counts = defaultdict(int)
    bbox_data = []
    current_frame = 0

    # ------------- 主循环（两段） -------------
    for segment_index, (start_frame, end_frame) in enumerate([(0, split_point), (split_point, total_frames)]):
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        print(f"\n▶ 正在处理第 {segment_index + 1}/2 段帧：{start_frame} 到 {end_frame}")

        for _ in tqdm(range(start_frame, end_frame), desc=f"处理段 {segment_index + 1}"):
            ret, frame = cap.read()
            if not ret:
                break

            current_frame += 1
            seconds = current_frame / fps
            timestamp = str(timedelta(seconds=seconds)).split('.')[0]

            results = model(frame, imgsz=IMGSZ)

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = box.conf[0].item()

                    if 1 <= cls <= 8:
                        status_counts[cls] += 1

                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2

                    bbox_data.append({
                        '帧编号': current_frame,
                        '时间戳': timestamp,
                        '类别': cls,
                        '置信度': conf,
                        'x1': x1,
                        'y1': y1,
                        'x2': x2,
                        'y2': y2,
                        '中心点X': center_x,
                        '中心点Y': center_y
                    })

                annotated_frame = result.plot()
                cv2.putText(annotated_frame, timestamp, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                video_writer.write(annotated_frame)

            if current_frame % 300 == 0:
                torch.cuda.empty_cache()
                gc.collect()

            del result, results

    # ------------- 资源释放与保存 -------------
    cap.release()
    video_writer.release()
    try:
        cv2.destroyAllWindows()   # 无 GUI 的 OpenCV(pip 版) 会抛错，忽略即可
    except Exception:
        pass

    # 保存状态统计表
    df_status = pd.DataFrame({
        '状态ID': list(range(1, 9)),
        '出现次数': [status_counts[i] for i in range(1, 9)]
    })
    df_status.to_excel(os.path.join(output_path, 'state_counts.xlsx'), index=False)

    # 保存边界框数据表 + 添加 Excel 公式列
    df_bbox = pd.DataFrame(bbox_data)

    # 插入 Excel 公式（基于“时间戳”列在B列，行从2开始）
    df_bbox.insert(2, '时间S', [f'=HOUR(B{i})*3600 + MINUTE(B{i})*60 + SECOND(B{i})' for i in range(2, 2 + len(df_bbox))])

    # 使用 ExcelWriter 保留公式格式
    excel_path = os.path.join(output_path, 'bbox_data.xlsx')
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_bbox.to_excel(writer, index=False)

    logging.info(f"完成处理视频：{video_name}")
    print("\n✅ 视频处理完成，结果已保存到：", output_path)
