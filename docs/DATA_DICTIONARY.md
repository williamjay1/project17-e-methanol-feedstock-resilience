# Result fields and units

The time step is one hour. Traces are sequential hourly model states after actions; bulk deliveries occur at declared daily collection events. No trace is a measured plant operating record.

| Field | Meaning | Unit / convention |
|---|---|---|
| `q` | Final methanol production during the hour | t methanol/h |
| `P`, `exact_P` | Graph-approximated / native-equation-replayed PEM electric power | MW electric |
| `hp` (native traces) | Hydrogen production in LHV units | MWh H2/h, numerically MW LHV; divide by 1/30 MWh/kg for kg/h |
| `H` | Usable H2 inventory above the pressure cushion | MWh LHV; not total vessel mass |
| `C` | CO2 inventory | t CO2 |
| `M` | Methanol inventory after delivery | t final methanol |
| `primary`, `backup` | Plant-gate CO2 accepted during the hour | t CO2/h |
| `delivery_due_t`, `delivery_t` | Contract due / product actually delivered at this step | t final methanol per event; zero outside collection events |
| `shortfall` | Product delivery deficit | t final methanol per event |
| `M_precollection` | Product stock immediately before bulk pickup | t final methanol; capacity checked before withdrawal |
| `storage_pressure_bar` | Native pressure reconstructed from usable H2 state | bar |
| `exact_power_MW` | PEM+auxiliary+pressure-dependent compression electricity | MW electric |
| `exact_cooling_MW` | Native thermal removal duty | MW thermal; not chiller electricity |
| `realized_price_EUR_MWh` (Danish traces) | Revealed actual Danish engineering replay price | EUR/MWh; current/past prices only in policy inputs |
| `realized_operating_cost_EUR` (Danish traces) | Replayed model operating expense | EUR per hourly step; not an audited facility bill or LCOM |
| `backup_capacity_t_day` | Minimum/fixed firm backup rate | t CO2/day; NOT delivered methanol output |
| `delivery_t`, `produced_t`, `unserved_t` (summaries) | Total horizon product quantities | t final methanol |
| `status`, `success`, `feasible_incumbent` | SciPy/HiGHS solver classification | Infeasible entries have no invented trace |
| `mip_gap`, `dual_bound` | Recorded solver diagnostics | Not evidence of native nonlinear global cost optimality |
| `seconds` | Original local computation time | s; not portable performance guarantee |
| `stock_ratio`, `recovery_ratio` | Normalized opening inventory and recoverable CO2 surplus | Dimensionless; necessary-screen definitions in summary JSON |
| `normalized_lower_bound`, `normalized_optimized_backup` | Screen / retained optimized capacity divided by mean carbon use | Dimensionless; equality counts describe the selected grid only |

Affine pilot traces use `e` for MW electricity and `H` for MWh H2; their coefficient `h2_mwh_per_t` differs from the native route. Do not mix route coefficients or use a CO2 fulfillment ratio as methanol delivery. Parameter facts and explicit design assumptions are distinguished in the parameter JSON and source records.

Price columns from the German source workbook and initialization/forecast prices are intentionally omitted from public traces, as are corresponding hourly source/forecast costs. Aggregated derived operating-expense summaries remain. Download the publisher workbook to regenerate those columns and run the information-hash reconstruction; the offline public physical check explicitly does not verify omitted expenses.
