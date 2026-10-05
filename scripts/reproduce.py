"""Verify retained witnesses or rerun the public model in a separate workspace."""
from pathlib import Path
import argparse, csv, hashlib, json, os, shutil, subprocess, sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parent

def check_manifest():
    obj=json.loads((REPO/'manifest.json').read_text())
    for row in obj['files']:
        p=REPO/row['path']
        assert p.is_file(),row['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],row['path']
    return len(obj['files'])

def seed(work):
    if work==REPO or work in [REPO/'published_results',REPO/'external_raw']:
        raise ValueError('Use a separate generated workspace.')
    (work/'results').mkdir(parents=True,exist_ok=True)
    (work/'results/figures').mkdir(parents=True,exist_ok=True)
    for p in (REPO/'published_results').rglob('*'):
        if p.is_file():
            q=work/'results'/p.relative_to(REPO/'published_results');q.parent.mkdir(parents=True,exist_ok=True)
            if not q.exists():shutil.copyfile(p,q)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['verify','smoke','validate','screen','figures','full'])
    p.add_argument('--workdir',type=Path,default=REPO/'work')
    p.add_argument('--raw-dir',type=Path,default=None)
    p.add_argument('--mucci-workbook',type=Path,default=None)
    a=p.parse_args();work=a.workdir.resolve();count=check_manifest();seed(work)
    os.environ['PROJECT17_WORKDIR']=str(work)
    if a.raw_dir:os.environ['PROJECT17_RAW_DIR']=str(a.raw_dir.resolve())
    if a.mucci_workbook:os.environ['PROJECT17_MUCCI_WORKBOOK']=str(a.mucci_workbook.resolve())
    from runtime import ROOT
    assert ROOT==work
    from verify_public_results import verify
    verify(work,REPO)
    commands={'validate':['validate_service_and_information.py'],
              'screen':['normalized_reserve_screen.py'], 'figures':['make_nature_figures.py'],
              'full':['mucci_service_milp.py --hours 1440 --outage-hours 336 --segments 8 --time-limit 45',
                      'run_service_boundaries.py','fair_reference_frontiers.py','process_failure_frontier.py',
                      'recovery_window_frontier.py','contract_stock_frontier.py','pilot_product_service.py',
                      *[f'causal_dispatch.py --days 60 --outage-days 21 --mode {mode} --segments 8 --price-source DK1 --forecast rolling'
                        for mode in ['mpc','credit_mpc','certificate_mpc','guard']],
                      'causal_dispatch.py --days 60 --outage-days 21 --mode certificate_mpc --segments 8 --price-source mucci --forecast rolling',
                      'validate_service_and_information.py','normalized_reserve_screen.py','make_nature_figures.py']}
    if a.action=='smoke':
        import numpy as np
        from mucci_service_milp import Design,solve
        from validate_service_and_information import replay
        design=Design()
        summary,trace=solve(np.zeros(72),design,24,min_backup=True,feasibility=True,time_limit=30)
        assert trace is not None and summary['feasible_incumbent'],summary
        audit=replay(trace,design)
        assert audit['shortfall_t']<1e-7
        for k,v in {'C':design.carbon_initial,'H':1/30,'M':design.product_initial}.items():
            assert audit['final'][k]>=v-1e-6
        report={'test':'72h/24h deterministic engineering solver smoke test; zero objective prices are synthetic test inputs, not observations',
                'solver':summary,'independent_replay':audit,'manifest_files_verified':count}
        (work/'smoke_test.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    for command in commands.get(a.action,[]):
        subprocess.run([sys.executable,str(HERE/command.split()[0]),*command.split()[1:]],check=True,env=os.environ.copy())
    print(json.dumps({'action':a.action,'manifest_files_verified':count,'workspace':str(work)}))

if __name__=='__main__':main()
