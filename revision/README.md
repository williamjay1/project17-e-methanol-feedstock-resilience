# Reproducibility files for the revised CO2 backup-sizing study

This supplement contains the additional schedule comparisons, deterministic sizing sensitivities, and day-by-day controller experiments reported in the revision. It includes the inputs and outputs needed for independent inspection of every result. Commands below are run from the extracted directory with Python 3.12.

## Read or verify the results offline

The sizing summary is in `results/sizing/sizing_experiments.csv`. A status of 0 means an optimal solution and a status of 2 means that HiGHS proved infeasibility. A blank capacity denotes infeasibility. `results/controller/mpc_experiments.csv` distinguishes actual executed shortfall from unexecuted time. The terminal criterion is assessed only for a completed 60-day episode. Each controller directory includes its hourly actions, daily solver diagnostics and outcome report. `trace_verification.csv` and `prefix_verification.csv` summarize independent balance and opportunity-to-use-information checks.

```sh
python -m pip install -r requirements.txt
python scripts/verify_revision.py --output results/controller
python scripts/revision_sizing.py --repository model_v1 --output rerun/sizing
```

The first program reconstructs inventories, checks flow/ramp/tank limits, collections, the actual supplier state and terminal restoration, and compares controller input hashes during common observation periods. Rows with an early stop cover only the executed prefix. No external workbook is required for these two commands.

## Re-run controller scheduling

The original program uses 60 days of 2021 German prices only to initialize the first unknown-price forecast, then uses the previous 1–7 revealed days. Supply the public Mucci workbook to recompute those hour-of-day means. Its original price and forecast vectors are omitted from this supplement. The following command retrieves the workbook from its publisher and verifies its SHA-256 before saving it. A local copy of the same workbook can instead be supplied to `--workbook`.

```sh
python model_v1/scripts/acquire_inputs.py mucci --raw-dir original_inputs --workdir rerun/download
python scripts/revision_mpc.py --repository model_v1 --workbook original_inputs/mucci_2023/elsevier_S2352152X2302011X_mmc2_20261002.xlsx --prices model_v1/published_results/DK1_hourly_replay_202510_202609.csv --output rerun/controller --jobs 3
python scripts/verify_revision.py --output rerun/controller
```

For a quick solver test, append `--smoke` to the second command. This runs the 1 January reference start with 21-day repair only. The verifier above expects all 16 experiments, so use it with the supplied complete results or a complete rerun. Target data use elapsed hours and daily boundaries aligned to Danish local midnight. The two 60-day slices each have a constant UTC offset.

## Design and interpretation

All reserve comparisons use identical hourly process equations, assets, collections and terminal stock requirements. The repeated 24-hour program adds equality constraints between each hour and the matching hour on the previous day. The daily setpoint program adds equalities within each day. Both optimize the same minimum backup as the unrestricted schedule with full knowledge of the design interruption. Opening CO2 and methanol stocks are 288 t and 238.794 t in the reference. Capacity sensitivity changes vessel size and opening stock together at 80% fill. Other one-factor tests retain reference inputs unless coded otherwise. Recovery-duration tests keep the daily contract unchanged and change total service. The tabulated aggregate bound is necessary and excludes individual process limits. The no-headroom suffix certificate is a separate direct calculation from the prescribed price schedule.

For the MPC experiments, the backup cap is fixed at 242.12 t/day, post-repair primary supply is capped at 1.15 times mean carbon demand, and the controller knows that supply interruption will last at most 21 days once observed. Each solve commits its first 24 hours. The normal policy optimizes a 72-hour horizon, uses eight process segments over the first day and both delivery and recovery bounds. A failed hard-service plan triggers the published remaining-episode emergency routine. Hard failure, executed delivery loss and an unexecuted tail are recorded separately.

Two 60-day episodes begin on 1 January and 1 May 2026. The 12 day-zero tests cross both dates with realized durations of 14 and 21 days and separate opening-stock designs (80% CO2/50% product, 70%/50%, 80%/45%). Four further tests shift the interruption to the beginning of day eight in the original 60-day window, with both durations and both calendar starts. The first seven days receive normal primary availability and no information about the upcoming interruption. When supply is first observed off, the remaining-duration bound is measured from that observed day. The terminal targets remain the stocks at the beginning of the 60-day episode, not the smaller or larger stocks reached at outage onset. The scenario driver simulates the selected repair date. Its daily input builder receives only observed supplier status and an upper bound on the remaining interruption. Solver thread count and seed are fixed, limits are 20 s per MPC solve, and primal/MIP feasibility tolerances are 1e-9. Wall-clock limits can lead to different time-limited cost incumbents on other platforms. No cost-optimality or probabilistic reliability estimate is implied.

## Results of the extra operation tests

All 12 episodes with interruption at their opening completed the 60 daily deliveries and restored the opening inventories. When interruption started after seven days of ordinary dispatch, the reference January and May schedules had depleted product stocks. On the January path, only 5.969 t CO2 remained and the next five hours required at least 8.094 t of stored CO2 despite full backup and the fastest admissible ramp down. Both January paths therefore stopped after 168 executed hours. They do not measure the shortfall over the unexecuted tail. Both May paths ran 1,440 hours and restored terminal stocks, with 385.844 t of actual modeled shortfall at 14-day repair and 387.871 t at 21-day repair. The January and May paths reveal a dependence on the state at the moment the interruption is first observed.

In the portable rerun, all 36 sizing statuses and capacities matched; a separate January 21-day reference MPC run completed all 60 collections. The included trace verifier compared common daily input hashes for eight repair-duration pairs, and all 112 comparable day pairs agreed.

## Attribution and input acquisition

- Model and baseline results, version 1.0.0: https://doi.org/10.5281/zenodo.23162313. The included `model_v1` subset contains the original solver and runtime, the published fixed production profile (q column), and the hourly Danish price series. See its MIT license and original attribution notices. The revised timing adapter uses the same equations and solver as v1.0.0.
- Energinet, Energi Data Service, Day-Ahead Prices, DK1, https://www.energidataservice.dk/tso-electricity/DayAheadPrices. Source Danish quarter-hour data are licensed CC BY 4.0. The v1.0.0 archive contains the source snapshots and aggregation program. The hourly means included here reproduce the v1.0.0 input.
- Mucci S, Mitsos A and Bongartz D. Cost-optimal Power-to-Methanol: Flexible operation or intermediate storage? Journal of Energy Storage (2023). https://doi.org/10.1016/j.est.2023.108614. Supplement workbook: https://ars.els-cdn.com/content/image/1-s2.0-S2352152X2302011X-mmc2.xlsx. Verified SHA-256 is 52673c982d3e686b3ffb24091045da491717f7346dc13ea3a75dab2d117d00c0.
- The generated physical trajectories and numerical summaries represent deterministic model experiments. The `MANIFEST.sha256` file covers the supplied files except the manifest itself.

