"""Nature-inspired, data-preserving artwork from audited derived CSVs.

Uses SciencePlots' pinned MIT-licensed science/nature styles, with no-LaTeX
rendering and journal-specific layout overrides. Nature does not endorse the
style repository. Vector PDFs/SVGs retain text; PNG companions are native1200dpi.
"""
from pathlib import Path
import hashlib
import itertools
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, FancyArrowPatch, Patch
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from runtime import ROOT, RAW, REPO_ROOT, load_parameters
OUT=ROOT/'results/figures'
QA=ROOT/'results/nature_figures_qa'
STYLE=REPO_ROOT/'scripts/styles'
W=160/25.4
BLUE='#0072B2'; ORANGE='#D55E00'; GREEN='#008875'; PURPLE='#8064A2'; GREY='#68717A'
records=[]


def configure():
    plt.style.use([str(STYLE/'science.mplstyle'),str(STYLE/'no-latex.mplstyle'),str(STYLE/'nature.mplstyle')])
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial'],
        'mathtext.fontset':'custom','mathtext.rm':'Arial','mathtext.it':'Arial:italic',
        'mathtext.bf':'Arial:bold','font.size':7,'axes.titlesize':7,'axes.labelsize':7,
        'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,
        'axes.linewidth':.55,'lines.linewidth':.9,'lines.markersize':3.4,
        'axes.spines.top':False,'axes.spines.right':False,'axes.grid':False,
        'xtick.top':False,'ytick.right':False,'xtick.minor.visible':False,
        'ytick.minor.visible':False,'xtick.direction':'out','ytick.direction':'out',
        'xtick.major.size':2.6,'ytick.major.size':2.6,'axes.labelpad':4,
        'text.color':'#242424','axes.labelcolor':'#242424','xtick.color':'#242424',
        'ytick.color':'#242424','pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none',
        'savefig.bbox':None,'savefig.facecolor':'white','figure.facecolor':'white',
        'figure.constrained_layout.use':False})


def panel(ax,letter,title):
    ax.text(0,1.14,letter,transform=ax.transAxes,fontweight='bold',fontsize=8,va='bottom')
    ax.text(.065,1.14,title,transform=ax.transAxes,fontsize=7,va='bottom')


def text_audit(fig):
    """Detect text-text and DATA-line-text intersections in display coordinates.

    This is conservative geometric QA, not a substitute for visual inspection.
    Tick marks, expected box interiors and image/color fill are not data lines.
    """
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    skipped=set()
    for ax in fig.axes:
        for axis in [ax.xaxis,ax.yaxis]:
            lo,hi=sorted(axis.get_view_interval())
            for tick in [*axis.get_major_ticks(),*axis.get_minor_ticks()]:
                if tick.get_loc()<lo-1e-10 or tick.get_loc()>hi+1e-10:
                    skipped.update([tick.label1,tick.label2])
    texts=[t for t in fig.findobj(Text) if t not in skipped and t.get_visible() and t.get_text().strip()]
    entries=[(t,t.get_window_extent(renderer)) for t in texts]
    overlap=[]
    for (ta,ba),(tb,bb) in itertools.combinations(entries,2):
        # A positive interior intersection, not touching bounding edges.
        inter=Bbox.intersection(ba,bb)
        if inter is not None and inter.width>.6 and inter.height>.6:
            overlap.append([ta.get_text(),tb.get_text(),round(inter.width,2),round(inter.height,2)])
    intersections=[]
    for ax in fig.axes:
        for line in ax.lines:
            if not line.get_visible() or line.get_linestyle() in {'None','none',''}:
                continue
            xy=line.get_transform().transform(line.get_xydata())
            for text,box in entries:
                for p0,p1 in zip(xy[:-1],xy[1:]):
                    if not np.isfinite([*p0,*p1]).all():continue
                    # Clip the rendered data segment against text rectangle.
                    delta=p1-p0;tlo,thi=0.,1.
                    for k in [0,1]:
                        low,high=(box.x0,box.x1) if k==0 else (box.y0,box.y1)
                        if abs(delta[k])<1e-12:
                            if not low < p0[k] < high:tlo,thi=1.,0.;break
                        else:
                            a,b=(low-p0[k])/delta[k],(high-p0[k])/delta[k]
                            tlo=max(tlo,min(a,b));thi=min(thi,max(a,b))
                    if thi>tlo+1e-8:
                        mid=p0+(tlo+thi)/2*delta
                        # Axes clip data paths; a continuation beyond the frame
                        # is not a rendered line crossing an exterior label.
                        if not line.get_clip_on() or ax.bbox.contains(*mid):
                            intersections.append([line.get_label(),text.get_text()]);break
    return dict(text_labels=len(entries),text_text_intersections=overlap,data_line_text_intersections=intersections)


