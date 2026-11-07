from pathlib import Path
import hashlib, json, warnings
import numpy as np
import pandas as pd
import scipy, statsmodels
import statsmodels.formula.api as smf

root=Path(__file__).resolve().parents[2]
folder=root/'04_analysis_data/validation'
outdir=root/'runs/validation';outdir.mkdir(parents=True,exist_ok=True)
source=folder/'逐窗配对及不可判读记录.csv'
old=folder/'一致性统计_口径核验_20261107.csv'
d=pd.read_csv(source); d=d[d.valid.eq(True)].dropna(subset=['model','human']).copy()
d['difference']=d['model']-d['human']; rows=[]
with warnings.catch_warnings():
 warnings.simplefilter('ignore')
 for (part, observer),g in d.groupby(['part','observer'],sort=True):
  fit=smf.mixedlm('difference ~ 1',g,groups=g.fish).fit(reml=True,method='powell',disp=False)
  if not fit.converged: raise RuntimeError((part,observer,'not converged'))
  bias=float(fit.fe_params.iloc[0]); vb=float(fit.cov_re.iloc[0,0]); vw=float(fit.scale); sd=np.sqrt(vb+vw)
  a=g.model.to_numpy(float); b=g.human.to_numpy(float); ccc=2*np.mean((a-a.mean())*(b-b.mean()))/(np.var(a)+np.var(b)+(a.mean()-b.mean())**2)
  rows.append(dict(part=part,observer=int(observer),n_fish=g.fish.nunique(),n_windows=len(g),MAE=np.mean(abs(a-b)),bias=bias,between_fish_variance=vb,within_fish_variance=vw,LoA_lower=bias-1.96*sd,LoA_upper=bias+1.96*sd,CCC=ccc,converged=bool(fit.converged)))
r=pd.DataFrame(rows); previous=pd.read_csv(old); compare=r.merge(previous,on=['part','observer'],suffixes=('_new','_old'),validate='1:1')
for col in ['MAE','bias','LoA_lower','LoA_upper','CCC']:
 delta=(compare[col+'_new']-compare[col+'_old']).abs().max()
 if delta>1e-5:raise AssertionError((col,delta))
out=outdir/'一致性统计_重新计算.csv';r.to_csv(out,index=False,encoding='utf-8-sig')
meta={'source':str(source.relative_to(root)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'method':'difference=model-observer; random-intercept by fish, intercept-only mixed model REML with Powell; single paired-window LoA = fixed intercept ± 1.96*sqrt(between-fish variance + within-fish residual variance); CCC uses pooled paired windows and population moments','bootstrap':'not reproduced; confidence interval columns from previous exploratory file are omitted','comparison':'point estimates reproduce prior exploratory CSV within 1e-5','statsmodels':statsmodels.__version__,'scipy':scipy.__version__,'numpy':np.__version__,'pandas':pd.__version__}
(outdir/'一致性统计_重新计算.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(r[['part','observer','n_fish','n_windows','MAE','bias','LoA_lower','LoA_upper','CCC']].round(4).to_string(index=False))
