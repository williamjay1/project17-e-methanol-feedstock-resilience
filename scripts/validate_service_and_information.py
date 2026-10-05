"""Independent equation replay and a price-independent shifted-tail witness.

Witness tests a standard feasibility-preservation construction, not cost optimality
or new control theory. No measured interruption probabilities are assigned.
"""
from pathlib import Path
import json,hashlib,inspect
from dataclasses import asdict,replace
import numpy as np
import pandas as pd
from mucci_service_milp import Design,solve,ROOT
from causal_dispatch import causal_inputs,price_forecast,shift_witness

K=1.5494;KH=191.24/30

def replay(df,d,initial=None,qprev=None):
    """Independent algebra; no optimizer constraints or residuals reused."""
    hcap=.072864*d.hydrogen_volume*65/30*d.usable_hydrogen_fraction
    ini={'C':d.carbon_initial,'H':min(1/30,hcap),'M':d.product_initial}
    if initial is not None:ini.update(initial)
    due=df.delivery_due_t.to_numpy();served=due-df.shortfall.to_numpy()
    def err(v):return float(np.max(np.abs(v)))
    errors={}
    errors['hydrogen_balance_MWh']=err(np.diff(np.r_[ini['H'],df.H])-df.hp+KH*df.q)
    errors['carbon_balance_t']=err(np.diff(np.r_[ini['C'],df.C])-df.primary-df.backup+K*df.q)
    errors['product_balance_t']=err(np.diff(np.r_[ini['M'],df.M])-df.q+served)
    errors['delivery_t']=err(df.delivery_t-served)
    errors['ramp_t_h']=max(0,float(np.max(np.abs(np.diff(np.r_[d.qmean if qprev is None else qprev,df.q]))))-d.ramp*d.qmax)
    errors['inventory_bounds']=max(0,float(-min(df.C.min(),df.H.min(),df.M.min())),float(df.C.max()-d.carbon_capacity),
                                  float(df.H.max()-hcap),float(df.M.max()-d.product_capacity))
    errors['precollection_product_capacity_t']=max(0,float(np.max(df.M+served)-d.product_capacity))
    errors['production_bounds']=max(0,float(d.minimum*d.qmax-df.q.min()),float(df.q.max()-d.qmax))
    g=df.hp.to_numpy();left=np.full(len(g),21.);right=np.full(len(g),100.)
    for _ in range(60):
        mid=(left+right)/2;f=mid*(.800128-.002525*mid+.00000873125*mid**2)
        left=np.where(f<g,mid,left);right=np.where(f>=g,mid,right)
    p=np.where(g<1e-8,0,(left+right)/2)
    pressure=75+df.H.to_numpy()/(.072864*d.hydrogen_volume/30)
    pc=g*(14.63*298/(.8*.9))*((pressure/40)**.289267946-1)/120000
    power=1.05*p+pc+.1847*df.q.to_numpy()
    cool=p-g*142/120+pc+1.3844*df.q.to_numpy()
    errors['native_hydrogen_graph_MW']=err(g-p*(.800128-.002525*p+.00000873125*p**2))
    errors['exact_power_replay_MW']=err(power-df.exact_power_MW)
    errors['exact_cooling_replay_MW']=err(cool-df.exact_cooling_MW)
    on=g>1e-8
    errors['native_hydrogen_domain_MW']=max(0,float(np.max(15.77002310625-g[on],initial=0)),float(np.max(g[on]-63.49405,initial=0)))
    if 'realized_operating_cost_EUR' in df:
        cost=power*df.realized_price_EUR_MWh+cool+50*(df.primary+df.backup)
        errors['expense_replay_EUR']=err(cost-df.realized_operating_cost_EUR)
    assert max(errors.values())<2e-5,errors
    return dict(max_residuals=errors,delivered_t=float(served.sum()),shortfall_t=float(df.shortfall.sum()),
                final={s:float(df[s].iloc[-1]) for s in ini},grid_peak_MW=float(np.max(power)),
                maximum_compressor_MW=float(pc.max()))

