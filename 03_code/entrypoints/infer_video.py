"""Run YOLO11n inference on one video and write frame-level detections and an annotated video."""
from __future__ import annotations
import argparse,csv,hashlib,json
from datetime import timedelta
from openpyxl import Workbook
from pathlib import Path
import cv2
from ultralytics import YOLO
ROOT=Path(__file__).resolve().parents[2]

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--video',type=Path,required=True)
 ap.add_argument('--weights',type=Path,default=ROOT/'02_model/best.pt')
 ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--device',default='0',help='CUDA device index or cpu')
 ap.add_argument('--conf',type=float,default=0.25)
 ap.add_argument('--imgsz',type=int,default=640)
 ap.add_argument('--max-frames',type=int,default=0,help='0 processes the complete video')
 ap.add_argument('--no-video',action='store_true')
 ap.add_argument('--no-xlsx',action='store_true',help='Write CSV only')
 a=ap.parse_args();video=a.video.resolve();weights=a.weights.resolve();out=a.output.resolve()
 if not video.is_file():ap.error('Input video does not exist')
 if not weights.is_file():ap.error('Weights do not exist')
 if not 0<=a.conf<=1 or a.max_frames<0:ap.error('Invalid confidence or frame limit')
 out.mkdir(parents=True,exist_ok=True); csvpath=out/'detections.csv';vpath=out/'annotated.mp4';meta=out/'inference_metadata.json';xlsx=out/'bbox_data.xlsx'
 if csvpath.exists() or meta.exists() or (not a.no_video and vpath.exists()) or (not a.no_xlsx and xlsx.exists()):ap.error('Output files already exist; use a new output directory')
 cap=cv2.VideoCapture(str(video))
 if not cap.isOpened():raise RuntimeError('Cannot open input video')
 fps=cap.get(cv2.CAP_PROP_FPS);width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 if not fps or not width or not height:raise ValueError('Invalid video dimensions or frame rate')
 writer=None
 try:
  if not a.no_video:
   writer=cv2.VideoWriter(str(vpath),cv2.VideoWriter_fourcc(*'mp4v'),fps,(width,height))
   if not writer.isOpened():raise RuntimeError('Cannot open video writer')
  model=YOLO(str(weights));frame_no=0;row_count=0
  workbook=None
  if not a.no_xlsx:
   workbook=Workbook(write_only=True);sheet=workbook.create_sheet('detections');sheet.append(['帧编号','时间戳','时间S','类别','置信度','x1','y1','x2','y2','中心点X','中心点Y'])
  with csvpath.open('w',encoding='utf-8-sig',newline='') as f:
   cols=['frame_number_one_based','time_seconds','class_index','confidence','x1','y1','x2','y2','center_x','center_y'];w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
   while not a.max_frames or frame_no<a.max_frames:
    ok,frame=cap.read()
    if not ok:break
    frame_no+=1;res=model.predict(frame,imgsz=a.imgsz,conf=a.conf,augment=True,device=a.device,verbose=False)[0]
    for box in res.boxes:
     xy=box.xyxy[0].cpu().tolist();x1,y1,x2,y2=map(float,xy)
     w.writerow(dict(frame_number_one_based=frame_no,time_seconds=(frame_no-1)/fps,class_index=int(box.cls[0]),confidence=float(box.conf[0]),x1=x1,y1=y1,x2=x2,y2=y2,center_x=(x1+x2)/2,center_y=(y1+y2)/2));row_count+=1
     if workbook:sheet.append([frame_no,str(timedelta(seconds=frame_no/fps)).split('.')[0],int(frame_no/fps),int(box.cls[0]),float(box.conf[0]),x1,y1,x2,y2,(x1+x2)/2,(y1+y2)/2])
    if writer:writer.write(res.plot())
  if workbook:workbook.save(xlsx)
 finally:
  cap.release()
  if writer:writer.release()
 meta.write_text(json.dumps(dict(video_name=video.name,weights_sha256=hashlib.sha256(weights.read_bytes()).hexdigest(),fps=fps,width=width,height=height,frames_processed=frame_no,detection_rows=row_count,imgsz=a.imgsz,confidence=a.conf,augment=True,reading='sequential',frame_numbering='one-based; time_seconds=(frame_number_one_based-1)/fps'),indent=2),encoding='utf8')
 print('frames',frame_no,'detections',row_count,'output',out)
if __name__=='__main__':main()
