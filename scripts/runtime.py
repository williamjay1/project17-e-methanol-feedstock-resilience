"""Portable read-only sources and isolated derived outputs."""
from pathlib import Path
import json, os

REPO_ROOT=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('PROJECT17_WORKDIR',str(REPO_ROOT/'work'))).resolve()
RAW=Path(os.environ.get('PROJECT17_RAW_DIR',str(REPO_ROOT/'external_raw'))).resolve()
if ROOT==REPO_ROOT or ROOT==RAW:
    raise ValueError('Working outputs must be isolated from repository and raw inputs.')

def load_parameters():
    params=json.loads((REPO_ROOT/'literature/parameters_mucci_2023.json').read_text(encoding='utf-8'))
    # Existing input may be identified explicitly; never write or move that input.
    params['sources']['inputs']['raw_path']=os.environ.get('PROJECT17_MUCCI_WORKBOOK',
        str(RAW/'mucci_2023'/'elsevier_S2352152X2302011X_mmc2_20261002.xlsx'))
    return params
