"""Preserve UTC quarters; aggregate exactly four 15-minute observations per hour."""
from pathlib import Path
import json
import pandas as pd
from runtime import ROOT, RAW, REPO_ROOT, load_parameters
RAW=REPO_ROOT/'public_inputs/energinet'
def main():
    frames=[]
    audit=[]
    for p in sorted(RAW.glob('DK1_DayAheadPrices_*_snapshot20261002.json')):
        obj=json.loads(p.read_text(encoding='utf-8'))
        f=pd.DataFrame(obj['records'])
        assert len(f)==obj['total'], (p,len(f),obj['total'])
        audit.append({'raw_file':str(p),'total':len(f)})
        frames.append(f)
    f=pd.concat(frames).sort_values('TimeUTC')
    assert f['PriceArea'].eq('DK1').all()
    assert not f['TimeUTC'].duplicated().any()
    f['time_utc']=pd.to_datetime(f['TimeUTC'],utc=True)
    assert (f['time_utc'].diff().dropna()==pd.Timedelta(minutes=15)).all()
    assert not f['DayAheadPriceEUR'].isna().any()
    hourly=f.set_index('time_utc')['DayAheadPriceEUR'].resample('h').agg(['mean','count'])
    assert hourly['count'].eq(4).all()
    hourly=hourly.rename(columns={'mean':'price_eur_per_mwh','count':'quarterhour_count'})
    out=ROOT/'results/DK1_hourly_replay_202510_202609.csv'
    hourly.to_csv(out)
    report=dict(raw=audit,quarters=len(f),hours=len(hourly),first=str(hourly.index[0]),
                last=str(hourly.index[-1]),minimum=float(hourly.price_eur_per_mwh.min()),
                maximum=float(hourly.price_eur_per_mwh.max()),
                license='CC BY 4.0; Energinet attribution; hourly aggregation is our transformation',
                note='UTC time; one hour is arithmetic mean of four equally long market intervals; '
                     'not a quarter-hour controller or plant electricity bill')
    (ROOT/'results/price_replay_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
