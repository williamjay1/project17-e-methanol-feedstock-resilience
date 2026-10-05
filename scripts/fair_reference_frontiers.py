"""Foresight fixed-profile and annual-mean references with identical service."""
import json
from dataclasses import asdict
import numpy as np
import pandas as pd
from mucci_service_milp import Design,solve,ROOT,prices_from_public_workbook

def main():
    d=Design();T=1440;prices=prices_from_public_workbook(T)
    # Preserved feasible no-shock cost incumbent, not a global optimum.
    base=ROOT/'results/mucci_service_1440h_8seg/noshock_trace.csv'
    fixed=pd.read_csv(base).q.to_numpy()
    out=ROOT/'results/fair_reference_frontiers';out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for H in [336,504]:
        for label,q in [('fixed_price_profile',fixed),('flat_contract_mean',np.full(T,d.qmean)),('adjustable',None)]:
            s,df=solve(prices,d,H,min_backup=True,feasibility=True,fixed=q,time_limit=30)
            row=dict(case=label,outage_h=H,**s);rows.append(row);print(json.dumps(row),flush=True)
            if df is not None:df.to_csv(out/f'{label}_{H}h_trace.csv',index=False)
    pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
    (out/'manifest.json').write_text(json.dumps(dict(design=asdict(d),results=rows,
             schedule_provenance=str(base),fixed_schedule_status='45s feasible no-shock foresight incumbent, native nonlinear electricity reconstructed; not author optimum',
             scope='Equal horizon, opening assets, hard daily deliveries and terminal stocks. Reserve optimization is exact within the declared no-grid-limit service model. Costs not optimized.'),indent=2),encoding='utf-8')

if __name__=='__main__':main()
