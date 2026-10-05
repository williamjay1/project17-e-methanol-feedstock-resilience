# E-methanol feedstock resilience: code and derived data

Portable reproducibility package for **CO2 Backup Requirements for Flexible E-Methanol Production under Supply Interruptions**. Repository version: **1.0.0**. This is engineering scenario analysis, not measured Kassø plant operation, not certification evidence, and not a reproduction of the original Mucci nonlinear optimum or complete Giehl model.

## What is reproducible

- Independently implemented process equations, carbon/hydrogen/product inventory balances, minimum-load/ramp restrictions, daily bulk delivery and restored terminal stocks.
- Fixed-profile, flat-mean and adjustable-production comparisons at the same delivery obligations/assets; all retained infeasible scenarios are included.
- Seventy native physical witnesses, seven affine accounting-transfer witnesses and five causal controller replays; necessary stock/recovery/response screen for 69 distinct designs.
- Seven vector figures from model outputs. Source styles are MIT-licensed SciencePlots, pinned to commit `b9b16959570bd2fbc9ff5118bacc423c3bddd592`; Nature does not endorse this repository.

The public-model comparisons report a 10.38% / 9.85% reduction in minimum firm CO2 backup capacity for 14-/21-day design stresses when production can adjust. Those are scenario outcomes, not observed procurement savings. The normalized screen is necessary, not generally sufficient. Product collection timing, ramp restrictions, early deadlines and inventory recovery remain binding in documented counterexamples.

## Quick start: no account, credentials or network needed

Python 3.12 is the executed interpreter. Install dependencies in your own environment:

```sh
python -m pip install -r requirements.txt
python scripts/reproduce.py verify --workdir /your/derived-work/project17
python scripts/reproduce.py smoke --workdir /your/derived-work/project17
python scripts/reproduce.py screen --workdir /your/derived-work/project17
```

On Windows replace the example work directory with an absolute writable derived-data directory. `published_results/` is the retained evidence snapshot; generated outputs go to a separate workspace, never into that snapshot or raw input directory. The smoke test **actually solves** a 72-hour/24-hour interruption case and independently checks physical balances, delivery and terminal stocks; zero prices in this test are synthetic diagnostic inputs, not a market observation.

`verify` replays existing witnesses; it does not claim to rerun all optimization. `screen` independently reconstructs the necessary-bound analysis. `figures` redraws all seven figures as native vector PDF/SVG and direct 1200-dpi PNG, but requires a suitable font installation (the executed artwork uses Arial; automatic font fallback can change label geometry).

## Full analysis and source-input checks

The Mucci publisher workbook is required for original German inputs and initialization of the controller's 2021 profile. It is publicly downloadable but **not redistributed here**, because a distinct supplemental-data redistribution grant was not established. No GAMS/BARON or copied author code is needed for this independently authored implementation.

```sh
python scripts/acquire_inputs.py mucci --raw-dir /your/read-only-inputs/project17 --workdir /your/derived-work/project17
python scripts/reproduce.py validate --workdir /your/derived-work/project17 --raw-dir /your/read-only-inputs/project17
python scripts/reproduce.py full --workdir /your/derived-work/project17 --raw-dir /your/read-only-inputs/project17
```

You can instead pass `--mucci-workbook /existing/input.xlsx` to read an already downloaded immutable copy. `validate` reruns admission, all 22 repair/fallback witnesses and the 120 daily information-hash reconstructions; it also replays the retained witnesses. `full` reruns the model sweeps and causal price replays, then validation and figures. It can take substantially longer than the offline checks. Mixed-integer incumbents, timings and equal-objective trajectories may differ with solver version; the existing fixed-price baseline is not a claimed unique global nonlinear optimum. Do not infer cost-optimality from capacity-feasibility runs.

The CC BY 4.0 Energinet quarter-hour snapshots are included under `public_inputs/energinet/`. Run `python scripts/prepare_price_replay.py` with `PROJECT17_WORKDIR` set to your generated workspace to rebuild the 8,760 hourly means from 35,040 quarter-hour observations. This is a deliberate hourly engineering aggregation, not settlement reproduction.

For the independent Giehl **accounting transfer**, input/output model units and source balance checks:

```sh
python scripts/acquire_inputs.py giehl --raw-dir /your/read-only-inputs/project17 --workdir /your/derived-work/project17
python scripts/audit_giehl_units.py
```

Before the last command set `PROJECT17_RAW_DIR` and `PROJECT17_WORKDIR` to the same directories used for acquisition. It reads the original Zenodo input/output workbooks. It does not rerun the source's complete optimization/transient model. The original GPL-3.0 repository is linked and pinned in `docs/DATA_SOURCES.md`, not bundled or relabeled as MIT.

## Scientific and publication boundaries

Interruption duration, opening stocks, firm backup and recovery headroom are declared design conditions, not reconstructed field events. No facility receipts, measured purity, operating inventories, certification eligibility or actual economic losses are inferred. Whole-day price publication is an explicit controller-information assumption, not historical publication telemetry. Causal policies do not receive future realized prices or a realized repair date. The guarantee is bounded to one day-zero interruption with day-aligned repairs and sufficient interchangeable qualified plant-gate feedstock; no grid-import budget, cold restart model or RFNBO proof is imposed.

Failed scenarios and service-deficient policies remain in the evidence. Lower expenses with unmet deliveries are not service-equivalent savings. Data/figures alone do not establish submission clearance, human authorship or compliance with a journal's AI policy. See `docs/RESEARCH_INTEGRITY.md`.

## Files and licensing

`scripts/`: independently authored scientific implementation and portable reproduction interface (MIT). `literature/`: parameter facts, unit locators and source/reuse boundaries. `published_results/`: retained derived scientific CSV/JSON evidence (CC BY 4.0). `public_inputs/energinet/`: credited original public snapshots (Energinet, CC BY 4.0). `provenance/`: checksums, actual executed package versions and packaging transformations. The top-level MIT license does not override third-party data/software terms; see `LICENSES.md`.

No private data, credentials, manuscript draft, internal reviewer notes or publisher attachments are included. `manifest.json` covers the public files (excluding itself and generated workspaces). Scientific source files remain protected outside this portable packaging copy.

## Citation and Zenodo

GitHub: https://github.com/williamjay1/project17-e-methanol-feedstock-resilience

Cite the exact commit/version you used. This repository has **no project DOI yet**. Source DOI `10.5281/zenodo.15855884` belongs to Giehl and colleagues, not this project. Responsible human creators will supply their verified identities, affiliation/ORCID where applicable, and create the Zenodo archive personally. No fabricated `CITATION.cff` authors or dummy DOI are embedded. Follow `docs/ZENODO_HANDOFF.md`: enable the repository in Zenodo **before creating the release**, then verify the generated archive and version-specific DOI.
