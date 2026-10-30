# Australian Health Forecast Lab

Research prototype for forecasting published aggregate Australian welfare caseload. The selected series is the national Carer Payment recipient total from the DSS monthly time series. It supports methods research using chronological evaluation and explicit uncertainty. It does not measure clinical demand or unmet caring need.

Recipient totals reflect program rules and recorded administrative status, including suspended and zero-rate recipients. Historical releases cannot establish a current operational forecast, and revised data cannot establish what was knowable at an earlier date.

## Intended use and limits

This repository is for reproducible, aggregate-level research. It is not intended for individual diagnosis, triage, treatment, welfare eligibility, or autonomous resource-allocation decisions. No patient records, identifiers, record linkage or private health data are accepted within this research scope.

Dataset licensing, units, coverage, publication delays, suppression and permitted reuse require source-specific review before analysis. Australian privacy, ethics, AI-governance and medical-device requirements depend on the actual data, intended use and adopting organisation. This project does not establish government endorsement, regulatory approval, or compliance for a deployment.

## Reference material

- [AIHW emergency-department activity over time](https://www.aihw.gov.au/hospitals/topics/emergency-departments/emergency-department-care-over-time)
- [AIHW copyright and reuse](https://www.aihw.gov.au/copyright)
- [Australian Privacy Principles](https://www.oaic.gov.au/privacy/australian-privacy-principles)
- [Australian Government AI policy](https://www.digital.gov.au/ai/ai-in-government-policy)
- [National Statement on Ethical Conduct in Human Research](https://www.nhmrc.gov.au/research-policy/ethics/national-statement-ethical-conduct-human-research)
- [TGA population-based analytics software guidance](https://www.tga.gov.au/resources/guidance/understanding-population-based-analytics-software-exclusion)

## Source inspection

Python 3.11 or later is required; the source inventory uses only the standard library.

```sh
python -m unittest discover -s tests -v
python scripts/audit_source.py --catalog-only --out data-audit
```

Use a new output directory under a trusted parent. Catalogue mode inventories fixed public AIHW API metadata URLs and records acquisition times and SHA-256 hashes; it does not download forecasting observations. Any catalogue acquisition failure exits with code 2. The optional document mode (omit `--catalog-only`) also inspects workbook structure without evaluating formulas and exits with code 2 if no workbook is inventoried. It refuses redirects and limits each download to 8 MiB and expanded workbook content to 40 MiB. The website/workbook URLs have returned HTTP 403; no access-control bypass is attempted. Availability is not guaranteed. A catalogue inventory is not validation that a particular table is suitable for forecasting. Source bodies should remain local; `data/` and `artifacts/` are ignored.

The [research-scope assessment](docs/RESEARCH_SCOPE.md) distinguishes privacy law, agency policy, voluntary guidance and research/regulatory boundaries. No forecasting implementation or model results are included yet.

[Source semantics and reproduction](docs/DATA.md) describe the DSS target, rounding, coverage and provenance, plus the reasons the inspected emergency-department sources were not selected. A strict projection validates the 177 reporting months from January 2012 to September 2026; no models have been fitted.

```sh
python -m scripts.audit_history --out history-artifacts
```

This fixed-source audit produces `carer-national.json` containing only national totals and provenance. It also inventories historical Queensland sources without joining incompatible reporting regimes. It requires a new trusted output directory and refuses unreviewed schemas, licences or missing monthly totals. The live command needs network access; tests run offline.
