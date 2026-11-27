# Review update status

Updated 27 November 2026. This page separates implemented changes from experiments that still need saved results.

| Review request | Current status |
|---|---|
| Preserve the approved data and original 20 cases | Preserved without changing the CSVs or G01–G20 inputs. |
| Add about 20 harder cases | H01–H20 prepared. Each has a verified feasible example. No witness is sent to the models. |
| Count broken constraints | Implemented and tested for structure, distance, hotel cost and interest quotas. |
| Give both systems the same distance/checking tools | Implemented in the revised shared tool set. |
| Give the feasibility specialist a checking role | Implemented in the revised team workflow. |
| Limit and log repairs | At most three rounds; initial and revised plans, fixed and introduced problems, and tool counts are saved. |
| Use traceable V3 evidence | All 60 original records rescored; original baseline remains unchanged. V2 is historical only. |
| Report variation and pass³ | Original baseline rechecked; pass³ is 80%. Revised analysis code is prepared. |
| Paired tests and 95% intervals | Implemented at case level. New comparative results require complete live cohorts. |
| Verify repeated-seed behavior | G01 ran twice with seed 11 and returned the same readable plan. This is one checked pair, not a general determinism claim. |
| Remove components and try another model | Experiment schedules prepared; live results pending. |
| Test a higher-capacity coordinator | Separate condition prepared; model availability and access must be checked. |
| Estimate cost per case | Dated prices and usage-based calculation prepared for the selected text models; actual billing remains separate. Original V3 per-case estimates are available. |
| Explain failures using real examples | Original M5 failures recounted and saved. Revised failure reports will use new run evidence. |
| Cite datasets and check licences | Five upstream sources identified. Restaurant licence is Unknown; shopping-source terms conflict. These points remain unresolved. |

## Verification completed

Twenty-three new offline tests passed. They include an independent route-distance check, adversarial plan checks, a complete fixture pilot, journal replay, recovery checks and refusal of partial comparative results. These are software tests, not live model-performance results.

The original evidence verifier passed for all 60 M5 baseline records. The original test suite ran with 45 passing tests and eight optional SDK tests skipped because that SDK is not installed in this local environment. No claim is made that those eight tests ran during this revision.

## Experiments

No new formal hard-case results are claimed on this page. Completed live experiments will be linked here only after their saved evidence has been checked. Earlier M6 results remain separate and do not stand in for the revised comparison.

The [first live development pilot](reports/PILOT_v1.md) completed both systems successfully. Its saved evidence passed verification in Colab and locally. It is separate from the formal tests.

The [final pilot and repeated-seed check](reports/PREFLIGHT_v2.md) passed in Colab and locally. The new formal grid has started; the first request encountered a recorded HTTP 503 service error. That failed record is preserved, and remaining requests resume without replacing it. No full comparative result is claimed.

The separate [M6 review revision](https://github.com/BashaierAwal/riyadh-travel-planner-m6-multi-agent/tree/m6/review-revision) contains the revised implementation and retains the earlier experiment as history.

An execution interruption left the first partial grid incomplete. [Recovery is documented here](RECOVERY.md). The primary complete comparison uses main-v2 with the same frozen code and settings; the earlier records and unfinished journal are preserved separately.

The [27-record checkpoint](reports/PROGRESS_27.md) passed local evidence verification. The revised main grid remains incomplete. The controller continues past recorded internal step-limit failures without retrying or replacing them.
