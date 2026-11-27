"""Independently replay the 60-day traces and compare daily controller inputs shared by repair scenarios."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
T=1440
qmax=1700/191.24; qbar=.82*qmax; alpha=1.5494; hcoef=191.24/30; Cmax=360.; Mmax=477.5879396984924
Hmax=.072864*1000*65/30; B=242.12/24; pmax=1.15*alpha*qbar
def metric(v):
    return float(np.max(np.abs(v)))
def verify(work):
    storage=[]; pairs={}
    for folder in sorted(work.iterdir()):
        result_file=folder/'revision_checks.json'
        if not result_file.is_file():continue
        r=json.loads(result_file.read_text(encoding='utf-8')); q=pd.read_csv(folder/'certificate_mpc_trace.csv')
        l=json.loads((folder/'certificate_mpc_progress.json').read_text(encoding='utf-8'))
        n=len(q); assert n%24==0 and n==r['executed_h'] and len(l)==n//24 and list(q.hour)==list(range(n))
        k=r['onset_day']*24; end=k+r['duration_days']*24
        interrupted=np.zeros(n,dtype=bool); interrupted[k:end]=True
        due=np.zeros(n);due[23::24]=24*qbar
        def diff(s,x0):return np.diff(np.r_[x0,s])
        balances={'CO2_t':metric(diff(q.C,r['C0_t'])-q.primary-q.backup+alpha*q.q),
          'MeOH_t':metric(diff(q.M,r['M0_t'])-q.q+q.delivery_t),
          'H2_MWh':metric(diff(q.H,1/30)-q.hp+hcoef*q.q)}
        violations=[float(np.max(np.maximum(-q.C, q.C-Cmax))),
           float(np.max(np.maximum(-q.H,q.H-Hmax))),
           float(np.max(np.maximum(-q.M, q.M+q.delivery_t-Mmax))),
           float(np.max(np.maximum(-q.primary,q.primary-np.where(interrupted,0.,pmax)))),
           float(np.max(np.maximum(-q.backup,q.backup-np.where(interrupted,B,0.)))),
           float(np.max(np.maximum(.2*qmax-q.q,q.q-qmax))),
           float(np.max(abs(diff(q.q,qbar))-.05*qmax)),
           metric(q.delivery_due_t-due),metric(q.delivery_t+q.shortfall-due)]
        margins=[q.C.iloc[-1]-r['C0_t'],q.M.iloc[-1]-r['M0_t'],q.H.iloc[-1]-1/30]
        s=dict(start=r['start'],duration_days=r['duration_days'],opening=r['opening'],onset_day=r['onset_day'],
          C_at_onset_t=float(q.C.iloc[k-1] if k else r['C0_t']),M_at_onset_t=float(q.M.iloc[k-1] if k else r['M0_t']),
          H_at_onset_MWh=float(q.H.iloc[k-1] if k else 1/30),shortfall_t=float(q.shortfall.sum()),
          missed_deadlines=int(((due>0)&(q.shortfall>1e-5)).sum()),delivered_t=float(q.delivery_t.sum()),
          physical_limit_violation=max(0.,*violations),minimum_terminal_margin=min(margins),**balances)
        s['executed_h']=n; s['unexecuted_h']=T-n
        s['terminal_assessed']=n==T
        s['minimum_terminal_margin']=min(margins) if n==T else np.nan
        suppr=[d['day'] for d in l if d.get('hard_service_failed')]
        if n<T: suppr.extend(i for i in r['hard_service_failure_days'] if i not in suppr)
        s['first_hard_failure_day']=min(suppr) if suppr else np.nan
        qprev=qbar if k==0 else q.q.iloc[k-1]
        tt=np.arange(1,505); min_load=np.maximum(.2*qmax,qprev-.05*qmax*tt)
        s['carbon_needed_to_ramp_down_t']=max(0.,float(np.max(np.cumsum(alpha*min_load-B))))
        s['capacity_from_outage_stocks_bound_t_day']=alpha*24*qbar-(s['C_at_onset_t']+alpha*s['M_at_onset_t'])/r['duration_days']
        s['minimum_cumulative_shortfall_from_outage_stocks_t']=max(0.,((24*alpha*qbar-242.12)*r['duration_days']-s['C_at_onset_t']-alpha*s['M_at_onset_t'])/alpha)
        assert max(violations)<5e-6 and (n<T or min(margins)>-5e-6) and max(balances.values())<5e-6
        assert np.array_equal(q.observed_outage.to_numpy(),interrupted)
        assert all(entry['observed_outage']==bool(interrupted[24*i]) for i,entry in enumerate(l))
        storage.append(s);pairs.setdefault((r['start'],r['opening'],r['onset_day']),{})[r['duration_days']]=l
    audits=[]
    for (start,stock,k),g in pairs.items():
        if set(g)!={14,21}:continue
        n=min(k+14,len(g[14]),len(g[21]))
        mismatches=[i for i in range(n) if g[14][i]['causal_input_sha256']!=g[21][i]['causal_input_sha256']]
        audits.append(dict(start=start,opening=stock,onset_day=k,common_decision_days=n,unequal_input_hash_days=mismatches))
    assert len(storage)==16 and len(audits)==8
    pd.DataFrame(storage).to_csv(work/'trace_verification.csv',index=False)
    pd.DataFrame(audits).to_csv(work/'prefix_verification.csv',index=False)
    print(pd.DataFrame(storage).to_string(index=False))
    print(pd.DataFrame(audits).to_string(index=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);verify(p.parse_args().output)


