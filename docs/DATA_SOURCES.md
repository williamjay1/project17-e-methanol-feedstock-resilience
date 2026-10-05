# Public source access and provenance

| Source | Access and original link | License and resolution | Reproduction role |
|---|---|---|---|
| Mucci/Mitsos/Bongartz 2023 process | https://doi.org/10.1016/j.est.2023.108614 ; public text https://arxiv.org/html/2305.18338v1 | Article CC BY 4.0; arXiv version has its separate distribution terms | Mathematical process parameter facts and native replay equations; no cold-start parameter invented |
| Mucci price workbook | https://ars.els-cdn.com/content/image/1-s2.0-S2352152X2302011X-mmc2.xlsx | Public direct download, no registration; distinct supplement redistribution license unverified; hourly input | Original German price replay and 2021 training profile; downloaded from owner, not bundled |
| Mucci supplement | https://ars.els-cdn.com/content/image/1-s2.0-S2352152X2302011X-mmc1.pdf | Public; retained for source equations/locators, not bundled | Read-only mathematical verification; independent model not original GAMS execution |
| Giehl et al. Zenodo v1 | https://zenodo.org/records/15855884 ; API https://zenodo.org/api/records/15855884 | CC BY 4.0 verified in record API; input/output workbooks, hourly source output | Independent affine accounting transfer and exact source-unit/balance audit, not a full original optimization replication |
| Nord_H2ub source | https://github.com/CSEI-EU/Nord_H2ub/tree/b45920770693376581342065c77a8926ddd82f9f | GPL-3.0; original source code not included | Source inspection provenance only; not required to run the independent models |
| Energinet DayAheadPrices | https://api.energidataservice.dk/dataset/DayAheadPrices ; metadata https://api.energidataservice.dk/meta/dataset/DayAheadPrices | CC BY 4.0 https://www.energidataservice.dk/terms-and-conditions ; DK1, quarter-hour; API date arguments 2025-10-01 to 2026-10-01 exclusive | Four fixed snapshots aggregated as four equal intervals/hour, 8,760 hourly observations; not legacy Elspotprices nor settlement reconstruction |
| SciencePlots | https://github.com/garrettj403/SciencePlots/tree/b9b16959570bd2fbc9ff5118bacc423c3bddd592 | MIT; copyright and source pin retained | Plot style only; no affiliation/endorsement implied |

Source creators: Mucci, Simone; Mitsos, Alexander; Bongartz, Dominik. Zenodo data: Giehl, Johannes; Hentschel, Dana; Ciprian, Lucia; Weibezahn, Jens. Danish data: Energinet. Style: John Garrett/SciencePlots contributors. All transformations and acquisition hashes are described in the public provenance files.

Mucci workbook SHA256: `52673c982d3e686b3ffb24091045da491717f7346dc13ea3a75dab2d117d00c0`.

Original Zenodo inputs MD5: `61cc40ce647e4157912c19e21abc25bb`. Original raw outputs MD5: `460f202c0107e287a3f78c787aa6a6b0`. These immutable identifiers are not a new project DOI. The repository stores only our derived source-unit audit, not the original input/output archives.

Public acquisition is limited to official file/API requests; no personal data, login scraping or facility-specific nonpublic records are collected. The four source price snapshots contain only market area, interval and price fields as supplied by the official public API. Live provider revisions may not match fixed snapshot hashes: retain them separately rather than overwrite or silently substitute.

The API date bounds and returned UTC timestamps are not interchangeable: the retained first hourly UTC timestamp is **2025-09-30 22:00:00+00:00** and the last is **2026-09-30 21:00:00+00:00**. Quarter boundaries can contain unequal UTC interval counts across daylight-saving transitions. Aggregation sorts the returned `TimeUTC` timestamps, enforces uninterrupted 15-minute steps and exactly four records per hour, and does not shift timestamps to force nominal date labels.
