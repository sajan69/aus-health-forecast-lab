# Australian Health Forecast Lab

Research prototype for forecasting recorded Australian health-service activity from published aggregate statistics. The focus is retrospective evaluation of emergency-department activity for planning research, with seasonal baselines, time-based validation and explicit uncertainty.

Recorded activity is not a measure of unmet need. Historical releases cannot establish a current operational forecast, and revised data cannot establish what was knowable at an earlier date.

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
python scripts/audit_source.py --out data-audit
```

Use a new output directory under a trusted parent. The command inventories fixed public AIHW document/API URLs, records acquisition times and SHA-256 hashes, and reads workbook structure without evaluating formulas. It refuses redirects and limits each download to 8 MiB and expanded workbook content to 40 MiB. Network failures are recorded; a missing usable workbook exits with code 2. Availability is not guaranteed. This is a document inventory, not validation that a particular table is suitable for forecasting. Source bodies should remain local; `data/` and `artifacts/` are ignored.

The [research-scope assessment](docs/RESEARCH_SCOPE.md) distinguishes privacy law, agency policy, voluntary guidance and research/regulatory boundaries. No forecasting implementation or model results are included yet.
