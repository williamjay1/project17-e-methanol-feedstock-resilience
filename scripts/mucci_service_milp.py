"""Independent fixed-design reduction of public Mucci2023 equations.

SOS2 interpolation enforces the published nonlinear PEM efficiency graph plus
0-or-minimum-load disjunction. Conservative maximum-pressure H2 compression
power is separated from native pressure-dependent compression. No GAMS code copied.
Contracts, carbon/product stores and supplier interruptions are declared extensions.
"""
from pathlib import Path
from dataclasses import dataclass,asdict,replace
import json,time,argparse
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.optimize import brentq
from scipy.sparse import coo_matrix

from runtime import ROOT, RAW, REPO_ROOT, load_parameters
PARAM=load_parameters()

@dataclass
class Design:
    modules:int=40
    pem_pressure:float=40.0
    hydrogen_volume:float=1000.0
    h2_nominal_kg_h:float=1700.0
    utilization:float=0.82
    carbon_capacity:float=360.0
    carbon_initial:float=288.0
    product_capacity:float=477.5879396984924
    product_initial:float=238.7939698492462
    replenish_factor:float=1.15
    ramp:float=0.05
    minimum:float=0.20
    segments:int=8
    usable_hydrogen_fraction:float=1.0
    @property
    def qmax(self):return self.h2_nominal_kg_h/191.24
    @property
    def qmean(self):return self.utilization*self.qmax

def pem_eff(x,pressure):return 0.8126-0.101*x-0.0003118*pressure+0.01397*x*x

