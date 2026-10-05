"""Diagnostic continuous-operation LP, not an operable controller or plant validation.

Primary source-model coefficients preserve the *encoded* Giehl input ratios.
Electrolyzer efficiency is aggregate-calibrated for this cheap pilot only.
Full price/outage foresight is explicitly an optimistic diagnostic bound.
"""
from pathlib import Path
from dataclasses import dataclass, asdict, replace
import json, time
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from runtime import ROOT, RAW, REPO_ROOT, load_parameters
OUT=ROOT/'results/product_service_pilot'

@dataclass
class Process:
    label: str='Giehl_encoded_reduction'
    co2_t_per_t: float=1.4
    h2_mwh_per_t: float=5.173496722238861*1.4
    eta: float=233048.0310414586/312625.4767246437
    aux_mwh_per_t: float=(12819.198302300432+158.98773334452767)/32176.086746081808
    qmax: float=24.3857896885029/(19.9/3.6)
    qmean: float=20.1928/(19.9/3.6)
    minimum: float=0.20
    ramp: float=0.50
    pem_max: float=52.0
    carbon_cap: float=360.0
    carbon_initial: float=288.0
    product_cap: float=2640/(19.9/3.6)
    product_initial: float=(2640/(19.9/3.6))*0.5
    hydrogen_hours: float=3.0
    replenish_factor: float=1.15

def matrices(rows,ncols):
    rr=[];cc=[];vv=[];rhs=[]
    for i,(terms,b) in enumerate(rows):
        for j,v in terms.items():rr.append(i);cc.append(j);vv.append(v)
        rhs.append(b)
    return coo_matrix((vv,(rr,cc)),shape=(len(rows),ncols)).tocsr(),np.array(rhs)

def solve(prices,p,outage_h,*,fixed=None,backup=None,min_backup=False,allow_shortfall=False):
    """q [t/h], e [MW], H [MWh], C/M [t], input/backup [t/h]."""
    T=len(prices); names=['q','e','H','C','M','primary','backup','shortfall']
    ix={name:np.arange(k*T,(k+1)*T) for k,name in enumerate(names)}
    N=8*T+1; ui=N-1
    hcap=p.hydrogen_hours*p.h2_mwh_per_t*p.qmean
    initial={'H':hcap/2,'C':p.carbon_initial,'M':p.product_initial}
    demand=np.zeros(T);demand[23::24]=24*p.qmean
    eq=[];ub=[];bounds=[]
    for name in names:
        for t in range(T):
            if name=='q':b=(p.minimum*p.qmax,p.qmax) if fixed is None else (float(fixed[t]),float(fixed[t]))
            elif name=='e':b=(0,p.pem_max)
            elif name=='H':b=(0,hcap)
            elif name=='C':b=(0,p.carbon_cap)
            elif name=='M':b=(0,p.product_cap)
            elif name=='primary':b=(0,0 if t<outage_h else p.replenish_factor*p.co2_t_per_t*p.qmean)
            elif name=='backup':b=(0,None if t<outage_h else 0)
            else:b=(0,float(demand[t]) if allow_shortfall else 0)
            bounds.append(b)
    bounds.append((0,None if backup is None else backup))
    for t in range(T):
        for store,terms,rhs in [
            ('H',{ix['H'][t]:1,ix['e'][t]:-p.eta,ix['q'][t]:p.h2_mwh_per_t},0),
            ('C',{ix['C'][t]:1,ix['primary'][t]:-1,ix['backup'][t]:-1,ix['q'][t]:p.co2_t_per_t},0),
            ('M',{ix['M'][t]:1,ix['q'][t]:-1,ix['shortfall'][t]:-1},-demand[t])]:
            if t:terms[ix[store][t-1]]=-1
            else:rhs+=initial[store]
            eq.append((terms,rhs))
        up={ix['q'][t]:1};down={ix['q'][t]:-1}
        if t:up[ix['q'][t-1]]=-1;down[ix['q'][t-1]]=1
        ub.extend([(up,p.ramp*p.qmax+(p.qmean if t==0 else 0)),
                   (down,p.ramp*p.qmax-(p.qmean if t==0 else 0)),
                   ({ix['backup'][t]:1,ui:-1},0)])
        if demand[t]>0:ub.append(({ix['M'][t]:1,ix['shortfall'][t]:-1},p.product_cap-demand[t]))
    for store in ['H','C','M']:ub.append(({ix[store][-1]:-1},-initial[store]))
    obj=np.zeros(N)
    if min_backup:obj[ui]=1
    else:
        obj[ix['e']]=prices
        obj[ix['q']]=prices*p.aux_mwh_per_t
        obj[ix['primary']]=26.81
        obj[ix['backup']]=26.81 # equal purchased-feed price; no market backup quote inferred
        obj[ix['shortfall']]=1e6
    Aeq,beq=matrices(eq,N);Aub,bub=matrices(ub,N)
    start=time.perf_counter()
    res=linprog(obj,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=beq,bounds=bounds,method='highs')
    summary=dict(success=bool(res.success),status=int(res.status),message=res.message,
                 seconds=time.perf_counter()-start)
    if not res.success:return summary,None
    x=res.x;df=pd.DataFrame({name:x[idx] for name,idx in ix.items()})
    df['delivery_due_t']=demand;df['delivery_t']=demand-df.shortfall
    df['M_precollection']=df.M+df.delivery_t
    df['price_eur_mwh']=prices
    summary.update(backup_capacity_t_day=float(x[ui]*24),delivery_t=float(df.delivery_t.sum()),
                   precollection_capacity_enforced=True,maximum_precollection_M_t=float(df.M_precollection.max()),
                   produced_t=float(df.q.sum()),unserved_t=float(df.shortfall.sum()),
                   electricity_mwh=float((df.e+df.q*p.aux_mwh_per_t).sum()),
                   total_backup_t=float(df.backup.sum()),
                   eq_max_abs=float(np.abs(Aeq@x-beq).max()),
                   inequality_max_violation=float(max(0,(Aub@x-bub).max())),
                   terminal={s:float(df[s].iloc[-1]) for s in initial},initial=initial,
                   objective=float(res.fun))
    return summary,df

