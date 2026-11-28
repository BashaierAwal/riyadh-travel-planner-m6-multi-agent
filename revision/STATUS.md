# Review update status

Updated 28 November 2026. This page separates implemented changes from experiments that still need saved results.

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
| Paired tests and 95% intervals | Implemented at case level. New comparative results require a complete predefined group or the complete live grid. |
| Verify repeated-seed behavior | G01 ran twice with seed 11 and returned the same readable plan. This is one checked pair, not a general determinism claim. |
| Remove components and try another model | Second-model grid started; component-removal grids pending. |
| Test a higher-capacity coordinator | Different-coordinator condition registered; live results pending. |
| Estimate cost per case | Dated prices and usage-based calculation prepared for the selected text models; actual billing remains separate. Original V3 per-case estimates are available. |
| Explain failures using real examples | Original M5 failures recounted and saved. Revised failure reports will use new run evidence. |
| Cite datasets and check licences | Five upstream sources identified. Restaurant licence is Unknown; shopping-source terms conflict. These points remain unresolved. |

## Verification completed

Twenty-three new offline tests passed. They include an independent route-distance check, adversarial plan checks, a complete fixture pilot, journal replay, recovery checks and refusal of partial comparative results. These are software tests, not live model-performance results.

The original evidence verifier passed for all 60 M5 baseline records. The original test suite ran with 45 passing tests and eight optional SDK tests skipped because that SDK is not installed in this local environment. No claim is made that those eight tests ran during this revision.

Two additional numeric-replay tests passed in both working copies. A [cross-platform check](reports/NUMERIC_REPLAY.md) confirmed identical rule decisions for all twenty feasible examples despite tiny route-number rounding differences. Raw hashes and all non-route checks remain exact.

The [registered queue](reports/PRIORITY_EXECUTION.md) prioritises the new hard cases after finishing a started original case. All forty registered cases remain planned; no data or scoring change is made.

## Experiments

The [current progress record](reports/PROGRESS.md) documents the verified 103-record main-grid and 79-record second-model snapshots, quota and service stops, and the second-model continuation. The revised grids remain incomplete; no new hard-case comparative result is claimed.

The [first development pilot](reports/PILOT_v1.md) and [final pilot and repeated-seed check](reports/PREFLIGHT_v2.md) are separate from the formal grids. Their saved evidence passed Colab and local checks.

The original partial main grid and its unfinished journal remain preserved. [Recovery](RECOVERY.md) explains why main-v2 is the primary new grid and why the earlier records are not pooled with it.

The separate [M6 review revision](https://github.com/BashaierAwal/riyadh-travel-planner-m6-multi-agent/tree/m6/review-revision) retains the earlier experiment as history. [Original-case coverage limits](reports/ORIGINAL_CASE_COVERAGE.md) are documented without changing the approved data or requests.

Three complete-group reporting tests also passed in each working copy. The reporting guard refuses the incomplete live hard-case group; it cannot produce a comparison from whichever cases happened to finish first.

## Full study scope confirmed on 28 November 2026

The complete 840-record plan is retained with Gemini. There is no current submission deadline constraint. Hard-case groups run first, followed by the remaining original-case comparisons. A separately saved, bounded service-error supervisor can wait five minutes and continue unstarted records after temporary provider failures; it stops at quota or inspection errors.

A second service supervisor adds readiness checks before controller starts, with bounded waits and no new case attempt while a check fails. Its six software tests passed in each working copy. This operational change preserves the frozen generation settings and all saved outcomes. See the [execution appendix](reports/PRIORITY_EXECUTION.md).
