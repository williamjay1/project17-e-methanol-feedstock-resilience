"""Native Mucci service feasibility and exact reconstructed operating points.

Fixed assets and hard daily product deliveries; no private observations. All
outage lengths/capacities are declared deterministic design stresses.
"""
from dataclasses import asdict,replace
from pathlib import Path
import json
import numpy as np
import pandas as pd
from mucci_service_milp import Design,solve,pem_eff,prices_from_public_workbook,ROOT

def necessary_bounds(d,T,H):
    c=1.5494;qm=d.qmean;qn=d.qmax
    n=np.arange(1,H+1)
    low=np.maximum(d.minimum*qn,qm-d.ramp*qn*n)
    return {
        'continuous_ramp_survival':max(0,float(np.max((c*np.cumsum(low)-d.carbon_initial)/n)))*24,
        'last_outage_delivery':max(0,c*(qm*H-d.product_initial)-d.carbon_initial)/H*24,
        'carbon_terminal_recovery':max(0,c*qm*T-d.replenish_factor*c*qm*(T-H))/H*24,
        'product_terminal_recovery':max(0,c*(qm*T-qn*(T-H))-d.carbon_initial)/H*24,
    }

def main():
    out=ROOT/'results/native_service_boundaries';out.mkdir(parents=True,exist_ok=True)
    T=1440;prices=prices_from_public_workbook(T);d=Design()
    rows=[]
    for H in [336,504]:
        for factor in [1.0,1.05,1.15,1.4]:
            case=replace(d,replenish_factor=factor)
            s,df=solve(prices,case,H,min_backup=True,feasibility=True,time_limit=55)
            row=dict(label=f'adjustable_{H}h_r{factor}',outage_h=H,replenish_factor=factor,**s,
                     **necessary_bounds(case,T,H));rows.append(row)
            print(json.dumps(row),flush=True)
            if df is not None:df.to_csv(out/f'{row["label"]}_trace.csv',index=False)
            pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
    # Native constitutive monotonicity plus all source equipment limits.
    x=np.linspace(.525,2.5,10001)
    deriv=.8126-.0003118*d.pem_pressure-.202*x+.04191*x*x
    hmin=.525*d.modules*pem_eff(.525,d.pem_pressure)
    hmax=2.5*d.modules*pem_eff(2.5,d.pem_pressure)
    compmax=hmax*(14.63*298/(.8*.9))*(3.5**.289267946-1)/120000
    proof=dict(minimum_native_derivative=float(deriv.min()),pem_hydrogen_min_MW=hmin,
               pem_hydrogen_max_MW=hmax,compressor_max_MW=compmax,compressor_bound_MW=1.75,
               co2_max_t_h=1.5494*d.qmax,co2_bound_t_h=20,
               synthesis_power_max_MW=.1847*d.qmax,synthesis_power_bound_MW=2.5,
               synthesis_cooling_max_MW=1.3844*d.qmax,synthesis_cooling_bound_MW=20,
               no_H2_buffer_effective_minimum_fraction=hmin/(6.374666666666667*d.qmax),
               native_hydrogen_capacity_MWh=.072864*d.hydrogen_volume*65*120/3600,
               no_electric_import_constraint=True,
               price_cost_scope='Service-boundary objective does not optimize cost. Exact feasible operating-cost replay is diagnostic only.',
               omitted='Battery, startup/shutdown, heat export, commercial CO2 qualification; no claims on these.')
    assert proof['minimum_native_derivative']>0 and compmax<1.75
    (out/'manifest.json').write_text(json.dumps(dict(design=asdict(d),hours=T,source='Mucci 2023 native process equations; published Germany 2022 input',
                           projection_proof=proof,results=rows),indent=2),encoding='utf-8')
    print(json.dumps(proof),flush=True)

if __name__=='__main__':main()