def save(fig,name):
    OUT.mkdir(exist_ok=True);QA.mkdir(exist_ok=True)
    geometry=text_audit(fig)
    fig.savefig(OUT/f'{name}.pdf')
    fig.savefig(OUT/f'{name}.svg')
    fig.savefig(OUT/f'{name}.png',dpi=1200)
    fig.savefig(QA/f'{name}_preview.png',dpi=220)
    records.append(dict(name=name,width_mm=fig.get_figwidth()*25.4,height_mm=fig.get_figheight()*25.4,
        vector_pdf_sha256=hashlib.sha256((OUT/f'{name}.pdf').read_bytes()).hexdigest(),
        vector_svg_sha256=hashlib.sha256((OUT/f'{name}.svg').read_bytes()).hexdigest(),
        png_dpi=1200,geometry=geometry))
    plt.close(fig)


def architecture():
    fig,ax=plt.subplots(figsize=(W,76/25.4));fig.subplots_adjust(left=.01,right=.99,bottom=.02,top=.98)
    ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    boxes=[(.035,.71,.255,.18,'Grid electricity\nPlant-gate input',BLUE),
           (.373,.71,.255,.18,'PEM and compression\nPublished relations',BLUE),
           (.711,.71,.255,.18,'Usable H$_2$ buffer\n75–140 bar',BLUE),
           (.035,.20,.255,.18,'CO$_2$ inventory\nFinite design stock',GREEN),
           (.373,.20,.255,.18,'Continuous synthesis\n20% floor; 5%/h ramp',GREEN),
           (.711,.20,.255,.18,'Methanol inventory\nDaily bulk delivery',GREEN)]
    for x,y,w,h,text,c in boxes:
        ax.add_patch(Rectangle((x,y),w,h,facecolor='white',edgecolor=c,linewidth=.75))
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',linespacing=1.4)
    for x0,x1,y in [(.294,.367,.80),(.632,.705,.80),(.294,.367,.29),(.632,.705,.29)]:
        ax.add_patch(FancyArrowPatch((x0,y),(x1,y),arrowstyle='->',mutation_scale=6,lw=.65,color=GREY))
    ax.text(.1625,.535,'Primary and firm backup\nQualified gate CO$_2$',ha='center',va='center',linespacing=1.4)
    ax.add_patch(FancyArrowPatch((.1625,.465),(.1625,.389),arrowstyle='->',mutation_scale=6,lw=.65,color=GREY))
    ax.plot([.8385,.8385,.5005],[.70,.495,.495],color=GREY,lw=.65)
    ax.add_patch(FancyArrowPatch((.5005,.495),(.5005,.389),arrowstyle='->',mutation_scale=6,lw=.65,color=GREY))
    ax.text(.5,.052,'Low-load survival  →  On-time product delivery  →  Restored inventories',ha='center',va='center')
    save(fig,'fig1_architecture')


