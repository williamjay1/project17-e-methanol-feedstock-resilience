"""Portable NECESSARY reserve screen, checked against ALL retained native designs.

This is a reanalysis of executed public-process scenarios, not new plant data,
new optimization runs, statistical validation, or a new control algorithm.
No core model is imported. Bounds are reconstructed from inventory algebra.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from runtime import ROOT, RAW, REPO_ROOT, load_parameters
OUT = ROOT / 'results/normalized_reserve_screen'
FIG = ROOT / 'results/figures'
KAPPA_C = 1.5494
KAPPA_H_KG = 191.24
SOURCES = ['native_service_boundaries', 'recovery_window_frontier',
           'process_service_frontier', 'contract_stock_frontier']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = json.loads((ROOT / 'results/native_service_boundaries/manifest.json').read_text())['design']
    rows = []
    hashes = {}
    for batch in SOURCES:
        source = ROOT / f'results/{batch}/summary.csv'
        hashes[str(source.relative_to(ROOT))] = digest(source)
        frame = pd.read_csv(source)
        for index, original in frame.iterrows():
            d = dict(base)
            total_h, outage_h, delay_h = 1440, 504, 0
            if batch == 'native_service_boundaries':
                outage_h = int(original.outage_h)
                d['replenish_factor'] = float(original.replenish_factor)
            elif batch == 'recovery_window_frontier':
                outage_h = int(original.outage_days * 24)
                total_h = outage_h + int(original.recovery_days * 24)
            elif batch == 'process_service_frontier':
                for key in ['carbon_initial', 'minimum', 'ramp', 'usable_hydrogen_fraction']:
                    d[key] = float(original[key])
                delay_h = int(original.backup_lead_h)
            elif batch == 'contract_stock_frontier':
                d['utilization'] = float(original.utilization)
                d['product_initial'] = float(original.product_fill) * d['product_capacity']
                d['replenish_factor'] = float(original.replenish_factor)
            recovery_h = total_h - outage_h
            mean_product = d['utilization'] * d['h2_nominal_kg_h'] / KAPPA_H_KG
            feed = KAPPA_C * mean_product
            stock = d['carbon_initial'] + KAPPA_C * d['product_initial']
            s = stock / (feed * outage_h)
            rho = (d['replenish_factor'] - 1) * recovery_h / outage_h
            available_fraction = (outage_h - delay_h) / outage_h
            zero_delay_bound = max(0., 1 - s, 1 - rho)
            lower_bound = zero_delay_bound / available_fraction
            # Exact existing terminal-product throughput condition, independent
            # of combined-stock algebra; retain it rather than suppressing it.
            product_bound = max(0., KAPPA_C * (mean_product * total_h -
                d['h2_nominal_kg_h'] / KAPPA_H_KG * recovery_h) -
                d['carbon_initial']) / (outage_h - delay_h)
            feasible = bool(original.success)
            optimized = float(original.backup_capacity_t_day) / (24 * feed) if feasible else None
            if feasible:
                assert optimized + 1e-8 >= lower_bound
                assert optimized + 1e-8 >= product_bound / feed
            # Checks are phase-aware: delivery occurs before state collection.
            daily_due = 24 * mean_product
            stock_phase_margin = d['product_capacity'] - d['product_initial'] - daily_due
            prebackup_due = (delay_h // 24) * daily_due
            prefix_deficit = max(0., prebackup_due - stock / KAPPA_C)
            if not feasible:
                assert stock_phase_margin < -1e-7 or prefix_deficit > 1e-7
            key_fields = [outage_h, recovery_h, d['utilization'], d['replenish_factor'],
                d['carbon_initial'], d['product_initial'], d['ramp'], d['minimum'],
                d['usable_hydrogen_fraction'], delay_h]
            row = dict(batch=batch, source_row=int(index), scenario_key=json.dumps(key_fields),
                feasible=feasible, outage_h=outage_h, recovery_h=recovery_h,
                mean_carbon_t_h=feed, stock_ratio=s, recovery_ratio=rho,
                backup_available_fraction=available_fraction, backup_delay_h=delay_h,
                ramp_fraction_h=d['ramp'], carbon_initial_t=d['carbon_initial'],
                product_initial_t=d['product_initial'], utilization=d['utilization'],
                usable_hydrogen_fraction=d['usable_hydrogen_fraction'],
                stock_phase_margin_t=stock_phase_margin, prebackup_deficit_t=prefix_deficit,
                zero_delay_screen=zero_delay_bound, normalized_lower_bound=lower_bound,
                normalized_optimized_backup=optimized,
                excess_above_bound=optimized-lower_bound if feasible else None,
                normalized_product_recovery_bound=product_bound / feed,
                dominant_bound='delivery' if s < rho else 'restoration')
            rows.append(row)
    all_rows = pd.DataFrame(rows)
    all_rows.to_csv(OUT / 'all_scenarios.csv', index=False)
    unique = all_rows.drop_duplicates('scenario_key').copy()
    unique.to_csv(OUT / 'unique_scenarios.csv', index=False)
    feasible = unique[unique.feasible].copy()
    failures = unique[~unique.feasible].copy()
    gaps = feasible[feasible.excess_above_bound > 1e-7].copy()
    gaps.to_csv(OUT / 'process_gap_cases.csv', index=False)
    assert len(all_rows) == 75 and int(all_rows.feasible.sum()) == 63
    assert len(failures) == 12
    summary = dict(analysis='Deterministic necessary-bound reanalysis; no new solves or observations',
        inventory_stock='C0 + kappa_C * M0',
        formula='U/f >= max(0,1-s,1-rho)/a; s=S0/(fL), rho=(r-1)R/L, a=(L-delay)/L',
        caveat='Necessary only: individual process, product-recovery throughput, collection phase and early deadline feasibility still apply.',
        all_records=len(all_rows), feasible_records=int(all_rows.feasible.sum()),
        unique_designs=len(unique), unique_feasible=len(feasible),
        unique_infeasible=len(failures), unique_feasible_at_bound=int((feasible.excess_above_bound.abs() <= 1e-7).sum()),
        unique_feasible_above_bound=len(gaps), maximum_normalized_process_gap=float(gaps.excess_above_bound.max()),
        maximum_gap_t_day=float((gaps.excess_above_bound * gaps.mean_carbon_t_h * 24).max()),
        phase_infeasible=int((failures.stock_phase_margin_t < -1e-7).sum()),
        early_deadline_infeasible=int((failures.prebackup_deficit_t > 1e-7).sum()),
        source_sha256=hashes, scenario_key_fields=['outage_h','recovery_h','utilization','replenish_factor',
            'carbon_initial','product_initial','ramp','minimum','usable_hydrogen_fraction','delay_h'],
        interpretation='Equality counts describe this chosen grid, not frequency, probability, coverage of all engineering regimes or a universal theorem.')
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    plot(feasible)
    print(json.dumps({k:v for k,v in summary.items() if k != 'source_sha256'}, indent=2))


def plot(feasible):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42,
        'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.25), layout='constrained')
    ax = axes[0]
    s = np.linspace(0, .45, 240)
    rho = np.linspace(0, 1.05, 240)
    ss, rr = np.meshgrid(s, rho)
    surface = np.maximum.reduce([np.zeros_like(ss),1-ss,1-rr])
    image = ax.pcolormesh(ss, rr, surface, cmap='cividis', vmin=.55, vmax=1., rasterized=True)
    ax.plot(s, s, color='white', linewidth=1.8)
    default = feasible[(feasible.backup_delay_h == 0) & (feasible.batch.isin(SOURCES[:2]))]
    ax.scatter(default.stock_ratio, default.recovery_ratio, s=25, edgecolor='black',
        facecolor='white', linewidth=.65, zorder=4)
    ax.text(.025,.92,'Delivery-limited screen',color='black',fontsize=10)
    ax.text(.19,.045,'Restoration-limited screen',color='black',fontsize=10)
    ax.text(.285,.30,r'$\rho=s$',color='white',rotation=35)
    ax.set(xlim=(0,.45),ylim=(0,1.05),xlabel=r'Opening stock ratio $s=S_0/(fL)$',
        ylabel=r'Recovery surplus ratio $\rho=(r-1)R/L$', title='(a) Necessary screen, immediate backup')
    bar = fig.colorbar(image,ax=ax,shrink=.80,pad=.025)
    bar.set_label(r'Lower bound on $U/f$')
    ax = axes[1]
    flags = feasible.backup_delay_h > 0
    tight = feasible.excess_above_bound.abs() <= 1e-7
    gap = ~tight
    for mask,label,color,marker in [(tight & ~flags,'Immediate backup, bound attained','#147d92','o'),
            (flags,'24/48 h delay, adjusted bound attained','#cf8a20','s'),
            (gap,'Process-constrained excess','#b64344','^')]:
        part=feasible[mask]
        ax.scatter(part.normalized_lower_bound,part.normalized_optimized_backup,
            s=31,facecolor=color,edgecolor='white',linewidth=.35,label=label,marker=marker,zorder=3)
    ax.plot([.2,1.08],[.2,1.08],color='gray',linestyle='--',linewidth=1,label='Equality line')
    excess=feasible.loc[feasible.excess_above_bound.idxmax()]
    ax.annotate('Empty carbon store;\n1%/h nominal ramp',
        xy=(excess.normalized_lower_bound,excess.normalized_optimized_backup),
        xytext=(.68,.52),arrowprops=dict(arrowstyle='-',color='#b64344'),fontsize=9)
    ax.set(xlim=(.2,1.08),ylim=(.2,1.08),xlabel=r'Necessary screen $\max(0,1-s,1-\rho)/a$',
        ylabel=r'Optimized firm backup $U/f$',title='(b) Unique feasible process designs')
    ax.legend(fontsize=8,loc='upper left',frameon=False)
    fig.savefig(FIG / 'fig7_normalized_reserve_screen.pdf',bbox_inches='tight')
    fig.savefig(OUT / 'normalized_reserve_screen_preview.png',dpi=180,bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
