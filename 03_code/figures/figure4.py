from pathlib import Path
import csv, re
import numpy as np
from scipy.stats import gaussian_kde
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

R=Path(__file__).resolve().parents[2]
BASE=R/'04_analysis_data/movement'
CACHE=BASE/'_traj_cache_stable.npz'
SENS=BASE/'SG5_SG10_20261106/逐鱼平滑对照.csv'
OUT=R/'runs/figures/Figure4.png'
OUT.parent.mkdir(parents=True,exist_ok=True)
# Rebuild the existing figure from the recorded source data.
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
main=read(BASE/'完整录像_图件源数据/15尾鱼_完整录像运动指标.csv')
smooth=read(SENS)
scales={r['video']:float(r['approx_cm_per_px']) for r in main}
assert len(main)==15 and len(smooth)==45 and len(scales)==15
for r in main:
    value=float(next(s['mean_speed_cm_s'] for s in smooth if s['video']==r['video'] and s['method']=='raw'))
    assert abs(value-float(r['mean_speed_cm_s']))<1e-5
z=np.load(CACHE,allow_pickle=True)
names=[str(x) for x in z['names']]
data={n:(z[f't{i}'],z[f'x{i}'],z[f'y{i}']) for i,n in enumerate(names)}
def key(n):
    m=re.search(r'(\d+)\s*℃\s*-\s*(\d+)',n)
    assert m,n
    return int(m.group(2)),int(m.group(1))