def fair_frontier():
    data=pd.read_csv(ROOT/'results/fair_reference_frontiers/summary.csv')
    fig,ax=plt.subplots(figsize=(W,76/25.4));fig.subplots_adjust(left=.12,right=.985,bottom=.18,top=.81)
    x=np.arange(2);width=.22
    for i,name in enumerate(['fixed_price_profile','flat_contract_mean','adjustable']):
        vals=[float(data.loc[(data.case==name)&(data.outage_h==h),'backup_capacity_t_day'].iloc[0]) for h in [336,504]]
        pos=x+(i-1)*width
        ax.bar(pos,vals,width,color=[GREY,BLUE,GREEN][i],linewidth=0,label=['Fixed price profile','Flat mean production','Adjustable production'][i])
        for xx,val in zip(pos,vals):ax.text(xx,val+4,f'{val:.2f}',ha='center',va='bottom')
    reductions=[]
    for hours in [336,504]:
        block=data[data.outage_h==hours].set_index('case')
        reductions.append(100*(1-block.loc['adjustable','backup_capacity_t_day']/block.loc['fixed_price_profile','backup_capacity_t_day']))
    for xx,pct in zip(x,reductions):
        ax.text(xx,294,f'{pct:.2f}% less than fixed profile',ha='center',fontsize=7,color=GREEN)
    ax.set(xticks=x,xticklabels=['14-day interruption','21-day interruption'],ylabel='Firm CO$_2$ backup (t d$^{-1}$)',ylim=(0,310),yticks=[0,100,200,300])
    fig.legend(*ax.get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.55,.985),ncol=3,columnspacing=1.8,handlelength=1.1)
    save(fig,'fig2_fair_frontier')


def recovery_window():
    data=pd.read_csv(ROOT/'results/recovery_window_frontier/summary.csv')
    fig,axes=plt.subplots(1,2,figsize=(W,77/25.4),sharey=True);fig.subplots_adjust(left=.115,right=.985,bottom=.19,top=.73,wspace=.18)
    for ax,days,letter in zip(axes,[14,21],['a','b']):
        sub=data[data.outage_days==days].sort_values('recovery_days')
        ax.plot(sub.recovery_days,sub.carbon_terminal_recovery,'--',color=ORANGE,lw=.8,label='Restoration bound')
        ax.axhline(sub.last_outage_delivery.iloc[0],color=GREEN,ls=':',lw=.9,label='Delivery bound')
        ax.plot(sub.recovery_days,sub.backup_capacity_t_day,'o',markerfacecolor='white',markeredgewidth=.8,color=BLUE,label='Optimized backup',zorder=4)
        ax.set(xlabel='Recovery window (d)',ylim=(210,276),yticks=[220,240,260],xticks=[0,14,28,42]);panel(ax,letter,f'{days}-day interruption')
    axes[0].set_ylabel('Firm CO$_2$ backup (t d$^{-1}$)')
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.55,.985),ncol=3,columnspacing=1.8,handlelength=1.9)
    save(fig,'fig3_recovery_window')


def process_limits():
    data=pd.read_csv(ROOT/'results/process_service_frontier/summary.csv')
    fig,axes=plt.subplots(1,2,figsize=(W,79/25.4));fig.subplots_adjust(left=.115,right=.985,bottom=.19,top=.70,wspace=.31)
    for ramp,color,marker in zip([.01,.05,.10],[BLUE,ORANGE,GREEN],['o','s','^']):
        sub=data[data['case'].str.startswith('C0')&(data.ramp==ramp)].sort_values('carbon_initial')
        axes[0].plot(sub.carbon_initial,sub.backup_capacity_t_day,marker+'-',color=color,markerfacecolor='white',markeredgewidth=.7,label=f'{ramp:.0%} nominal h$^{{-1}}$')
    axes[0].set(xlabel='Opening CO$_2$ stock (t)',ylabel='Firm CO$_2$ backup (t d$^{-1}$)',ylim=(228,273),xticks=[0,120,240,360]);panel(axes[0],'a','Ramp and opening stock')
    axes[0].legend(loc='lower center',bbox_to_anchor=(.5,1.035),ncol=3,fontsize=6,handlelength=1.4,columnspacing=.6)
    lead=data[data['case'].str.startswith('backup_lead')].sort_values('backup_lead_h')
    ok=lead[lead.success]
    default=float(data.loc[data['case'].str.startswith('C0')&(data.carbon_initial==288)&(data.ramp==.05),'backup_capacity_t_day'].iloc[0])
    axes[1].plot([0,*ok.backup_lead_h],[default,*ok.backup_capacity_t_day],'o-',color=BLUE,markerfacecolor='white',markeredgewidth=.8)
    axes[1].axvspan(72,104,facecolor='#eef0f2',zorder=0)
    axes[1].set(xlabel='Backup response delay (h)',ylim=(228,273),xlim=(-3,104),xticks=[0,24,48,72,96]);panel(axes[1],'b','Backup response')
    axes[1].legend(handles=[Patch(facecolor='#eef0f2',label='No full service at 72/96 h')],loc='lower center',bbox_to_anchor=(.5,1.035),handlelength=1.3,fontsize=6)
    save(fig,'fig4_process_boundaries')


