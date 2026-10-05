"""Recheck physical witnesses and manuscript quantities without network access."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

def verify(work,repository):
    from validate_service_and_information import frontier_checks,affine_checks,replay
    from mucci_service_milp import Design
    native,infeasible=frontier_checks();affine=affine_checks();causal=[]
    for group in ['causal_DK1_60d_21out_certificate_mpc_8seg_rolling',
                  'causal_DK1_60d_21out_credit_mpc_8seg_rolling',
                  'causal_DK1_60d_21out_guard_8seg_rolling','causal_DK1_60d_21out_mpc_8seg_rolling',
                  'causal_mucci_60d_21out_certificate_mpc_8seg_rolling']:
        files=list((work/'results'/group).glob('*_trace.csv'));assert len(files)==1
        causal.append(dict(case=group,**replay(pd.read_csv(files[0],float_precision='round_trip'),Design())))
    assert len(native)==70 and len(affine)==7 and len(causal)==5 and len(infeasible)==12
    screen=json.loads((work/'results/normalized_reserve_screen/summary.json').read_text())
    for k,v in {'all_records':75,'unique_designs':69,'unique_feasible':57,'unique_infeasible':12,
                'unique_feasible_at_bound':55,'unique_feasible_above_bound':2,'phase_infeasible':10,
                'early_deadline_infeasible':2}.items():assert screen[k]==v,(k,screen[k])
    frame=pd.read_csv(work/'results/fair_reference_frontiers/summary.csv')
    reductions=[]
    for hours in [336,504]:
        subset=frame[frame.outage_h==hours]
        fixed=subset[subset['case']=='fixed'].iloc[0] if 'fixed' in set(subset['case']) else subset[subset['case'].str.contains('fixed')].iloc[0]
        adjustable=subset[subset['case'].str.contains('adjust')].iloc[0]
        assert abs(fixed.delivery_t-adjustable.delivery_t)<1e-6
        reductions.append({'outage_h':hours,'fixed_t_day':float(fixed.backup_capacity_t_day),
            'adjustable_t_day':float(adjustable.backup_capacity_t_day),
            'reduction_percent':float(100*(1-adjustable.backup_capacity_t_day/fixed.backup_capacity_t_day))})
    residual=max(max(row['max_residuals'].values()) for row in native+affine+causal)
    report={'native_witnesses':len(native),'affine_witnesses':len(affine),'causal_witnesses':len(causal),
        'retained_infeasible_cases':len(infeasible),'maximum_equation_residual':residual,
        'fair_service_comparison':reductions,'screen_counts_verified':True,
        'licence_boundary':'German source/forecast-price vectors and related hourly costs are omitted; price-free physical replays do not verify those omitted costs. Danish realized expense replay is retained.',
        'scope':'Model witnesses, not field observations; offline replay does not rerun all optimization or reconstruct 120 controller hashes.'}
    (work/'public_verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2));return report
