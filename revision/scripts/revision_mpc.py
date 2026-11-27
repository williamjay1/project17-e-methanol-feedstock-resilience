"""Re-run the published joint-bound MPC under shifted calendar starts, repair times and opening stocks.
Usage: python revision_mpc.py --repository <published repository> --workbook <Mucci workbook>
       --prices <year-long DK1 hourly UTC CSV> --output <output directory> [--jobs 3]
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(key,'1')
import argparse, sys, json, warnings, itertools, contextlib, hashlib
from dataclasses import replace
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd

def run(args):
    repo, book, src, base, start, days, stock, onset = args
    output=Path(base); output.mkdir(parents=True, exist_ok=True)
    work=output / (start + '_' + str(days) + 'd_' + stock + '_onset' + str(onset))
    work.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(Path(repo)/'scripts'))
    os.environ['PROJECT17_MUCCI_WORKBOOK']=str(book)
    os.environ['PROJECT17_WORKDIR']=str(output / '_model_work')
    import mucci_service_milp as model
    import controller_timing as controller
    # SciPy forwards HiGHS options. Keep concurrent jobs reproducible and CPU bounded.
    from scipy.optimize import milp as scipy_milp
    def one_thread(*a,**kw):
        kw['options']=dict(kw.get('options',{}),threads=1,random_seed=0,mip_feasibility_tolerance=1e-9,primal_feasibility_tolerance=1e-9)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='Unrecognized options detected')
            return scipy_milp(*a,**kw)
    model.milp=one_thread
    d=model.Design()
    if stock=='carbon70': d=replace(d,carbon_initial=.70*d.carbon_capacity)
    if stock=='product45': d=replace(d,product_initial=.45*d.product_capacity)
    window=pd.read_csv(src)
    window['utc']=pd.to_datetime(window.time_utc,utc=True)
    begin=pd.Timestamp(start,tz='Europe/Copenhagen').tz_convert('UTC')
    episode=window.loc[window.utc>=begin].iloc[:1440]
    assert len(episode)==1440 and episode.utc.diff().dropna().eq(pd.Timedelta('1h')).all()
    assert len(set(v.utcoffset() for v in episode.utc.dt.tz_convert('Europe/Copenhagen')))==1
    prices=episode.price_eur_per_mwh.to_numpy()
    fname=work/'daily_log.txt'
    with fname.open('w',encoding='utf-8') as log, contextlib.redirect_stdout(log):
        report,trace,logs=controller.dispatch(prices,d,mode='certificate_mpc',realized_outage_h=days*24,
             backup=242.12/24,max_outage_h=504,horizon=72,time_limit=20,save_dir=work,forecast_mode='rolling',realized_onset_h=onset*24)
    h0=1/30
    out=dict(start=start,duration_days=days,opening=stock,onset_day=onset,C0_t=d.carbon_initial,M0_t=d.product_initial,
        status=report['status'],executed_h=report['complete_hours'],days_met=int(((trace.delivery_due_t>0)&
        ((trace.delivery_due_t-trace.delivery_t).abs()<1e-5)).sum()),shortfall_t=report['measured_model_shortfall_t'],
        delivered_t=report['delivered_t'],C_margin_t=trace.C.iloc[-1]-d.carbon_initial,H_margin_MWh=trace.H.iloc[-1]-h0,
        M_margin_t=trace.M.iloc[-1]-d.product_initial,hard_service_failure_days=report['hard_service_failure_days'],
        max_balance_residual=max(float((trace.C.diff().fillna(trace.C.iloc[0]-d.carbon_initial)-trace.primary-trace.backup+1.5494*trace.q).abs().max()),
        float((trace.H.diff().fillna(trace.H.iloc[0]-h0)-trace.hp+6.374666666666667*trace.q).abs().max()),
        float((trace.M.diff().fillna(trace.M.iloc[0]-d.product_initial)-trace.q+trace.delivery_t).abs().max())),
        max_capacity_violation=max(0.,float((trace.M_precollection-d.product_capacity).max()),float((trace.C-d.carbon_capacity).max()),
        float((trace.backup-242.12/24).max())), max_daily_shortfall_t=float(trace.shortfall.max()),
        cost_eur=report['total_exact_operating_cost_EUR'])
    out['unexecuted_h']=1440-len(trace)
    out['terminal_assessed']=len(trace)==1440
    if len(trace)<1440:
        for key in ('C_margin_t','H_margin_MWh','M_margin_t'):out[key]=None
    (work/'revision_checks.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    return out

def main():
    p=argparse.ArgumentParser()
    for arg in ('repository','workbook','prices','output'):p.add_argument('--'+arg,required=True,type=Path)
    p.add_argument('--jobs',type=int,default=3)
    p.add_argument('--smoke',action='store_true',help='Run only the reference January 21-day replay.')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    expected='52673c982d3e686b3ffb24091045da491717f7346dc13ea3a75dab2d117d00c0'
    if hashlib.sha256(a.workbook.read_bytes()).hexdigest()!=expected:raise ValueError('Workbook digest differs from the published experiment.')
    scenarios=[(a.repository,a.workbook,a.prices,a.output,*s,0) for s in
               itertools.product(('2026-01-01','2026-05-01'),(14,21),('reference','carbon70','product45'))]
    scenarios.extend((a.repository,a.workbook,a.prices,a.output,start,days,"reference",7)
                     for start,days in itertools.product(("2026-01-01","2026-05-01"),(14,21)))
    if a.smoke:scenarios=[(a.repository,a.workbook,a.prices,a.output,'2026-01-01',21,'reference',0)]
    with ProcessPoolExecutor(a.jobs) as pool:
        fut=[pool.submit(run,s) for s in scenarios]
        from concurrent.futures import as_completed
        rows=[]
        for f in as_completed(fut):
            r=f.result();rows.append(r)
            pd.DataFrame(rows).sort_values(['start','duration_days','opening']).to_csv(a.output/'mpc_experiments.csv',index=False)
            print(r['start'],r['duration_days'],r['opening'],r['status'],r['shortfall_t'],flush=True)
if __name__=='__main__':main()



