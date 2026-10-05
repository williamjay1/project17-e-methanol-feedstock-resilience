# Owner-operated GitHub -> Zenodo handoff

Repository: https://github.com/williamjay1/project17-e-methanol-feedstock-resilience

No release or tag has been created by this preparation workflow. There is no project DOI yet. Source DOIs in the repository describe other researchers' inputs, not this deposit.

1. Review the repository and confirm actual responsible human creators, their order, affiliations/ORCIDs if applicable, and the license mapping in `LICENSES.md`. Do not list an AI system as an author or infer author identity from a GitHub login.
2. Before archiving, add a valid `CITATION.cff` with the **real** creators and software metadata. The code license is MIT; describe the CC BY 4.0 result/input datasets separately. Do not include a future DOI, invented affiliation or example person. Validate using cffconvert. A `.zenodo.json` is optional; if both files exist, Zenodo uses `.zenodo.json` rather than CFF. Avoid conflicting metadata.
3. Log into Zenodo yourself, connect/authorize GitHub, go to the GitHub integration page, click **Sync now**, and enable this public repository.
4. After the toggle is enabled and creators/license metadata are checked, create the GitHub release (suggested first version `v1.0.0`) from the reviewed commit. A tag by itself is not the release-ingestion workflow.
5. Wait for ingestion, open the actual Zenodo record, and verify files, creators, title, version, licenses and source-related identifiers. For paper-specific reproducibility cite the **version-specific** DOI; a concept DOI represents the version family.
6. Preserve the release/commit used by the paper. Add the actual DOI/badge/citation metadata only after it exists. Report that DOI for the manuscript's data/code availability paragraph and dataset/software reference; do not replace the upstream Giehl DOI.

Official instructions verified 5 October 2026:

- https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content
- https://help.zenodo.org/docs/github/enable-repository/
- https://help.zenodo.org/docs/github/describe-software/citation-file/
- https://help.zenodo.org/docs/github/describe-software/
- https://help.zenodo.org/docs/github/archive-software/github-upload/

The journal's authorship/AI policy, funding/interests and author approval requirements remain separate from assigning a repository DOI. This workflow does not submit the paper or perform Zenodo account actions on the owner's behalf.
