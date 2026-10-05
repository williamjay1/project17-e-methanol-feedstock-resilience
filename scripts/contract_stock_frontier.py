"""Structured contract/product-stock sensitivities, not probability draws."""
from dataclasses import replace,asdict
import json
import numpy as np
import pandas as pd
from mucci_service_milp import Design,solve,ROOT
from run_service_boundaries import necessary_bounds

def main():
    base=Design();out=ROOT/'results/contract_stock_frontier';out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for utilization in [.25,.35,.60,.82,.95]:
        for fill in [0,.5,1]:
            for r in [1.,1.15]:
                d=replace(base,utilization=utilization,product_initial=fill*base.product_capacity,replenish_factor=r)
                summary,trace=solve(np.zeros(1440),d,504,min_backup=True,feasibility=True,time_limit=30)
                row=dict(utilization=utilization,product_fill=fill,replenish_factor=r,**necessary_bounds(d,1440,504),**summary)
                rows.append(row)
                if trace is not None:trace.to_csv(out/f'contract{utilization}_fill{fill}_r{r}_trace.csv',index=False)
                print(json.dumps({k:row[k] for k in ['utilization','product_fill','replenish_factor','status','backup_capacity_t_day'] if k in row}),flush=True)
    pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
    (out/'manifest.json').write_text(json.dumps(dict(base_design=asdict(base),results=rows,
             scope='Preselected deterministic 5x3x2 contract and opening-product-stock grid. '
                   'No empirical distribution/likelihood; hard daily delivery and unchanged terminal restoration. '
                   'Sensitivity of service envelope, not new facility demand measurements.'),indent=2),encoding='utf-8')

if __name__=='__main__':main()