def frontier_checks():
    """Recheck every native frontier witness, including the bulk-pickup event.

    Designs are reconstructed from recorded sweep settings, not solver matrices.
    Infeasible rows are retained as solver classifications, not fabricated traces.
    """
    d=Design();checks=[];classified=[]
    groups=['native_service_boundaries','fair_reference_frontiers','recovery_window_frontier',
            'process_service_frontier','contract_stock_frontier']
    for group in groups:
        directory=ROOT/'results'/group
        frame=pd.read_csv(directory/'summary.csv')
        for _,row in frame.iterrows():
            case=d
            if group=='native_service_boundaries':
                case=replace(d,replenish_factor=float(row.replenish_factor))
                name=row.label;L=int(row.outage_h);lead=0
            elif group=='fair_reference_frontiers':
                name=f'{row["case"]}_{int(row.outage_h)}h';L=int(row.outage_h);lead=0
            elif group=='recovery_window_frontier':
                name=f'outage{int(row.outage_days)}_recover{int(row.recovery_days)}'
                L=int(row.outage_days)*24;lead=0
            elif group=='process_service_frontier':
                case=replace(d,carbon_initial=float(row.carbon_initial),minimum=float(row.minimum),
                             ramp=float(row.ramp),usable_hydrogen_fraction=float(row.usable_hydrogen_fraction))
                name=row['case'];L=504;lead=int(row.backup_lead_h)
            else:
                case=replace(d,utilization=float(row.utilization),product_initial=float(row.product_fill)*d.product_capacity,
                             replenish_factor=float(row.replenish_factor))
                name=f'contract{row.utilization}_fill{row.product_fill:g}_r{row.replenish_factor}'
                L=504;lead=0
            path=directory/f'{name}_trace.csv'
            if not path.exists():
                assert int(row.status)==2,(group,name,row.status)
                classified.append(dict(group=group,case=name,status='infeasible',solver_status=int(row.status)))
                continue
            trace=pd.read_csv(path,float_precision='round_trip');audit=replay(trace,case)
            assert audit['shortfall_t']<1e-6
            for store,initial in [('C',case.carbon_initial),('H',min(1/30,.072864*case.hydrogen_volume*65/30*case.usable_hydrogen_fraction)),('M',case.product_initial)]:
                assert audit['final'][store]>=initial-1e-6,(group,name,store)
            primary_cap=np.full(len(trace),case.replenish_factor*K*case.qmean);primary_cap[:L]=0
            backup_cap=np.full(len(trace),float(row.backup_capacity_t_day)/24);backup_cap[:lead]=0;backup_cap[L:]=0
            assert max(float((trace.primary-primary_cap).max()),float((trace.backup-backup_cap).max()))<2e-5
            assert abs(audit['delivered_t']-float(row.delivery_t))<1e-6
            checks.append(dict(group=group,case=name,maximum_precollection_M_t=float((trace.M+trace.delivery_t).max()),**audit))
    trace=pd.read_csv(ROOT/'results/mucci_service_1440h_8seg/noshock_trace.csv',float_precision='round_trip')
    checks.append(dict(group='unshocked_native_process',case='noshock',**replay(trace,d)))
    return checks,classified

def affine_checks():
    directory=ROOT/'results/product_service_pilot'
    p=json.loads((directory/'pilot_manifest.json').read_text())['process']
    hcap=p['hydrogen_hours']*p['h2_mwh_per_t']*p['qmean'];checks=[]
    for path in sorted(directory.glob('*trace.csv')):
        f=pd.read_csv(path,float_precision='round_trip');served=f.delivery_due_t-f.shortfall
        errors={
            'H_balance':float(np.abs(np.diff(np.r_[hcap/2,f.H])-p['eta']*f.e+p['h2_mwh_per_t']*f.q).max()),
            'C_balance':float(np.abs(np.diff(np.r_[p['carbon_initial'],f.C])-f.primary-f.backup+p['co2_t_per_t']*f.q).max()),
            'M_balance':float(np.abs(np.diff(np.r_[p['product_initial'],f.M])-f.q+served).max()),
            'precollection_capacity':max(0,float((f.M+served-p['product_cap']).max())),
            'ramp':max(0,float(np.abs(np.diff(np.r_[p['qmean'],f.q])).max())-p['ramp']*p['qmax'])}
        assert max(errors.values())<2e-5,(path.name,errors)
        checks.append(dict(case=path.stem,max_residuals=errors,delivered_t=float(served.sum()),shortfall_t=float(f.shortfall.sum())))
    assert len(checks)==7
    return checks

