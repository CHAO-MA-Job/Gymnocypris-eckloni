"""Train YOLO11n on the Time80 split; paths are supplied by the user or resolved within the package."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
INITIAL_SHA256 = '0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1'
CFG = dict(epochs=200, imgsz=640, batch=16, workers=8, optimizer='AdamW',
 lr0=0.0005, lrf=0.00005, momentum=0.937, weight_decay=0.001,
 warmup_epochs=5, warmup_momentum=0.8, warmup_bias_lr=0.1,
 box=0.05, cls=0.6, dfl=0.1, patience=0, close_mosaic=10,
 seed=0, deterministic=True, amp=True, plots=True, val=True,
 hsv_h=0.015, hsv_s=0.7, hsv_v=0.4, translate=0.1, scale=0.5,
 fliplr=0.5, flipud=0.0, mosaic=1.0, mixup=0.0, cutmix=0.0,
 degrees=0.0, shear=0.0, perspective=0.0, nbs=64)

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--dataset',type=Path,default=ROOT/'01_dataset')
 ap.add_argument('--weights',type=Path,default=ROOT/'02_model/yolo11n_pretrained.pt')
 ap.add_argument('--output',type=Path,default=Path('runs'))
 ap.add_argument('--device',default='0',help='CUDA device index, or cpu')
 ap.add_argument('--workers',type=int,default=8)
 ap.add_argument('--name',default='time80_seed0')
 ap.add_argument('--smoke',action='store_true',help='One epoch using 8 training and 4 validation images')
 ap.add_argument('--check-only',action='store_true')
 a=ap.parse_args(); dataset=a.dataset.resolve(); weights=a.weights.resolve(); output=a.output.resolve()
 if not weights.is_file():ap.error('Pretrained weights not found; use --weights PATH')
 digest=hashlib.sha256(weights.read_bytes()).hexdigest()
 print(json.dumps({'dataset':str(dataset),'weights_sha256':digest,'matches_training_initial_weights':digest==INITIAL_SHA256,'output':str(output)},ensure_ascii=False))
 for split in ('train','val'):
  imgs=dataset/'images'/split;labels=dataset/'labels'/split
  if not imgs.is_dir() or not labels.is_dir():ap.error('Missing images or labels for '+split)
  paths=sorted(p for p in imgs.iterdir() if p.suffix.lower() in {'.jpg','.jpeg','.png','.bmp'})
  if not paths:ap.error('Empty split: '+split)
  missing=[p.name for p in paths if not (labels/(p.stem+'.txt')).exists()]
  if missing:ap.error(f'{split} contains images without matching labels: {missing[:5]}')
  print(split,len(paths),'matching image-label pairs')
 if a.check_only:return
 from ultralytics import YOLO
 output.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='fish_time80_') as tmp:
  temp=Path(tmp); data_root=dataset
  if a.smoke:
   data_root=temp/'sample'
   for split,n in [('train',8),('val',4)]:
    (data_root/'images'/split).mkdir(parents=True);(data_root/'labels'/split).mkdir(parents=True)
    for src in sorted((dataset/'images'/split).glob('*'))[:n]:
     shutil.copy2(src,data_root/'images'/split/src.name)
     shutil.copy2(dataset/'labels'/split/(src.stem+'.txt'),data_root/'labels'/split/(src.stem+'.txt'))
  data={'path':str(data_root),'train':'images/train','val':'images/val','nc':8,'names':[str(i) for i in range(1,9)]}
  yaml_path=temp/'data.yaml';yaml_path.write_text(yaml.safe_dump(data,sort_keys=False),encoding='utf8')
  cfg=CFG.copy();cfg.update(data=str(yaml_path),device=a.device,workers=a.workers,project=str(output),name=a.name,exist_ok=False)
  if a.smoke:cfg.update(epochs=1,batch=2,workers=0,amp=False,plots=False,close_mosaic=0)
  YOLO(str(weights)).train(**cfg)
if __name__=='__main__':main()
