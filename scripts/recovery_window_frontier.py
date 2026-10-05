"""Separate outage duration from contracted post-outage recovery window."""
import json
from dataclasses import asdict
import numpy as np
import pandas as pd
from mucci_service_milp import Design,solve,ROOT
from run_service_boundaries import necessary_bounds

def main():
    d=Design();out=ROOT/'results/recovery_window_frontier';out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for days in [14,21]:
        H=days*24
        for Rdays in [1,3,7,14,21,39,46]:
            T=H+Rdays*24
            s,df=solve(np.zeros(T),d,H,min_backup=True,feasibility=True,time_limit=30)
            bounds=necessary_bounds(d,T,H)
            credit=d.carbon_initial+1.5494*d.product_initial
            row=dict(outage_days=days,recovery_days=Rdays,
                     replenishment_threshold=1+credit/(1.5494*d.qmean*Rdays*24),
                     **bounds,**s);rows.append(row);print(json.dumps({k:v for k,v in row.items() if k in ['outage_days','recovery_days','success','backup_capacity_t_day','replenishment_threshold','continuous_ramp_survival','last_outage_delivery','carbon_terminal_recovery','product_terminal_recovery']}),flush=True)
            if df is not None:df.to_csv(out/f'outage{days}_recover{Rdays}_trace.csv',index=False)
    pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
    (out/'manifest.json').write_text(json.dumps(dict(design=asdict(d),results=rows,
                     scope='Deterministic recovery deadline design; zero objective prices because only exact service projection is optimized.'),indent=2),encoding='utf-8')

if __name__=='__main__':main()