def main():
    out=ROOT/'results/final_validation';out.mkdir(parents=True,exist_ok=True)
    d=Design();T=1440;L=504;b=242.12/24;pmax=d.replenish_factor*K*d.qmean
    assert pmax>=b
    summary,plan=solve(np.zeros(T),d,L,backup=b,feasibility=True,time_limit=30)
    assert plan is not None and summary['feasible_incumbent']
    # Initial feasible tail is obtained ex ante, for the maximum design event.
    plan.to_csv(out/'admission_witness_trace.csv',index=False)
    repairs=[]
    for repair_day in range(22):
        # Fault injection: EVERY daily cost optimizer is unavailable. Use the
        # stored tail only. This tests fallback, not a simulated real fault rate.
        cache=plan.copy();actions=[];state=None;qprev=d.qmean
        for t in range(0,T,24):
            cache=shift_witness(cache,t>=repair_day*24,pmax)
            action=cache.iloc[:24].copy()
            replay(action,d,initial=state,qprev=qprev)
            state={s:float(action[s].iloc[-1]) for s in ['C','H','M']};qprev=float(action.q.iloc[-1])
            actions.append(action);cache=cache.iloc[24:].copy()
        trace=pd.concat(actions,ignore_index=True);audit=replay(trace,d)
        assert audit['shortfall_t']<1e-7
        for s,v in {'C':d.carbon_initial,'H':1/30,'M':d.product_initial}.items():assert state[s]>=v-1e-6
        repairs.append(dict(repair_day=repair_day,**audit))
    # The controller-input API cannot receive unrevealed prices or true repair.
    # Reconstruct all 60 input hashes of the audited certificate/credit replays.
    signature=list(inspect.signature(causal_inputs).parameters)
    assert 'actual_prices' not in signature and 'realized_outage_h' not in signature
    forecast=price_forecast();checks=[]
    for mode in ['credit_mpc','certificate_mpc']:
        directory=ROOT/f'results/causal_DK1_60d_21out_{mode}_8seg_rolling'
        frame=pd.read_csv(directory/f'{mode}_trace.csv',float_precision='round_trip');logs=json.loads((directory/f'{mode}_progress.json').read_text())
        source_prices=pd.read_csv(ROOT/'results/DK1_hourly_replay_202510_202609.csv')
        timestamps=pd.to_datetime(source_prices.time_utc,utc=True)
        known=source_prices.loc[timestamps>=pd.Timestamp('2025-12-31T23:00:00Z')].iloc[:T].price_eur_per_mwh.to_numpy()
        audit=replay(frame,d);hashes=0
        state={'C':288.,'H':1/30,'M':d.product_initial};qprev=d.qmean;emergency=False
        for t,log in zip(range(0,T,24),logs):
            inputs=causal_inputs(d,T,t,state,qprev,known[t:t+24],known[:t],forecast,t<L,
                                 mode,L,b,forecast_mode='rolling',emergency=emergency)
            assert inputs['input_sha256']==log['causal_input_sha256'],(mode,t)
            hashes+=1
            # Any repair later than this observation and any unrevealed prices
            # yield the SAME API arguments, hence bit-identical input hashes.
            if log.get('hard_service_failed'):emergency=True
            action=frame.iloc[t:t+24];state={s:float(action[s].iloc[-1]) for s in state};qprev=float(action.q.iloc[-1])
        checks.append(dict(policy=mode,reconstructed_daily_hashes=hashes,**audit))
    other=[]
    for name,mode in [('causal_DK1_60d_21out_guard_8seg_rolling','guard'),
                      ('causal_DK1_60d_21out_mpc_8seg_rolling','mpc'),
                      ('causal_mucci_60d_21out_certificate_mpc_8seg_rolling','certificate_mpc')]:
        directory=ROOT/'results'/name;frame=pd.read_csv(directory/f'{mode}_trace.csv')
        other.append(dict(case=name,**replay(frame,d)))
    frontiers,classifications=frontier_checks();affine=affine_checks()
    result=dict(admission_solver=summary,shifted_tail_repairs=repairs,
                controller_input_signature=signature,causal_hash_and_equation_checks=checks,other_replays=other,
                native_frontier_checks=frontiers,retained_infeasible_classifications=classifications,
                affine_transfer_checks=affine,precollection_capacity_independently_checked=True,
                scientific_scope='Standard shifted feasible-tail construction: single day-zero interruption, '
                    'day-boundary repair in [0,21] days, adequate interchangeable qualified gate input, '
                    'no plant grid/energy budget. Not a novel MPC stability theorem or native cost optimum.',
                fault_injection='No cost-optimizer action is used for any of 22 witness replays. No empirical fault probability.')
    (out/'validation_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    pd.DataFrame([dict(repair_day=r['repair_day'],delivered_t=r['delivered_t'],shortfall_t=r['shortfall_t'],
                       C_final=r['final']['C'],M_final=r['final']['M'],max_residual=max(r['max_residuals'].values()))
                  for r in repairs]).to_csv(out/'witness_repair_frontier.csv',index=False)
    print(json.dumps(dict(witness_repair_count=len(repairs),hash_checks=sum(c['reconstructed_daily_hashes'] for c in checks),
                         native_frontier_witnesses=len(frontiers),affine_witnesses=len(affine),
                         retained_infeasible_cases=len(classifications),
                         maximum_replay_residual=max(max(c['max_residuals'].values()) for c in checks+other+frontiers+affine),
                         admission_seconds=summary['seconds'])),flush=True)

if __name__=='__main__':main()
