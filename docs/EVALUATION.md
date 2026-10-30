# Recorded retrospective evaluation

The source is one DSS September 2026 revised release of national Carer Payment recipient counts, with 177 months from January 2012 to September 2026. [Data definitions and licence](DATA.md) remain part of every interpretation. These are real published aggregate observations, not synthetic outcomes or customer data. No prospective or government deployment validation was performed.

## Reproduction and provenance

The [fixed method](METHOD.md) was committed at [d2e32a5](https://github.com/sajan69/aus-health-forecast-lab/commit/d2e32a519dace2eb4acfb45a0e9fee5cb76101b3) before computing predictive errors. The recorded results were executed locally using the installed wheel from code [4ffb7b6](https://github.com/sajan69/aus-health-forecast-lab/commit/4ffb7b679b2cf745671cb97f4ca05c174c3ec98a). [Evaluation JSON](reports/evaluation.json) records all metrics, calibration and the 66 selected-model holdout predictions. [Benchmark JSON](reports/benchmark.json) records every timing repeat and environment. The full 1,356 candidate prediction records are produced by the CLI and retained in CI artifacts, rather than duplicated in the recorded summary. Later CI runs are independent validation, not the source of these local timing samples.

```sh
aus-health-forecast evaluate examples/carer-national-sep2026.json --out NEW_EVALUATION.json
aus-health-forecast evaluate examples/carer-national-sep2026.json --out NEW_REPORT.html --format html
aus-health-forecast benchmark examples/carer-national-sep2026.json --out NEW_BENCHMARK.json --repeats 3
```

The frozen input's selected-row SHA-256 is `6a72d3c5d9f5dac939c7173d5fc883cff4a28f5732e203e71954beb0c58b6c2c`; raw workbook SHA-256 is `af25df58fec196687935f950c1802640394dbe381ecada03fc387edb70b60d52`. These identify reviewed bytes and rows, not historical release vintages or publisher authentication. [Example HTML](../examples/report.html) is a standalone derived report with no remote assets.

## Model comparison

There are 91 development origins, with 273 predictions per model, all ending before October 2024. Pooled development MAE was 1,276.685 for last value, 6,224.542 for seasonal naive, 1,069.300 for damped Holt and 997.649 for ridge change. Ridge was selected using those development scores. No parameters or winner were changed in response to holdout errors.

There are 22 common holdout origins with three horizons, giving 66 dependent forecasts per model. Earlier observations enter each later refit; selection and interval widths stay fixed. The method document gives the unequal target-date ranges for each horizon.

| Model | Holdout pooled MAE | Holdout pooled RMSE | Bias: prediction minus observation |
| --- | ---: | ---: | ---: |
| Last value | 1,403.561 | 1,696.207 | -1,392.197 |
| Seasonal naive | 10,115.303 | 10,577.348 | -10,115.303 |
| Damped Holt | 873.085 | 1,107.271 | -214.720 |
| Ridge change, selected | 719.915 | 896.892 | +162.687 |

The seasonal baseline underpredicted all 66 cases in this period. It carries an older level forward while the published caseload was rising. This is a descriptive finding about this release and period, not proof of a causal driver or a universally superior model. Last value underpredicted 62/66; selected ridge underpredicted 31/66. No significance test or independent-sample confidence claim is made.

| Selected ridge horizon | Cases | MAE | RMSE | Bias | MASE | Underpredicted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 month | 22 | 472.873 | 545.869 | +65.863 | 0.052 | 10 |
| 2 months | 22 | 772.162 | 939.369 | +159.341 | 0.085 | 11 |
| 3 months | 22 | 914.711 | 1,110.342 | +262.857 | 0.100 | 10 |

MASE uses each origin's training-prefix seasonal scale, not holdout observations. All 66 selected-model cases had a positive scale. A zero scale is explicitly null in the implementation and tests. Errors evaluate published rounded counts, not unrounded administrative truth.

## Interval behaviour and temporal variation

| Horizon | Nominal 80%: covered / cases | Mean width | Nominal 95%: covered / cases | Mean width |
| --- | ---: | ---: | ---: | ---: |
| 1 month | 20/22 | 1,773.447 | 22/22 | 2,627.315 |
| 2 months | 18/22 | 2,773.360 | 22/22 | 5,964.189 |
| 3 months | 21/22 | 3,979.007 | 22/22 | 9,450.096 |

All nominal 95% intervals covered their observed targets in this small sample; that is not a 100% future-coverage guarantee. Widths can be conservative. Calibration used dependent development residuals after model selection, and future policy or reporting changes can break the relationship.

Selected-model development MAE was 911.436 for targets before 2020 (105 overlapping cases), 1,125.772 for 2020–2021 (72 cases), and 995.851 from 2022 through the development boundary (96 cases). These pre-specified temporal summaries illustrate variation; they do not isolate COVID effects or the March 2020 program transfer. There is no regional or demographic validation from this national-only input.

## Bounded compute measurement

Three complete offline evaluations were measured on 30 October 2026 after the installed-wheel tests. Each repeat reads and validates the same 177-month file, performs all four candidates at 91 development and 22 holdout origins, selects/calibrates, computes metrics and generates three series-end estimates. Every repeat checked record counts and identical selected-model/MAE outcomes. The workload has 1,356 candidate point predictions plus three series-end estimates.

| Repeat | Wall milliseconds |
| --- | ---: |
| 1 | 2,686.104 |
| 2 | 2,625.856 |
| 3 | 2,738.540 |
| Median | 2,686.104 |

Timer: `perf_counter`. Includes input reads, strict parsing/hash validation, fitting, selection, calibration, metrics, environment metadata and series-end extrapolation. Excludes CLI/dependency imports, source acquisition, output serialization/writes, correctness assertions, network, TLS and browser rendering. No explicit warmup or cache clearing; earlier tests and OS caches may benefit repeats. This is a single-client shared-host workload, not a throughput/capacity result or an improvement against a performance baseline.

Environment: Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, pandas 2.3.3, statsmodels 0.15.0, scikit-learn 1.9.1, threadpoolctl 3.7.0; Linux 6.18.57 x86-64/glibc 2.39, nine reported logical CPUs. Numerical pools were limited to one; recorded OpenBLAS version 0.3.30. Host scheduling and filesystem performance are not controlled. Exact environment and raw samples are in the JSON record.

## Practical limits

This prototype demonstrates an inspectable way to compare short-horizon national administrative-caseload models. It does not establish staffing needs, care demand, funding requirements, entitlement decisions, fraud, clinical benefit, government adoption or legal compliance for deployment. Source revisions and publication delays mean this is a revised-history retrospective benchmark. October–December 2026 series-end estimates are indexed from September data, not an assurance that all three months were in the future when that release was acquired.

The [research-scope assessment](RESEARCH_SCOPE.md) distinguishes source permissions, applicable law, agency policy, voluntary guidance and institutional/regulatory decisions. Human review and adopter-specific validation remain necessary for any proposed government use.

## Verification evidence

[CI run 41061064361](https://github.com/sajan69/aus-health-forecast-lab/actions/runs/41061064361) at the measured source commit passed all seven jobs: 19 source tests on Python 3.11–3.13, 17 installed-wheel package tests and full real-aggregate evaluation on Python 3.12–3.13, plus two live source-audit jobs. The Python 3.12 job additionally generated HTML/CSV exports, completed the three-repeat workload and passed four real Chromium checks. Its timings differ from the recorded local sample and are not substituted for it.

The checks exercise prefix boundaries, holdout mutation invariance of development selection/calibration, direct model behaviour, failed optimisation, null MASE scale, interval ranks and recomputed case metrics. The browser checks inspect rendered values/chart/warnings, expandable provenance, 390px body fit with horizontal scrolling, and an inert HTML payload without network requests, dialogs or page errors. Desktop/mobile screenshots and machine case results are CI artifacts. Local installed-wheel verification passed the same 36 Python tests and four browser checks; the local Chromium 143 binary differs from CI's downloaded browser. This is functional verification, not exhaustive security, accessibility or predictive validation.
