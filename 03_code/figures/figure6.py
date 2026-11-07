from pathlib import Path
import cv2, numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2];F=R/'04_analysis_data/movement'; OUT=R/'runs/figures'; OUT.mkdir(parents=True,exist_ok=True)
coords=pd.read_csv(F/'候选四角_自动推定.csv').set_index('video')
fish=pd.read_csv(F/'候选网格_逐鱼覆盖_工作数据.csv')
sheets=pd.read_excel(R/'04_analysis_data/detection_tables/7_中心点轨迹_全身.xlsx',sheet_name=None)
temps=[16,19,21,23,25];colors=['#FEE08B','#FDAE61','#F46D43','#D73027','#A50026'];tracks={};stats=[]
for temp in temps:
 for no in [1,2,3]:
  video=f'{temp}-{no}';c=coords.loc[video];pts=np.float32([[c.tl_x,c.tl_y],[c.tr_x,c.tr_y],[c.br_x,c.br_y],[c.bl_x,c.bl_y]])
  H=cv2.getPerspectiveTransform(pts,np.float32([[0,0],[60,0],[60,45],[0,45]]));df=sheets[f'{temp}℃-{no}'].dropna(subset=['中心点X','中心点Y']);xy=cv2.perspectiveTransform(np.float32(df[['中心点X','中心点Y']].to_numpy()).reshape(-1,1,2),H).reshape(-1,2)
  ok=(xy[:,0]>=0)&(xy[:,0]<=60)&(xy[:,1]>=0)&(xy[:,1]<=45);xy=xy[ok];assert len(xy)>1
  tracks[(temp,no)]=xy;stats.append(dict(temperature_C=temp,fish=no,n=len(xy),mean_y_cm=float(xy[:,1].mean()),sd_y_cm=float(xy[:,1].std(ddof=1))))
ydata=pd.DataFrame(stats)
plt.rcParams.update({'font.family':'Arial','font.size':8,'axes.spines.top':False,'axes.spines.right':False})
fig=plt.figure(figsize=(7.2,4.6));gs=fig.add_gridspec(2,10,height_ratios=[1,1.13],left=.10,right=.97,bottom=.12,top=.91,hspace=.48,wspace=.38);axes=[];rng=np.random.default_rng(0)
for i,temp in enumerate(temps):
 ax=fig.add_subplot(gs[0,2*i:2*i+2]);axes.append(ax)
 for no in [1,2,3]:
  v=tracks[(temp,no)]; idx=rng.choice(len(v),min(len(v),180),replace=False);ax.scatter(v[idx,0],v[idx,1],s=2.5,color=colors[i],alpha=.47,linewidths=0)
 vals=ydata[ydata.temperature_C==temp];mu=vals.mean_y_cm.mean();sd=vals.sd_y_cm.mean()
 ax.axhline(mu,color='#D62728',lw=.8);ax.axhline(mu-sd,color='#D62728',lw=.7,ls='--');ax.axhline(mu+sd,color='#D62728',lw=.7,ls='--')
 ax.set(xlim=(0,60),ylim=(45,0));ax.set_xticks([]);ax.set_yticks([]);ax.set_xlabel(f'{temp} °C',labelpad=3)
 for sp in ax.spines.values():sp.set_visible(True);sp.set_color('#cccccc');sp.set_linewidth(.7)
axes[0].set_ylabel('Mapped tank Y (cm)')
b=fig.add_subplot(gs[1,:5]);c=fig.add_subplot(gs[1,6:]);groups=fish.groupby('temperature_C').visited_percent.agg(['mean','std']).reindex(temps);p=np.arange(5)
b.bar(p,groups['mean'],color=colors,edgecolor='#708090',linewidth=.6,width=.65);b.errorbar(p,groups['mean'],yerr=groups['std'],fmt='none',ecolor='black',capsize=2,lw=.7)
for i,temp in enumerate(temps):
 v=fish[fish.temperature_C==temp].sort_values('fish').visited_percent.to_numpy();b.scatter(i+np.array([-.12,0,.12]),v,c='black',s=10,zorder=4)
 vals=ydata[ydata.temperature_C==temp].sort_values('fish');m=vals.mean_y_cm.to_numpy();sd=vals.sd_y_cm.to_numpy();c.errorbar(m,i+np.array([-.18,0,.18]),xerr=sd,fmt='o',color=colors[i],ecolor=colors[i],markeredgecolor='#333333',markeredgewidth=.45,markersize=3.2,elinewidth=2,capsize=0);c.plot([m.mean(),m.mean()],[i-.31,i+.31],color='#333',ls=':',lw=.8)
b.set_xticks(p,[str(t) for t in temps]);b.set_xlabel('Temperature (°C)');b.set_ylabel('Visited cells (%)');b.set_ylim(0,85)
c.set_yticks(p,[str(t) for t in temps]);c.set_ylim(-.5,4.5);c.set_xlim(0,45);c.set_xlabel('Mapped tank Y (cm)');c.set_ylabel('Temperature (°C)')
fig.canvas.draw();fig.text(.025,axes[0].get_position().y1+.025,'A',fontweight='bold',fontsize=11);fig.text(.025,b.get_position().y1+.02,'B',fontweight='bold',fontsize=11);fig.text(c.get_position().x0,c.get_position().y1+.02,'C',fontweight='bold',fontsize=11)
from matplotlib.text import Text
for obj in fig.findobj(match=Text):
 if obj.get_text().strip(): obj.set_fontsize(max(obj.get_fontsize(), 10.8))
out=OUT/'Figure6.png';fig.savefig(out,dpi=900);plt.close(fig);print(out)
ydata.to_csv(OUT/'Figure6_A_映射Y均值和个体标准差.csv',index=False,encoding='utf-8-sig')
