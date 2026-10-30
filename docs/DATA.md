# Aggregate source semantics

Review date: 30 October 2026. [Recorded source inventory](source-audit.json) contains actual request URLs, acquisition times, hashes, columns and counts. It contains no forecast scores or patient records. Source observations and metadata can be revised after acquisition.

## Queensland quarterly table

Source: Queensland Government, Queensland Health. *Emergency departments – quarterly data*, September 2025. Accessed 30 October 2026. The inventory is a derived summary and does not imply government endorsement.

The [official dataset](https://www.data.qld.gov.au/dataset/emergency-departments-quarterly-data) and its public CKAN catalogue declare **Creative Commons Attribution 4.0**. The [September 2025 resource](https://www.data.qld.gov.au/dataset/emergency-departments-quarterly-data/resource/a9634f60-dd88-4d40-8e80-efaf9b6135c5) exposes a DataStore table. The ordinary CSV download did not yield an accepted HTTP 200 response during inspection; the documented public data API returned the table without credentials or redirects.

The captured API response returned **630 of 630 reported rows** in one request, with the period label `Sep-25`, **105 facility/HHS codes**, and triage labels `1`, `2`, `3`, `4`, `5`, `ALL`. These counts describe the table's structure. They do not establish 105 distinct hospitals: facility, HHS and broader totals may overlap. `ALL` must not be added to its component categories, nor organisational totals added to their component facilities.

The field `Last Month in QTR` identifies a quarter, not a month of observations. The numeric-looking measures are supplied as text. Empty cells, suppression symbols, missing data and genuine zero need distinct treatment; arbitrary text cannot be coerced into zero. No presentation count or outcome measure has been accepted as a model target by this inventory alone.

The catalogue lists a separate [pre-October 2020 dataset](https://www.data.qld.gov.au/dataset/emergency-departments-pre-oct-20). Its existence does not prove compatibility across the boundary. The inspected table covers only one quarter; no continuous historical panel or historical release vintages have been validated. It cannot support a forecasting evaluation by itself.

Reproduce the current source inventory from a trusted local directory:

```sh
python scripts/audit_source.py --qld-only --out qld-artifacts
```

The command downloads two fixed public resources: the catalogue and one bounded DataStore response with a limit of 1,000. It does not follow catalogue URLs or retrieve other periods automatically. The raw response, including source metadata, remains local or in the short-lived CI artifact; only its structural inventory is committed. This is not a production collector or an independent audit of the publisher's data.

## AIHW sources have different grains

The [AIHW monthly activity page](https://www.aihw.gov.au/hospitals/topics/emergency-departments/emergency-department-care-over-time) describes 2018–19 to 2024–25 monthly **average daily presentations**. Rounded daily averages must not be multiplied into purported exact monthly counts. The associated website/spreadsheet requests returned HTTP 403 in the document inspection; no access-control bypass was attempted and no monthly source file was validated.

The [MyHospitals API](https://www.aihw.gov.au/hospitals/other-resources/myhospitals-api) is a separate published interface. Its captured `MYH0035` catalogue contained **70 datasets across 14 annual reporting windows**, 2011–12 to 2024–25, split into five triage categories. Those annual windows cannot be silently treated as monthly data. A successful catalogue request does not validate a forecasting dataset.

The [API specification](https://myhospitalsapi.aihw.gov.au/swagger/v1/swagger.json) states CC BY 3.0, while the general [website copyright policy](https://www.aihw.gov.au/copyright) states CC BY 4.0 subject to separate notices. These notices are not collapsed into an assumed universal licence. No AIHW data-based model or redistributed monthly extract is included.

The [2024–25 technical appendix](https://www.aihw.gov.au/getmedia/159d833f-6f0f-4bd7-9563-c090a1ab8030/Emergency-department-care-2024-25-appendixes.pdf) explains that reporting coverage and collection specifications vary across jurisdictions and years. The collection is not all emergency or urgent care; jurisdiction refers to the hospital, not necessarily a patient's residence. These are interpretation limits, not modelling corrections inferred from the values.

## Research boundary

Only published aggregate data is within scope. No suppression reconstruction, patient linkage, private health data or individual predictions are permitted. The [research-scope assessment](RESEARCH_SCOPE.md) records the applicable legal/policy distinctions and remaining deployment boundaries. An inventory of data access and structure is not ethics approval, clinical validation, an operational forecast or a compliance certificate.
