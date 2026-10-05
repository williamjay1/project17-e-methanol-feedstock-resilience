"""Process and delivery boundaries, retaining all feasible/infeasible stresses."""
import json
from dataclasses import replace,asdict
import numpy as np
import pandas as pd
from mucci_service_milp import ROOT,Design,solve,prices_from_public_workbook
from run_service_boundaries import necessary_bounds

def main():
    d=Design();T=1440;H=504;prices=prices_from_public_workbook(T)
    out=ROOT/'results/process_service_frontier';out.mkdir(parents=True,exist_ok=True)
    rows=[]
    specs=[]
    for C0 in [0,72,144,288,360]:
        for ramp in [.01,.05,.10]:
            specs.append((f'C0{C0}_ramp{ramp}',replace(d,carbon_initial=C0,ramp=ramp),0))
    for Hfrac in [0,.01,.1,1]:
        specs.append((f'H2_fraction{Hfrac}',replace(d,usable_hydrogen_fraction=Hfrac),0))
    for lead in [24,48,72,96]:specs.append((f'backup_lead{lead}',d,lead))
    for name,case,lead in specs:
        pc=np.full(T,case.replenish_factor*1.5494*case.qmean);pc[:H]=0
        bc=np.ones(T)*1e5;bc[:lead]=0;bc[H:]=0
        s,df=solve(prices,case,H,min_backup=True,feasibility=True,
                    primary_caps=pc,backup_caps=bc,time_limit=30)
        bounds=necessary_bounds(case,T,H)
        first_hour=max(0,1.5494*(case.qmean-case.ramp*case.qmax)-case.carbon_initial)*24
        row=dict(case=name,carbon_initial=case.carbon_initial,minimum=case.minimum,ramp=case.ramp,
                  usable_hydrogen_fraction=case.usable_hydrogen_fraction,backup_lead_h=lead,
                  analytical_first_hour_bound_t_day=first_hour,
                  prebackup_delivery_necessary_shortfall_t=max(0,case.qmean*(lead//24)*24-case.product_initial-case.carbon_initial/1.5494),
                  **bounds,**s)
        rows.append(row);print(json.dumps(row),flush=True)
        if df is not None:df.to_csv(out/f'{name}_trace.csv',index=False)
        pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
    (out/'manifest.json').write_text(json.dumps(dict(design=asdict(d),hours=T,outage_h=H,
            proxy='Opening stocks, backup latency and usable-H2 availability are stress variables, not measured plant states.',
            exceptions='H2_fraction0 removes usable stock while retaining native PEM disjunction/pressure model; not a published vessel design.',results=rows),indent=2),encoding='utf-8')

if __name__=='__main__':main()
