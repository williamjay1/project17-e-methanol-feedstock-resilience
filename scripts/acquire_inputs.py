"""Acquire original owner inputs without overwriting raw evidence or copying author code."""
from pathlib import Path
import argparse, hashlib, io, json, os, stat, zipfile
from datetime import datetime, timezone
import requests

WORKBOOK_URL='https://ars.els-cdn.com/content/image/1-s2.0-S2352152X2302011X-mmc2.xlsx'
WORKBOOK_SHA='52673c982d3e686b3ffb24091045da491717f7346dc13ea3a75dab2d117d00c0'

def download(url,path,expected=None,algorithm='sha256'):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        response=requests.get(url,timeout=180,headers={'User-Agent':'Public-process-model-reproduction/1.0'})
        response.raise_for_status()
        body=response.content
        if expected and hashlib.new(algorithm,body).hexdigest()!=expected:
            raise ValueError('Provider content differs from the retained input checksum; raw file not written.')
        with path.open('xb') as f:f.write(body)
        path.chmod(stat.S_IREAD)
    body=path.read_bytes()
    if expected:assert hashlib.new(algorithm,body).hexdigest()==expected,path.name
    return {'url':url,'file':path.name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'read_only_original':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('source',choices=['mucci','giehl'])
    p.add_argument('--raw-dir',type=Path,required=True);p.add_argument('--workdir',type=Path,required=True)
    a=p.parse_args();raw=a.raw_dir.resolve();work=a.workdir.resolve();assert raw!=work
    sources=[]
    if a.source=='mucci':
        sources.append(download(WORKBOOK_URL,raw/'mucci_2023'/'elsevier_S2352152X2302011X_mmc2_20261002.xlsx',WORKBOOK_SHA))
        # Validate OOXML, rejecting an HTML challenge even if a provider responds HTTP 200.
        with zipfile.ZipFile(raw/'mucci_2023'/'elsevier_S2352152X2302011X_mmc2_20261002.xlsx') as z:assert '[Content_Types].xml' in z.namelist()
    else:
        url='https://zenodo.org/api/records/15855884/files/'
        archives=[('paper_energy_2025_inputs.zip','61cc40ce647e4157912c19e21abc25bb'),
                  ('paper_energy_2025_output_raw.zip','460f202c0107e287a3f78c787aa6a6b0')]
        for filename,checksum in archives:sources.append(download(url+filename+'/content',raw/filename,checksum,'md5'))
        # Extract ONLY the known workbook member into derived cache, never raw data.
        member='paper_energy_2024_inputs/paper_energy_2024_input_base_10op.xlsx'
        target=work/'cache/giehl_inputs'/member;target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(raw/'paper_energy_2025_inputs.zip') as z:
            body=z.read(member)
            if target.exists():assert target.read_bytes()==body
            else:
                with target.open('xb') as f:f.write(body)
    work.mkdir(parents=True,exist_ok=True)
    report={'source':a.source,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'files':sources,
            'note':'Official owner download only. No private data, author software redistribution or original-model optimum replication.'}
    name='acquisition_'+a.source+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json'
    with (work/name).open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