def solve(prices,d,outage_h,*,backup=None,min_backup=False,fixed=None,allow_shortfall=False,time_limit=45,
          feasibility=False,graph_hours=None,initial=None,due=None,primary_caps=None,backup_caps=None,
          terminal=None,initial_load=None,credit_floor=None,product_floor=None):
    T=len(prices);K=d.segments+1
    assert d.pem_pressure==40.0, 'Current pressure/usable-H2 projection is audited for 40bar only.'
    assert 35<=d.modules<=40 and 800<=d.hydrogen_volume<=1500
    assert 1700<=d.h2_nominal_kg_h<=1800
    assert 0<=d.usable_hydrogen_fraction<=1
    names=['q','P','hp','H','C','M','primary','backup','shortfall']
    ix={n:np.arange(i*T,(i+1)*T) for i,n in enumerate(names)}
    G=0 if feasibility else (T if graph_hours is None else min(graph_hours,T))
    lam=np.arange(9*T,9*T+K*G).reshape(G,K)
    seg=np.arange(9*T+K*G,9*T+K*G+(K-1)*G).reshape(G,K-1)
    on=np.arange(9*T+K*G+(K-1)*G,9*T+K*G+(K-1)*G+T-G)
    ui=9*T+K*G+(K-1)*G+T-G;N=ui+1
    pw=np.linspace(0.525,2.5,K)*d.modules
    hp=pw*pem_eff(pw/d.modules,d.pem_pressure)
    hydrogen_cap=0.072864*d.hydrogen_volume*(140-75)*120/3600*d.usable_hydrogen_fraction
    h0=min(120/3600,hydrogen_cap) # native one kg; zero in a no-usable-buffer stress
    dem=np.zeros(T);dem[23::24]=d.qmean*24
    if due is not None:dem=np.array(due,float)
    init={'H':h0,'C':d.carbon_initial,'M':d.product_initial}
    if initial is not None:init.update(initial)
    end={'H':h0,'C':d.carbon_initial,'M':d.product_initial}
    if terminal is not None:end=terminal
    q0=d.qmean if initial_load is None else initial_load
    lo=np.zeros(N);hi=np.full(N,np.inf);integ=np.zeros(N)
    lo[ix['q']]=d.minimum*d.qmax;hi[ix['q']]=d.qmax
    if fixed is not None:
        fixed=np.asarray(fixed,float)
        assert len(fixed)==T and fixed.min()>=d.minimum*d.qmax-1e-6 and fixed.max()<=d.qmax+1e-6
        assert np.max(np.abs(np.diff(np.r_[q0,fixed])))<=d.ramp*d.qmax+1e-6
        lo[ix['q']]=fixed;hi[ix['q']]=fixed
    hi[ix['P']]=pw[-1];hi[ix['hp']]=1950*120/3600
    hi[ix['H']]=hydrogen_cap;hi[ix['C']]=d.carbon_capacity;hi[ix['M']]=d.product_capacity
    hi[ix['primary']]=d.replenish_factor*1.5494*d.qmean;hi[ix['primary'][:outage_h]]=0
    hi[ix['backup'][outage_h:]]=0
    if primary_caps is not None:hi[ix['primary']]=primary_caps
    if backup_caps is not None:hi[ix['backup']]=backup_caps
    hi[ix['shortfall']]=dem if allow_shortfall else 0
    hi[lam.ravel()]=1;hi[seg.ravel()]=1;integ[seg.ravel()]=1
    hi[on]=1;integ[on]=1
    if backup is not None:hi[ui]=backup
    rows=[];lower=[];upper=[]
    def row(terms,a,b=None):rows.append(terms);lower.append(a);upper.append(a if b is None else b)
    for t in range(T):
        if t<G:
            row({ix['P'][t]:1,**{int(lam[t,k]):-pw[k] for k in range(K)}},0)
            row({ix['hp'][t]:1,**{int(lam[t,k]):-hp[k] for k in range(K)}},0)
            row({**{int(l):1 for l in lam[t]},**{int(y):-1 for y in seg[t]}},0)
            row({int(y):1 for y in seg[t]},0,1)
            for k in range(K):
                terms={int(lam[t,k]):1}
                if k:terms[int(seg[t,k-1])]=-1
                if k<K-1:terms[int(seg[t,k])]=-1
                row(terms,-np.inf,0)
        else:
            # Exact projection of the monotone native PEM graph for service
            # feasibility; exact electric power is reconstructed afterwards.
            z=int(on[t-G])
            row({ix['hp'][t]:1,z:-hp[0]},0,np.inf)
            row({ix['hp'][t]:1,z:-hp[-1]},-np.inf,0)
            # Tail P is only a declared linear cost forecast, never a reported
            # physical PEM power. Full feasibility mode gives it zero weight.
            row({ix['P'][t]:1,ix['hp'][t]:-pw[-1]/hp[-1]},0)
        for store,terms,rhs,initial in [
            ('H',{ix['H'][t]:1,ix['hp'][t]:-1,ix['q'][t]:6.374666666666667},0,init['H']),
            ('C',{ix['C'][t]:1,ix['primary'][t]:-1,ix['backup'][t]:-1,ix['q'][t]:1.5494},0,init['C']),
            ('M',{ix['M'][t]:1,ix['q'][t]:-1,ix['shortfall'][t]:-1},-dem[t],init['M'])]:
            if t:terms[ix[store][t-1]]=-1
            else:rhs+=initial
            row(terms,rhs)
        terms={ix['q'][t]:1}
        if t:terms[ix['q'][t-1]]=-1;previous=0
        else:previous=q0
        row(terms,previous-d.ramp*d.qmax,previous+d.ramp*d.qmax)
        row({ix['backup'][t]:1,ui:-1},-np.inf,0)
        # Production is accumulated BEFORE the instantaneous day-end collection.
        # Bounding only post-collection M would allow a hidden tank overflow.
        if dem[t]>0:
            row({ix['M'][t]:1,ix['shortfall'][t]:-1},-np.inf,d.product_capacity-dem[t])
        if credit_floor is not None and credit_floor[t]>0:
            row({ix['C'][t]:1,ix['M'][t]:1.5494},float(credit_floor[t]),np.inf)
        if product_floor is not None and product_floor[t]>0:
            row({ix['M'][t]:1},float(product_floor[t]),np.inf)
    for store,value in end.items():
        row({ix[store][-1]:1},value,np.inf)
    rr=[];cc=[];vv=[]
    for i,terms in enumerate(rows):
        for j,v in terms.items():rr.append(i);cc.append(j);vv.append(v)
    A=coo_matrix((vv,(rr,cc)),shape=(len(rows),N)).tocsc()
    comp=(14.63*298/(0.8*0.9))*(3.5**0.289267946-1)/120000
    obj=np.zeros(N)
    if min_backup:obj[ui]=1
    else:
        obj[ix['P']]=1.05*prices+1
        obj[ix['hp']]=comp*prices+comp-142/120
        obj[ix['q']]=0.1847*prices+1.3844
        obj[ix['primary']]=50;obj[ix['backup']]=50
        obj[ix['shortfall']]=1e6
    start=time.perf_counter()
    res=milp(obj,integrality=integ,bounds=Bounds(lo,hi),
             constraints=LinearConstraint(A,lower,upper),
             options={'time_limit':time_limit,'mip_rel_gap':1e-6})
    summary=dict(success=bool(res.success),status=int(res.status),message=res.message,
                 seconds=time.perf_counter()-start,mip_gap=getattr(res,'mip_gap',None),
                 dual_bound=getattr(res,'mip_dual_bound',None),feasible_incumbent=res.x is not None)
    if res.x is None:return summary,None
    x=res.x;df=pd.DataFrame({name:x[ind] for name,ind in ix.items()})
    df['price_eur_mwh']=prices;df['delivery_due_t']=dem;df['delivery_t']=dem-df.shortfall
    df['M_precollection']=df.M+df.delivery_t
    df['true_eta']=pem_eff(df.P/d.modules,d.pem_pressure)
    df['hydrogen_graph_error_mw']=df.hp-df.P*df.true_eta
    # The native H2-production function is strictly increasing on its ON range.
    # Reconstruct exact feasible PEM power for every optimized H2 flow; no venting.
    true_p=[]
    for h in df.hp:
        if h<1e-8:true_p.append(0.0)
        else:
            assert hp[0]-1e-6<=h<=hp[-1]+1e-6
            bounded=float(np.clip(h,hp[0],hp[-1]))
            true_p.append(brentq(lambda power:power*pem_eff(power/d.modules,d.pem_pressure)-bounded,pw[0],pw[-1]))
    df['exact_P']=true_p
    df['storage_pressure_bar']=75+df.H/(0.072864*d.hydrogen_volume*120/3600)
    df['exact_compressor_MW']=df.hp*(14.63*298/(0.8*0.9))*((df.storage_pressure_bar/d.pem_pressure)**0.289267946-1)/120000
    df['exact_power_MW']=1.05*df.exact_P+df.exact_compressor_MW+0.1847*df.q
    df['exact_cooling_MW']=df.exact_P-df.hp*142/120+df.exact_compressor_MW+1.3844*df.q
    df['exact_operating_cost_EUR']=df.exact_power_MW*prices+df.exact_cooling_MW+50*(df.primary+df.backup)
    vals=A@x
    violation=max(0,np.max(np.array(lower)-vals),np.max(vals-np.array(upper)),np.max(lo-x),np.max(x-hi))
    summary.update(backup_capacity_t_day=float(x[ui]*24),delivery_t=float(df.delivery_t.sum()),
                 precollection_capacity_enforced=True,maximum_precollection_M_t=float(df.M_precollection.max()),
                 unserved_t=float(df.shortfall.sum()),produced_t=float(df.q.sum()),
                 maximum_constraint_violation=float(violation),
                 maximum_h2_graph_error_mw=float(np.abs(df.hydrogen_graph_error_mw).max()),
                 minimum_C=float(df.C.min()),minimum_H=float(df.H.min()),
                 exact_native_h2_equation_max_abs=float(np.abs(df.hp-df.exact_P*pem_eff(df.exact_P/d.modules,d.pem_pressure)).max()),
                 exact_power_correction_max_MW=float(np.abs(df.exact_P-df.P).max()),
                 exact_replayed_operating_cost_EUR=float(df.exact_operating_cost_EUR.sum()),
                 exact_replayed_electricity_MWh=float(df.exact_power_MW.sum()),
                 exact_feasibility_projection=bool(feasibility),graph_hours=G,
                 terminal={s:float(df[s].iloc[-1]) for s in ['C','H','M']},objective=float(res.fun))
    return summary,df