names.sort(key=key)
assert len(names)==15 and {n.replace('℃','') for n in names}==set(scales)
temps=(16,19,21,23,25); colors=('#FEE08B','#FDAE61','#F46D43','#D73027','#A50026')
x0=min(d[1].min() for d in data.values());x1=max(d[1].max() for d in data.values())
y0=min(d[2].min() for d in data.values());y1=max(d[2].max() for d in data.values())
dx=(x1-x0)*.05;dy=(y1-y0)*.05;x0-=dx;x1+=dx;y0-=dy;y1+=dy
gx,gy=np.mgrid[x0:x1:200j,y0:y1:200j];points=np.vstack([gx.ravel(),gy.ravel()])
plt.rcParams.update({'font.family':'Arial','font.size':8.5,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.linewidth':.8,'savefig.facecolor':'white'})
fig=plt.figure(figsize=(7.1,7.2),facecolor='white')
grid=fig.add_gridspec(3,5,left=.095,right=.84,bottom=.555,top=.94,wspace=.075,hspace=.08)
cmap=matplotlib.colormaps['OrRd']; im=None
for i,name in enumerate(names):
    row,col=divmod(i,5);t,x,y=data[name];assert np.all(np.diff(t)>=0)
    kde=gaussian_kde(np.vstack([x[::5],y[::5]]),bw_method=.18)
    density=np.concatenate([kde(points[:,j:j+4000]) for j in range(0,points.shape[1],4000)]).reshape(gx.shape)
    density/=density.max()
    ix=np.clip(((x-x0)/(x1-x0)*199).round().astype(int),0,199)
    iy=np.clip(((y-y0)/(y1-y0)*199).round().astype(int),0,199)
    v=density[ix,iy]; keep=np.diff(t)<=1.5
    ax=fig.add_subplot(grid[row,col]);im=ax.pcolormesh(gx,gy,density,shading='auto',cmap='OrRd',vmin=0,vmax=1,rasterized=True)
    if keep.any():
        xy=np.column_stack([x,y]);segments=np.stack([xy[:-1][keep],xy[1:][keep]],axis=1)
        ax.add_collection(LineCollection(segments,colors=cmap(.28+.72*v[:-1][keep]),linewidths=.28,zorder=3))
    ax.scatter(x[0],y[0],s=9,c='#F4A460',edgecolors='white',linewidths=.5,zorder=5)
    ax.scatter(x[-1],y[-1],s=9,c='#D62728',edgecolors='white',linewidths=.5,zorder=5)
    ax.set(xlim=(x0,x1),ylim=(y1,y0));ax.set_aspect('equal')
    ax.set_xticks([(x0+x1)/2],[str(temps[col])] if row==2 else [])
    ax.set_yticks([(y0+y1)/2],[str(row+1)] if col==0 else [])
    ax.tick_params(length=0,pad=2,labelsize=8)
    for spine in ax.spines.values():spine.set(color='#cccccc',linewidth=.6)
    L=5/scales[name.replace('℃','')]; bx=x0+dx*.6; by=y1-dy*1.2
    ax.plot([bx,bx+L],[by,by],color='black',lw=1.4,solid_capstyle='butt',zorder=6)
    
    print('trajectory',name,flush=True)
fig.text(.02,.965,'A',fontsize=11,fontweight='bold',va='top')
fig.text(.015,.75,'Fish',rotation=90,va='center',fontsize=9)
fig.text(.46,.52,'Temperature (°C)',ha='center',fontsize=9)
legend=[Line2D([],[],marker='o',ls='',ms=4,mfc=c,mec='white',label=l) for c,l in [('#F4A460','Start'),('#D62728','End')]]
legend.append(Line2D([0],[0],color='black',lw=1.5,label='Scale bar: ~5 cm'))
fig.legend(handles=legend,loc='upper center',bbox_to_anchor=(.46,.99),ncol=3,frameon=False,handletextpad=.3)
cax=fig.add_axes([.865,.59,.012,.31]);cb=fig.colorbar(im,cax=cax);cb.set_label('Relative density (per fish)',fontsize=9);cb.ax.tick_params(labelsize=8,length=0)
ax=fig.add_axes([.11,.09,.73,.345]);ax2=ax.twinx();ax.set_zorder(2);ax.patch.set_alpha(0);ax2.set_zorder(1)
vmeans=[];vstd=[];pmeans=[];pstd=[]
for i,(temp,color) in enumerate(zip(temps,colors)):
    sub=[r for r in main if int(r['temperature_C'])==temp];assert len(sub)==3
    vs=np.array([float(r['mean_speed_cm_s']) for r in sub]);ps=np.array([float(r['cumulative_path_cm']) for r in sub])
    vmeans.append(vs.mean());vstd.append(vs.std(ddof=1));pmeans.append(ps.mean());pstd.append(ps.std(ddof=1))
    ax.bar(i,vs.mean(),width=.58,color='#F4A460',alpha=.9,zorder=1)
    ax.errorbar(i,vs.mean(),yerr=vs.std(ddof=1),fmt='none',ecolor='#777777',capsize=2.5,lw=.9,zorder=2)
    ax.scatter(i+np.array([-.14,0,.14]),vs,s=17,color=color,edgecolors='#555555',linewidths=.4,zorder=3)
ax2.errorbar(range(5),pmeans,yerr=pstd,color='#708090',marker='D',markersize=4,lw=1.5,capsize=2.5,zorder=3)
ax.set(xticks=range(5),xticklabels=temps,xlabel='Temperature (°C)',ylabel='Mean projected speed (cm/s)',ylim=(0,10.5),xlim=(-.55,4.55))
ax2.set(ylabel='Cumulative projected path (cm)',ylim=(0,6500));ax.spines['top'].set_visible(False);ax2.spines['top'].set_visible(False)
fig.text(.02,.45,'B',fontsize=11,fontweight='bold',va='top')
ax.legend(handles=[Patch(facecolor='#F4A460',alpha=.9,label='Mean speed'),Line2D([0],[0],color='#708090',marker='D',markersize=4,label='Cumulative path')],loc='upper right',frameon=False)
ins=ax.inset_axes([.075,.57,.41,.36]);ins.set_facecolor('white')
for method,label,color,marker in [('raw','Raw','#707070','o'),('SG5','SG5','#F4A460','s'),('SG10','SG10','#D62728','^')]:
    vals=[np.mean([float(r['mean_speed_cm_s']) for r in smooth if int(r['temperature_C'])==t and r['method']==method]) for t in temps]
    ins.plot(range(5),vals,marker=marker,color=color,linewidth=1,markersize=3.5,label=label)
ins.set(xticks=range(5),xticklabels=temps,ylim=(1.5,8.5),ylabel='Speed (cm/s)')
ins.tick_params(labelsize=8,direction='in');ins.xaxis.label.set_size(8);ins.yaxis.label.set_size(8)
ins.spines[['top','right']].set_visible(False)
from matplotlib.text import Text
fig.canvas.draw()
for obj in fig.findobj(match=Text):
 if obj.get_text().strip(): obj.set_fontsize(max(obj.get_fontsize(), 10.7))
fig.savefig(OUT,dpi=900);plt.close(fig)
print('SAVED',OUT,flush=True)