def causal_service():
    names=['mpc','credit_mpc','certificate_mpc','guard']
    fig,axes=plt.subplots(2,1,figsize=(W,102/25.4),sharex=True);fig.subplots_adjust(left=.135,right=.985,bottom=.125,top=.82,hspace=.28)
    for name,c,ls,label in zip(names,[GREY,ORANGE,GREEN,PURPLE],['-','--','-',':'],['Price MPC','Delivery-only MPC','Joint MPC','Feasible-tail benchmark']):
        t=pd.read_csv(ROOT/f'results/causal_DK1_60d_21out_{name}_8seg_rolling/{name}_trace.csv')
        h=np.arange(len(t))/24
        axes[0].plot(h,t.C+1.5494*t.M,label=label,color=c,ls=ls,lw=.8)
        axes[1].plot(h,t.shortfall.cumsum(),color=c,ls=ls,lw=.9)
    for ax in axes:
        ax.axvspan(0,21,color='#f0f1f3',zorder=0)
        ax.axvline(21,color='#9aa2a8',ls=':',lw=.55)
        ax.set_xlim(0,60)
    axes[0].set_ylabel('CO$_2$-equivalent\nstock credit (t)');panel(axes[0],'a','Combined inventory')
    axes[1].set(ylabel='Cumulative shortfall (t)',xlabel='Episode time (d)');panel(axes[1],'b','Missed methanol delivery')
    fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.55,.985),ncol=2,columnspacing=2.8,handlelength=2.)
    save(fig,'fig5_causal_service')


def source_transfer():
    native=pd.read_csv(ROOT/'results/native_service_boundaries/summary.csv')
    affine=pd.read_csv(ROOT/'results/product_service_pilot/pilot_summary.csv')
    fig,ax=plt.subplots(figsize=(W,74/25.4));fig.subplots_adjust(left=.115,right=.985,bottom=.19,top=.76)
    x=np.array([1.,1.05,1.15,1.4])
    mean=native.loc[(native.outage_h==504)&(native.replenish_factor==1),'backup_capacity_t_day'].iloc[0]
    vals=[native.loc[(native.outage_h==504)&(native.replenish_factor==r),'backup_capacity_t_day'].iloc[0]/mean for r in x]
    ax.plot(x,vals,'o-',label='Published-process reference',color=BLUE,markerfacecolor='white',markeredgewidth=.8)
    mean=affine.loc[affine['case']=='replenishment_factor_1.0','backup_capacity_t_day'].iloc[0]
    vals=[affine.loc[affine['case']==f'replenishment_factor_{r}','backup_capacity_t_day'].iloc[0]/mean for r in x]
    ax.plot(x,vals,'s--',label='Giehl-derived affine transfer',color=ORANGE,markerfacecolor='white',markeredgewidth=.8)
    ax.set(xlabel='Recovered supply / ongoing mean feed',ylabel='Backup / mean feed',ylim=(.65,1.03),xticks=[1,1.1,1.2,1.3,1.4])
    fig.legend(*ax.get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.55,.985),ncol=2,columnspacing=2.,handlelength=2.)
    save(fig,'fig6_accounting_transfer')