def prices_from_public_workbook(T):
    p=Path(PARAM['sources']['inputs']['raw_path'])
    w=load_workbook(p,read_only=True,data_only=True)
    vals=np.array([r[1] for r in w['Day-ahead'].iter_rows(min_row=2,max_row=T+1,values_only=True)],float)
    w.close();return vals

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--hours',type=int,default=72)
    parser.add_argument('--outage-hours',type=int,default=24);parser.add_argument('--segments',type=int,default=8)
    parser.add_argument('--time-limit',type=float,default=45);args=parser.parse_args()
    assert args.hours%24==0
    d=Design(segments=args.segments);prices=prices_from_public_workbook(args.hours)
    out=ROOT/f'results/mucci_service_{args.hours}h_{args.segments}seg';out.mkdir(parents=True,exist_ok=True)
    rows=[]
    fixed=None
    for label,h,minb,b in [('noshock',0,False,0),('adjustable_min_backup',args.outage_hours,True,None),
                         ('fixed_min_backup',args.outage_hours,True,None)]:
        summary,trace=solve(prices,d,h,min_backup=minb,backup=b,
                            fixed=fixed if label=='fixed_min_backup' else None,time_limit=args.time_limit)
        rows.append(dict(case=label,**summary));print(json.dumps(rows[-1]),flush=True)
        if label=='noshock' and trace is not None:fixed=trace.q.to_numpy()
        if trace is not None:trace.to_csv(out/f'{label}_trace.csv',index=False)
    x=np.linspace(0.525,2.5,10001)
    f=d.modules*x*pem_eff(x,d.pem_pressure)
    points=np.linspace(0.525,2.5,d.segments+1)
    approximation=np.interp(x,points,d.modules*points*pem_eff(points,d.pem_pressure))
    manifest=dict(design=asdict(d),nominal_methanol_t_h=d.qmax,hours=args.hours,outage_h=args.outage_hours,
           source_parameter_file=str(ROOT/'literature/parameters_mucci_2023.json'),
           pointwise_max_abs_graph_error_MW=float(np.abs(f-approximation).max()),
           pointwise_max_relative_graph_error=float((np.abs(f-approximation)/f).max()),
           status='Independent fixed-design graph reduction; not author MINLP optimum reproduction',
           scope='Full-foresight diagnostic; no implemented causal policy. Native synthesis and H2 balance; '
                 'joint contracts/carbon/product stocks are extensions. Fixed 140bar compressor power '
                 'bounds native power conservatively, so cost is not exact native dynamic-pressure cost. '
                 'No heat or cooling duty interpreted as chiller electricity; no startups modeled.',results=rows)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
    print(json.dumps({k:v for k,v in manifest.items() if 'graph_error' in k}),flush=True)

if __name__=='__main__':main()
