from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "04_analysis_data/movement"
out = ROOT / "runs/figures"
out.mkdir(parents=True, exist_ok=True)
d = pd.read_csv(DATA / "Figure5_窗口速度波动_逐窗数据.csv")
f = pd.read_csv(DATA / "Figure5_窗口速度波动_逐鱼数据.csv")
assert f.video.nunique() == 15

plt.rcParams.update({'font.family':'Arial','font.size':8.5,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'axes.linewidth':.8,'axes.spines.top':False,'axes.spines.right':False})
colors=['#FEE08B','#FDAE61','#F46D43','#D73027','#A50026'];temps=[16,19,21,23,25]
fig,(ax,bx)=plt.subplots(1,2,figsize=(7.1,3.25),gridspec_kw={'width_ratios':[1.25,1]},layout='constrained')
for i,(t,c) in enumerate(zip(temps,colors)):
 vals=d.loc[d.temperature_C==t,'speed_sd_cm_s'].to_numpy()
 ax.boxplot([vals],positions=[i],widths=.55,patch_artist=True,showfliers=True,medianprops={'color':'black','linewidth':.9},boxprops={'facecolor':c,'alpha':.75,'edgecolor':'#708090','linewidth':.7},flierprops={'marker':'.','markersize':2,'markerfacecolor':'#777777','markeredgecolor':'none','alpha':.35},whiskerprops={'color':'#708090'},capprops={'color':'#708090'})
 ff=f[f.temperature_C==t].sort_values('video').mean_window_sd.to_numpy()
 bx.bar(i,ff.mean(),width=.6,color=c,edgecolor='#708090',linewidth=.7,alpha=.85);bx.errorbar(i,ff.mean(),yerr=ff.std(ddof=1),fmt='none',ecolor='black',capsize=2.6,lw=.9)
 bx.scatter(i+np.array([-.14,0,.14]),ff,s=17,c='black',linewidths=0,zorder=3)
for axx in (ax,bx):axx.set_xticks(range(5),[str(i) for i in temps]);axx.set_xlabel('Temperature (°C)')
ax.set_ylabel('Within-window speed SD (cm/s)');bx.set_ylabel('Mean window speed SD (cm/s)')
for axx,label in ((ax,'A'),(bx,'B')):axx.text(-.17,1.04,label,transform=axx.transAxes,fontsize=11,fontweight='bold')
from matplotlib.text import Text
fig.canvas.draw()
for obj in fig.findobj(match=Text):
 if obj.get_text().strip(): obj.set_fontsize(max(obj.get_fontsize(), 10.7))
fig.savefig(out/'Figure5.png',dpi=900,facecolor='white');plt.close(fig)
