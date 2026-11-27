# Scope of reuse permissions

| Material | Applicable permission | Attribution / restriction |
|---|---|---|
| Independently authored Python implementation and repository documentation | MIT, top-level `LICENSE` | Does not grant rights in others' software or source attachments |
| `published_results/` and newly generated study figures | Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/ | Cite this repository's actual version/commit and underlying source models; distinguish scenarios from observations |
| `public_inputs/energinet/` and transformed Danish hourly prices | Energinet, CC BY 4.0 | Source: Energinet (www.energidataservice.dk); transformations: UTC sorting/quarter-hour arithmetic averaging; no endorsement implied |
| Giehl source data and extracted numeric unit/balance facts | Giehl, Hentschel, Ciprian and Weibezahn, CC BY 4.0, DOI 10.5281/zenodo.15855884 | Model accounting reduction is ours, not a full source-model replication |
| SciencePlots style files | MIT, copyright 2018 John Garrett; full original notice `scripts/styles/LICENSE.txt` | Pin b9b16959570bd2fbc9ff5118bacc423c3bddd592 retained |
| Mucci article/model parameter facts | Article CC BY 4.0; DOI 10.1016/j.est.2023.108614 | Independent implementation of published equations; source workbook/GAMS attachments omitted because a distinct reuse grant was not verified |
| Original Nord_H2ub software | Original repository GPL-3.0 | Not included, not executed as this independent model, and not licensed by the top-level MIT grant |

The contributors license newly generated result datasets and figures under CC BY 4.0. This license covers their contribution only and does not supersede rights held in underlying third-party material. No original German price series or initialization/forecast-price vectors are included. Related hourly German/forecast expenses are also omitted; aggregated model expense summaries and physical/dispatch results remain clearly derived outputs. Download the publisher input directly for recomputation; numerical agreement and attribution do not create redistribution permission.
