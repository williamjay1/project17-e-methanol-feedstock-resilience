"""Controlled minimum-backup comparisons and one-factor sensitivities on the published process solver.
Usage: python revision_sizing.py --repository <v1.0.0 repository> --output <directory>.
Outputs use no price series because prices have zero objective weight in minimum-backup sizing.
"""
import argparse, os, sys, json, warnings
from pathlib import Path
from dataclasses import replace
import numpy as np
import pandas as pd
from scipy.optimize import milp as original_milp, LinearConstraint
from scipy.sparse import coo_matrix
def run(repo, out):
    sys.path.insert(0,str(repo/'scripts'))
    os.environ['PROJECT17_WORKDIR']=str(out/'_model_work')
    import mucci_service_milp as model
    d=model.Design(); rows=[]; out.mkdir(parents=True,exist_ok=True)
    scenarios=[]
    for L in (14,21):
        for mode in ('unrestricted','daily_setpoint','periodic_24h','flat_mean','fixed_price'):
            scenarios.append(('benchmark',mode,d,L,60-L,0))
    for L in (14,21):
        for mode in ('unrestricted','flat_mean','fixed_price'):
            scenarios.append(('no_headroom',mode,replace(d,replenish_factor=1.0),L,60-L,0))
    for label,changed,R,delay in [
      ('CO2_fill_20pct',replace(d,carbon_initial=.2*d.carbon_capacity),39,0),
      ('CO2_fill_100pct',replace(d,carbon_initial=d.carbon_capacity),39,0),
      ('product_fill_0pct',replace(d,product_initial=0),39,0),
      ('product_fill_60pct',replace(d,product_initial=.6*d.product_capacity),39,0),
      ('headroom_1.0',replace(d,replenish_factor=1.),39,0),
      ('headroom_1.05',replace(d,replenish_factor=1.05),39,0),
      ('headroom_1.4',replace(d,replenish_factor=1.4),39,0),
      ('recovery_7d',d,7,0),('recovery_14d',d,14,0),('recovery_46d',d,46,0),
      ('ramp_1pct',replace(d,ramp=.01),39,0),('ramp_10pct',replace(d,ramp=.1),39,0),
      ('delay_24h',d,39,24),('delay_48h',d,39,48),('delay_72h',d,39,72),
      ('tank_180t',replace(d,carbon_capacity=180,carbon_initial=144),39,0),
      ('tank_540t',replace(d,carbon_capacity=540,carbon_initial=432),39,0),
      ('empty_CO2_ramp_1pct',replace(d,carbon_initial=0,ramp=.01),39,0),
      ('empty_CO2_ramp_5pct',replace(d,carbon_initial=0,ramp=.05),39,0),
      ('low_stocks_ceiling',replace(d,carbon_initial=.70*d.carbon_capacity,product_initial=.45*d.product_capacity),39,0)]:
        scenarios.append(('sensitivity',label,changed,21,R,delay))
    for group,label,design,L,R,delay in scenarios:
        T=(L+R)*24; H=L*24
        def constrained_milp(obj,*a,**kw):
            kw['options']=dict(kw.get('options',{}),threads=1,random_seed=0)
            if label in ('daily_setpoint','periodic_24h'):
                idx=np.arange(1,T) if label=='daily_setpoint' else np.arange(24,T)
                if label=='daily_setpoint':idx=idx[idx%24!=0]
                prior=idx-(1 if label=='daily_setpoint' else 24)
                row=np.arange(len(idx))
                mat=coo_matrix((np.r_[np.ones(len(idx)),-np.ones(len(idx))],
                    (np.r_[row,row],np.r_[idx,prior])),shape=(len(idx),len(obj))).tocsc()
                kw['constraints']=[kw['constraints'],LinearConstraint(mat,0.,0.)]
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore',message='Unrecognized options detected')
                return original_milp(obj,*a,**kw)
        model.milp=constrained_milp
        primary=np.full(T,design.replenish_factor*1.5494*design.qmean);primary[:H]=0.
        allowed=np.zeros(T);allowed[delay:H]=1e5
        fixed=None
        if label=='flat_mean': fixed=np.full(T,design.qmean)
        if label=='fixed_price':
            fixed=pd.read_csv(repo/'published_results/mucci_service_1440h_8seg/noshock_trace.csv').q.to_numpy()
        report,trace=model.solve(np.zeros(T),design,H,min_backup=True,feasibility=True,
                    primary_caps=primary,backup_caps=allowed,fixed=fixed,time_limit=90)
        if report['status'] not in (0,2): raise RuntimeError(str(report))
        reservoir=(design.carbon_initial+1.5494*design.product_initial)
        mu=1.5494*design.qmean*24
        b=max(0,mu*L-reservoir,mu*L-(design.replenish_factor-1)*mu*R)/(L-delay/24)
        if trace is not None:
            assert abs(trace.delivery_t.sum()-T*design.qmean)<1e-5
            if label=='daily_setpoint':assert np.ptp(trace.q.values.reshape(-1,24),axis=1).max()<1e-6
            if label=='periodic_24h':assert np.ptp(trace.q.values.reshape(-1,24),axis=0).max()<1e-6
            if group=='benchmark':trace[['q','C','H','M','primary','backup','delivery_t']].to_csv(out/f'{label}_{L}d.csv',index=False)
        row=dict(group=group,case=label,L_days=L,R_days=R,total_deliveries_t=T*design.qmean,CO2_capacity_t=design.carbon_capacity,
          CO2_initial_t=design.carbon_initial,methanol_initial_t=design.product_initial,recovered_ratio=design.replenish_factor,
          ramp=design.ramp,delay_h=delay,tank_capacity_days=design.carbon_capacity/mu,solver_status=report['status'],
          solver_message=report['message'],backup_t_day=report.get('backup_capacity_t_day'),mean_CO2_t_day=mu,
          backup_over_mean=(report.get('backup_capacity_t_day') or 0)/mu if report['status']==0 else np.nan,
          necessary_bound_t_day=b,max_violation=report.get('maximum_constraint_violation'),mip_gap=report.get('mip_gap'))
        rows.append(row);pd.DataFrame(rows).to_csv(out/'sizing_experiments.csv',index=False)
        print(label,L,row['backup_t_day'],report['status'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--repository',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();run(a.repository,a.output)