def lower_bounds(p,H,T):
    floor_path=np.maximum(p.minimum*p.qmax,p.qmean-p.ramp*p.qmax*np.arange(1,H+1))
    ramp_survival=max(0,np.max((p.co2_t_per_t*np.cumsum(floor_path)-p.carbon_initial)/np.arange(1,H+1)))*24
    return dict(minimum_load=max(0,p.co2_t_per_t*p.minimum*p.qmax-p.carbon_initial/H)*24,
                ramp_aware_survival=ramp_survival,
                event_product_contract=max(0,(p.co2_t_per_t*(p.qmean*H-p.product_initial)
                                      -p.carbon_initial)/H)*24,
                restored_terminal_mass=max(0,p.co2_t_per_t*p.qmean*T
                    -p.replenish_factor*p.co2_t_per_t*p.qmean*(T-H))/H*24,
                recovery_process_capacity=max(0,(p.co2_t_per_t*(p.qmean*T-p.qmax*(T-H))
                                                -p.carbon_initial)/H)*24)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    hourly=pd.read_csv(ROOT/'results/DK1_hourly_replay_202510_202609.csv',parse_dates=['time_utc'])
    times=pd.to_datetime(hourly.time_utc,utc=True)
    prices=hourly.loc[(times>='2026-01-01')&(times<'2026-02-26'),'price_eur_per_mwh'].to_numpy()
    assert len(prices)==56*24
    p=Process();rows=[]
    base,trace=solve(prices,p,0,backup=0)
    assert base['success'],base
    trace.to_csv(OUT/'noshock_trace.csv',index=False)
    rows.append(dict(case='noshock',days=0,**base))
    fixed=trace.q.to_numpy()
    for days in [14,21]:
        H=24*days
        for name,q in [('fixed_noshock_schedule',fixed),('adjustable_production',None)]:
            result,_=solve(prices,p,H,fixed=q,min_backup=True)
            assert result['success'],result
            u=result['backup_capacity_t_day']/24
            opt,tr=solve(prices,p,H,fixed=q,backup=u+1e-7)
            assert opt['success'],opt
            tr.to_csv(OUT/f'{name}_{days}d_trace.csv',index=False)
            rows.append(dict(case=name,days=days,**opt,**{'bound_'+k:v for k,v in lower_bounds(p,H,len(prices)).items()}))
        # survival-only design is a deliberate counterexample, not dropped for failure.
        survival=lower_bounds(p,H,len(prices))['ramp_aware_survival']/24+1e-7
        result,tr=solve(prices,p,H,backup=survival,allow_shortfall=True)
        rows.append(dict(case='minimum_load_carbon_only',days=days,**result))
        if tr is not None:tr.to_csv(OUT/f'survival_only_{days}d_trace.csv',index=False)
    # Isolate the observable mathematical recovery-rate boundary; no probability sampling.
    for factor in [1.0,1.05,1.15,1.4]:
        pp=replace(p,replenish_factor=factor)
        result,tr=solve(prices,pp,21*24,min_backup=True)
        rows.append(dict(case=f'replenishment_factor_{factor}',days=21,**result,
                    **{'bound_'+k:v for k,v in lower_bounds(pp,21*24,len(prices)).items()}))
    pd.DataFrame(rows).to_csv(OUT/'pilot_summary.csv',index=False)
    meta=dict(process=asdict(p),hours=len(prices),scope='Optimistic full-foresight diagnostic LP; NOT final analysis, '
              'NOT causal controller, NOT replication of full Giehl MILP or Mucci MINLP; '
              'continuous low-load synthesis; fixed equal daily product contracts and restored inventories',
              sources={'Giehl':'https://zenodo.org/records/15855884',
              'code_commit':'b45920770693376581342065c77a8926ddd82f9f',
              'floor':'Mucci2023 section5.2 Table4 https://arxiv.org/html/2305.18338v1',
              'ramp':'Giehl prepared Object__to_from_node rows11-12;50% nominal/h',
              'eta':'Aggregate H2energy/electricity from unshocked public output; pilot reduction only',
              'H2buffer':'3 mean-consumption hours: design scenario; no leak in cheap pilot',
              'initial_stocks':'CO280%nameplate and MeOH50%model2640MWh cap: design, not observations',
              'replenishment':'15% above mean modeled demand: design scenario, not permit-to-hour inference'})
    (OUT/'pilot_manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(pd.DataFrame(rows)[['case','days','success','backup_capacity_t_day','delivery_t','unserved_t','eq_max_abs']].to_string(index=False))

if __name__=='__main__':main()