def reserve_screen():
    data=pd.read_csv(ROOT/'results/normalized_reserve_screen/unique_scenarios.csv')
    feasible=data[data.feasible]
    fig,axes=plt.subplots(1,2,figsize=(W,84/25.4));fig.subplots_adjust(left=.115,right=.985,bottom=.19,top=.74,wspace=.44)
    ax=axes[0];s=np.linspace(0,.45,60);rho=np.linspace(0,1.4,95);ss,rr=np.meshgrid(s,rho)
    surface=np.maximum.reduce([np.zeros_like(ss),1-ss,1-rr])
    image=ax.contourf(ss,rr,surface,levels=np.linspace(.55,1.,10),cmap='cividis')
    ax.plot(s,s,color='white',lw=.8)
    default=feasible[(feasible.backup_delay_h==0)&feasible.batch.isin(['native_service_boundaries','recovery_window_frontier'])]
    ax.scatter(default.stock_ratio,default.recovery_ratio,s=10,facecolor='white',edgecolor='#242424',linewidth=.5,zorder=4)
    assert default.recovery_ratio.max()<1.4
    ax.set(xlabel=r'Opening stock ratio $s$',ylabel=r'Recovery surplus ratio $\rho$',xlim=(0,.45),ylim=(0,1.4),xticks=[0,.2,.4],yticks=[0,.35,.7,1.05,1.4]);panel(ax,'a','Stock–recovery screen')
    bar=fig.colorbar(image,ax=ax,pad=.025,shrink=.9,fraction=.06,ticks=[.6,.8,1.]);bar.ax.tick_params(labelsize=6);bar.set_label('Necessary U/f',fontsize=6,labelpad=2)
    ax=axes[1];delay=feasible.backup_delay_h>0;tight=feasible.excess_above_bound.abs()<=1e-7
    for mask,label,c,marker in [(tight&~delay,'Immediate backup',BLUE,'o'),(delay,'24/48 h response',ORANGE,'s'),(~tight,'Ramp-constrained excess',GREEN,'^')]:
        part=feasible[mask];ax.scatter(part.normalized_lower_bound,part.normalized_optimized_backup,s=12,facecolor=c,edgecolor='white',linewidth=.3,label=label,marker=marker,zorder=3)
    ax.plot([.2,1.05],[.2,1.05],color=GREY,ls='--',lw=.65)
    ax.set(xlabel='Necessary response-adjusted U/f',ylabel='Optimized U/f',xlim=(.2,1.05),ylim=(.2,1.05),xticks=[.2,.4,.6,.8,1.],yticks=[.2,.4,.6,.8,1.]);panel(ax,'b','Process-model comparison')
    fig.legend(*ax.get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.55,.985),ncol=3,handlelength=1.,columnspacing=1.8)
    save(fig,'fig7_normalized_reserve_screen')


def main():
    configure()
    for builder in [architecture,fair_frontier,recovery_window,process_limits,causal_service,source_transfer,reserve_screen]:builder()
    report=dict(style_source='https://github.com/garrettj403/SciencePlots',commit='b9b16959570bd2fbc9ff5118bacc423c3bddd592',license='MIT; copyright and full license retained in scripts/styles/LICENSE.txt',
        official_guide='https://www.nature.com/nature/for-authors/final-submission',
        font='Arial, ordinary7pt and multi-panel labels8pt; figure width160mm matches current article text block',
        rationale='Nature-inspired layout; not Nature submission certification or endorsement. Figures derive only from unchanged verified numerical results.',
        artifacts=records,visual_review='Required after geometric checks; geometry does not certify all graphical relationships.')
    (QA/'geometry_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'figure_manifest.json').write_text(json.dumps(dict(
        figures=[r['name']+'.pdf' for r in records],
        editable_vectors=[r['name']+'.svg' for r in records],
        native_raster_dpi=1200, style_source=report['style_source'],
        style_commit=report['commit'], geometry_audit='results/nature_figures_qa/geometry_audit.json',
        source='Audited derived CSVs and explicitly modeled architecture, not measured plant operation.'
    ),indent=2),encoding='utf-8')
    print(json.dumps([dict(name=r['name'],text_overlaps=len(r['geometry']['text_text_intersections']),line_text=len(r['geometry']['data_line_text_intersections'])) for r in records],indent=2))


if __name__=='__main__':main()
