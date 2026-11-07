# -*- coding: utf-8 -*-
"""Figure 3 candidate: Time80 training, class confusion and manual fish positions."""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

ROOT=Path(__file__).resolve().parents[2]
train=ROOT/'02_model/results.csv'
positions=ROOT/'04_analysis_data/validation/逐时刻两观察者模型对照_预览.csv'
metrics=ROOT/'04_analysis_data/validation/逐鱼对照指标_两观察者模型_预览.csv'
matrix_png=ROOT/'02_model/confusion_matrix.png'
out=ROOT/'runs/figures/Figure3.png'
out.parent.mkdir(parents=True,exist_ok=True)
t=pd.read_csv(train); d=pd.read_csv(positions); p=pd.read_csv(metrics)
assert len(t)==200 and len(d)==2700 and p.fish.nunique()==15
assert d.groupby('fish').size().eq(180).all()
assert int(d.model_ok.sum())==2663
# Source: recorded confusion matrix image, prediction rows and reference columns.
M=np.zeros((9,9),dtype=int)
M[0,0]=635
M[1,1],M[1,2],M[1,8]=361,73,28
M[2,1],M[2,2],M[2,3],M[2,8]=13,168,1,47
M[3,3],M[3,4],M[3,8]=258,89,55
M[4,3],M[4,4],M[4,8]=59,224,59
M[5,5],M[5,6],M[5,7],M[5,8]=104,26,13,17
M[6,5],M[6,6],M[6,7],M[6,8]=26,240,20,32
M[7,5],M[7,6],M[7,7],M[7,8]=29,37,140,34
M[8,1],M[8,2],M[8,3],M[8,4]=5,15,3,1
assert np.array_equal(M[:,:8].sum(axis=0),[635,379,256,321,314,159,303,173])
mpl=matplotlib
mpl.rcParams.update({'font.family':'Arial','font.size':8.3,'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.8,'xtick.major.width':.7,'ytick.major.width':.7,'legend.fontsize':8,'figure.facecolor':'white','savefig.facecolor':'white'})
red='#D62728'; orange='#F4A460'; blue='#708090'; black='#414141'
fig=plt.figure(figsize=(7.1,8.9))
outer=fig.add_gridspec(3,1,height_ratios=[1.18,1.6,2.2],left=.085,right=.97,top=.965,bottom=.075,hspace=.36)
top=outer[0].subgridspec(1,3,wspace=.50)
axes=[fig.add_subplot(top[0,i]) for i in range(3)]
ax=axes[0]
for kind,color,ls in [('train',orange,'-'),('val',red,'--')]:
 cols=[f'{kind}/box_loss',f'{kind}/cls_loss',f'{kind}/dfl_loss']
 ax.plot(t.epoch,t[cols].sum(axis=1),color=color,lw=1.3,ls=ls,label='Training' if kind=='train' else 'Validation')
ax.set(xlabel='Epoch',ylabel='Total loss',xlim=(0,200));ax.legend(loc='upper right',handlelength=1.7)
ax=axes[1]
ax.plot(t.epoch,t['metrics/mAP50(B)'],color=red,lw=1.3,label='mAP@0.50')
ax.plot(t.epoch,t['metrics/mAP50-95(B)'],color=blue,lw=1.3,label='mAP@0.50–0.95')
ax.set(xlabel='Epoch',ylabel='mAP',xlim=(0,200),ylim=(0,1));ax.legend(loc='lower right',handlelength=1.7)
ax=axes[2]
ax.plot(t.epoch,t['metrics/precision(B)'],color=orange,lw=1.3,label='Precision')
ax.plot(t.epoch,t['metrics/recall(B)'],color=red,lw=1.3,ls='--',label='Recall')
ax.set(xlabel='Epoch',ylabel='Score',xlim=(0,200),ylim=(0,1));ax.legend(loc='lower right',handlelength=1.7)
for ax,label in zip(axes,'ABC'):
 ax.text(-.22,1.05,label,transform=ax.transAxes,fontweight='bold',fontsize=11,va='bottom')
 ax.xaxis.set_major_locator(MaxNLocator(4));ax.yaxis.set_major_locator(MaxNLocator(5))
mid=outer[1].subgridspec(1,2,width_ratios=[1.22,1.38],wspace=.30)
ax=fig.add_subplot(mid[0,0]);im=ax.imshow(M,cmap='OrRd',vmin=0,vmax=635,interpolation='nearest')
for i in range(9):
 for j in range(9):
  if M[i,j]: ax.text(j,i,str(M[i,j]),ha='center',va='center',fontsize=7,color='white' if M[i,j]>330 else black)
labs=[str(i) for i in range(1,9)]+['BG']
ax.set_xticks(range(9),labs);ax.set_yticks(range(9),labs)
ax.tick_params(length=0,pad=2);ax.set(xlabel='Reference class',ylabel='Predicted class')

ax.text(-.25,1.05,'D',transform=ax.transAxes,fontweight='bold',fontsize=11,va='bottom')
for side in ['top','right','left','bottom']:ax.spines[side].set_visible(False)
ax=fig.add_subplot(mid[0,1]);temps=[16,19,21,23,25]
for k,temp in enumerate(temps):
 g=p[p.fish.str.startswith(f'{temp}-')].copy()
 for j,(_,row) in enumerate(g.sort_values('fish').iterrows()):
  ax.scatter(k+[-.15,0,.15][j],row.model_vs_obs1_dist_mean,s=28,facecolor=orange,edgecolor=blue,lw=.8,zorder=3)
 ax.hlines(g.model_vs_obs1_dist_mean.mean(),k-.25,k+.25,color=red,lw=1.5,zorder=2)
ax.set_xticks(range(5),[str(v) for v in temps])
ax.set(xlabel='Temperature (°C)',ylabel='Mean centre distance (px)',ylim=(0,22))
ax.yaxis.set_major_locator(MaxNLocator(5))
ax.text(-.16,1.05,'E',transform=ax.transAxes,fontweight='bold',fontsize=11,va='bottom')


bottom=outer[2].subgridspec(3,5,wspace=.16,hspace=.24)
track_axes=[]
for row in range(3):
 for k,temp in enumerate(temps):
  ax=fig.add_subplot(bottom[row,k]);track_axes.append(ax)
  fish=f'{temp}-{row+1}'
  z=d[d.fish.eq(fish)].sort_values('sample_second')
  assert len(z)==180 and z.sample_second.iloc[0]==180 and z.sample_second.iloc[-1]==359
  ax.plot(z.obs1_cx,z.obs1_cy,color=blue,lw=1.35,alpha=.85)
  ax.plot(z.model_cx,z.model_cy,color=orange,lw=.95,ls='--',alpha=.95)
  ax.set_xlim(0,1920);ax.set_ylim(1080,0);ax.set_aspect('equal')
  if row==0:ax.set_title(f'{temp} °C',fontsize=8.3,pad=3)
  ax.text(.035,.94,fish,transform=ax.transAxes,ha='left',va='top',fontsize=7.7)
  ax.set_xticks([0,1000]);ax.set_yticks([0,500,1000]);ax.tick_params(length=2,pad=1,labelsize=7.5)
  if k:ax.set_yticklabels([])
  else:ax.set_ylabel('Y (px)',labelpad=2)
  if row<2:ax.set_xticklabels([])
  else:ax.set_xlabel('X (px)',labelpad=2)
  for side in ['top','right']:ax.spines[side].set_visible(True);ax.spines[side].set_color('#d5d5d5')
pos=track_axes[0].get_position()
legend_y=pos.y1+.035
fig.text(.018,legend_y,'F',fontsize=11,fontweight='bold',ha='left',va='center')
fig.text(.085,legend_y,'03:00–06:00 · one position per second',fontsize=8.3,ha='left',va='center')
fig.legend([Line2D([0],[0],color=blue,lw=1.7),Line2D([0],[0],color=orange,lw=1.2,ls='--')],['Manual','Model'],ncol=2,frameon=False,loc='center right',bbox_to_anchor=(.975,legend_y),handlelength=2,columnspacing=1.2)
from matplotlib.text import Text
fig.canvas.draw()
for obj in fig.findobj(match=Text):
 if obj.get_text().strip(): obj.set_fontsize(max(obj.get_fontsize(), 10.7))
fig.savefig(out,dpi=900,facecolor='white')
plt.close(fig)
payload={'figure':'Figure 3 working candidate','sources_sha256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in (train,positions,metrics,matrix_png)},'trajectory_examples':[f'{x}-{j}' for j in (1,2,3) for x in temps],'trajectory_window_seconds':'[180,360), one per second','missing_model':'missing values remain gaps','points':'one fish; mean matched-time centre distance in original image pixels','center_bars':'mean of three fish means','matrix':'manually transcribed from supplied raw confusion_matrix.png and validated by per-class reference totals; row=predicted, column=reference; matching thresholds pending historical verification','observer':'first manually labelled boxes only','export':'900 DPI at 7.1 by 8.9 inches'}
(out.parent/'Figure3_绘图数据来源.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
print('Saved',out)
