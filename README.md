# Australian Health Forecast Lab

Research prototype for forecasting published aggregate Australian welfare caseload. The selected series is the national Carer Payment recipient total from the DSS monthly time series. It supports methods research using chronological evaluation and explicit uncertainty. It does not measure clinical demand or unmet caring need.

Recipient totals reflect program rules and recorded administrative status, including suspended and zero-rate recipients. Historical releases cannot establish a current operational forecast, and revised data cannot establish what was knowable at an earlier date.

## Intended use and limits

This repository is for reproducible, aggregate-level research. It is not intended for individual diagnosis, triage, treatment, welfare eligibility, or autonomous resource-allocation decisions. No patient records, identifiers, record linkage or private health data are accepted within this research scope.

Dataset licensing, units, coverage, publication delays, suppression and permitted reuse require source-specific review before analysis. Australian privacy, ethics, AI-governance and medical-device requirements depend on the actual data, intended use and adopting organisation. This project does not establish government endorsement, regulatory approval, or compliance for a deployment.

## Offline forecast evaluation

Python 3.12 or later is required for the forecasting package. The source-audit scripts also work on Python 3.11. No provider account, key, cloud deployment or paid data is needed.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install .
aus-health-forecast validate examples/carer-national-sep2026.json
aus-health-forecast evaluate examples/carer-national-sep2026.json --out evaluation.json
aus-health-forecast evaluate examples/carer-national-sep2026.json --out report.html --format html
aus-health-forecast evaluate examples/carer-national-sep2026.json --out metrics.csv --format csv
aus-health-forecast benchmark examples/carer-national-sep2026.json --out benchmark.json --repeats 3
```

Open `report.html` locally. It has an uncertainty chart, all four candidates' errors, empirical interval coverage, intended-use limits and expandable provenance. HTML needs no scripts, server or external assets. JSON includes every development and holdout prediction; CSV contains 24 model/horizon/stage summary rows. Exports require new paths and refuse overwrite. Each evaluation command recomputes the fixed experiment; it does not submit data anywhere.

The selected ridge model's reserved-period MAE is approximately 720 published recipients, compared with 1,404 for last value and 873 for damped Holt. These are 66 overlapping forecasts across three horizons, not independent trials or a claim of government suitability. The source and full method matter more than a single score.

## Architecture and verification

The package validates one reviewed release and its hashes, constructs expanding chronological prefixes, fits fixed candidates, locks the development winner and calibration, evaluates reserved-period errors, then serializes bounded outputs. The application does not deserialize fitted models or execute user-supplied code. No database or service daemon is required for this small national series.

```sh
python -m unittest discover -s tests -v
python -m unittest discover -s forecast_tests -v
```

The 19 source tests are separate from 17 package tests. CI runs source tests on Python 3.11–3.13 and built-wheel package tests/evaluation on Python 3.12–3.13. Chromium checks the generated desktop/mobile report, provenance and inert HTML payloads. Live catalogue/source checks are separate from offline tests. [Input and export controls](docs/SECURITY.md) describe the trusted-local boundary.

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

The [research-scope assessment](docs/RESEARCH_SCOPE.md) distinguishes privacy law, agency policy, voluntary guidance and research/regulatory boundaries. The [evaluation method](docs/METHOD.md) defines the chronological split and model selection. [Recorded findings](docs/EVALUATION.md) distinguish this retrospective benchmark from operational validation.

[Source semantics and reproduction](docs/DATA.md) describe the DSS target, rounding, coverage and provenance, plus the reasons the inspected emergency-department sources were not selected. A strict projection validates the 177 reporting months from January 2012 to September 2026; the evaluation uses the frozen release without live acquisition.

```sh
python -m scripts.audit_history --out history-artifacts
```

This fixed-source audit produces `carer-national.json` containing only national totals and provenance. It also inventories historical Queensland sources without joining incompatible reporting regimes. It requires a new trusted output directory and refuses unreviewed schemas, licences or missing monthly totals. The live command needs network access; tests run offline.
