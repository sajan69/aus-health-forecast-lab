# Research scope and Australian governance

Source review: 30 October 2026. This is a documented design assessment for a public-aggregate research prototype, not legal advice, institutional ethics approval or a regulator's determination.

## Intended purpose and data boundary

The intended question is whether simple forecasting methods improve on seasonal baselines when predicting recorded emergency-department activity in historical published statistics. Intended readers are analysts reviewing methods and uncertainty. Outputs are not instructions for staffing, funding, clinical care or individual decisions. Recorded presentations describe use of reporting services; they do not measure unmet need, resolved illness or population health by themselves.

Only published aggregate tables are within scope. Patient records, identifiers, unit-record files, linkage, protected-attribute risk scores and private health-system extracts are outside scope. Source acquisition uses fixed official URLs without credentials, cookies, redirects or automated retries. A failed download is recorded rather than bypassed. Public availability alone does not establish safe reuse: the source's licence, definitions, suppression and aggregation remain relevant.

## Applicable obligations and guidance

| Area | Relevance to this prototype | Boundary for adoption |
| --- | --- | --- |
| Privacy law | The [Australian Privacy Principles](https://www.oaic.gov.au/privacy/australian-privacy-principles) govern personal-information handling by covered entities. The design excludes personal data; no statutory exemption is asserted merely because a file is public. | An adopter must assess its entity, data and jurisdiction. Any addition of personal information changes this assessment. |
| Queensland privacy | The [Queensland Privacy Principles](https://www.oic.qld.gov.au/government/privacy/queensland-privacy-principles) concern agencies' handling of personal information under the Information Privacy Act 2009. This personal research repository is not presented as a Queensland agency system. | Agency/contractor applicability, privacy-impact assessment and security arrangements require the adopting organisation's review. The guidance-page date is not treated as a legislative commencement date. |
| Commonwealth AI policy | [DTA policy v2.1](https://www.digital.gov.au/ai/ai-in-government-policy), updated 21 October 2026, applies to covered non-corporate Commonwealth entities, with exceptions. It is a governance reference here, not a private-project certification. | Agencies assess in-scope criteria during design. In-scope uses require an [impact assessment](https://www.digital.gov.au/ai/ai-in-government-policy/ai-use-case-impact-assessment), completed with risk treatments before deployment, then monitoring. |
| Ethical AI | The [eight Australian AI Ethics Principles](https://www.industry.gov.au/publications/australias-ai-ethics-principles) are voluntary. That page identifies the newer six-practice Guidance for AI Adoption. Ethical design remains necessary even without patient data. | Transparency, oversight, testing, challenge/correction and community impacts need context-specific evidence; aggregate accuracy does not certify fairness. |
| Medical-device boundary | [TGA item 14N guidance](https://www.tga.gov.au/resources/guidance/understanding-population-based-analytics-software-exclusion) distinguishes population analytics from individual clinical purposes. This prototype makes no individual disease predictions or treatment recommendations. | Intended purpose and every feature matter. No TGA approval or exclusion ruling is claimed; a clinical feature requires a fresh regulatory assessment before supply/use. |
| Research ethics | The [2025 National Statement](https://www.nhmrc.gov.au/research-policy/ethics/national-statement-ethical-conduct-human-research) took effect on 23 June 2026. No participants are recruited and no individual records are sought. | This is not an HREC exemption determination. Institutional research, funding, participant involvement or a changed data/use context requires the appropriate research-governance screening. |
| Copyright | [AIHW's reuse policy](https://www.aihw.gov.au/copyright) permits CC BY 4.0 reuse subject to exceptions, including separate notices and third-party material. The actual source file must be checked. | Attribute source material and distinguish derivatives; do not imply endorsement or reuse logos. |

State/territory policies are not interchangeable with Commonwealth policy. No claim of Queensland or other state operational readiness follows from this review. Government adoption remains outside the prototype's intended purpose.

## Harm and evidence limitations

Underprediction could make an unsupported capacity decision appear justified. Regional averages can hide within-region access barriers; small jurisdictions can be poorly represented by a national error average. Neither a low error nor a narrow interval justifies automatic service cuts. Published small-cell suppression must remain intact; no reconstruction or individual linkage is permitted. Indigenous-specific interpretation would require appropriate Indigenous data governance and engagement, rather than inferring community needs from general regional totals.

Publication lag, revised history, COVID-era changes and reporting coverage can alter apparent predictability. An evaluation using the latest revised series is retrospective, not proof of real-time forecasting performance. Source units and dates belong alongside every result. Model estimates do not establish causation, clinical benefit or government adoption.

This assessment supports source inspection and methods research within the stated boundary. No operational, clinical or government deployment has been approved. Changes to data, purpose or users require reassessment before the expanded use.
