# M6: Coordinated Riyadh Travel Planner

**Current status:** the formal-v3 comparison completed on 9 November 2026: 120 live records, 60 per condition, 484 HTTP requests. Earlier incomplete attempts remain separate. Saved evidence passed the independent arithmetic/integrity verifier in Colab and locally.

## Problem and design

We investigate whether splitting the Riyadh planning task among a Coordinator, an Attraction/Preference specialist and a Budget/Structural Feasibility specialist improves plans relative to a single generalist. These are three model-based roles. The Coordinator delegates, receives specialist messages and integrates the final itinerary. The budget specialist receives the proposed activities before reporting constraints. The serial topology and one-round stopping rule make communication observable and bound its cost.

The M2 inputs, M4 datasets, twenty M5 cases, requested seeds 11/22/33 and frozen scorer are unchanged. Both conditions must return one hotel, two activities and two restaurants per day, existing IDs and no repeated activities. Restaurants may repeat. Structural feasibility does not establish routing, opening hours, booking or real-world budget sufficiency.

## Implementation

`m6planner/workflow.py` implements typed messages, four model stages, frozen search-tool access and final parsing. `policy.py` specifies shared timeout/retry/pacing/resource limits. `experiment.py` creates counterbalanced paired records with immutable manifests, resumable complete records and interruption guards. `analysis.py` verifies and summarizes both complete conditions, retaining all failures. The Colab notebook disables live execution by default.

Both conditions share model/temperature/SDK/parser/data/cases/scoring and a 10 HTTP request ceiling per whole-system attempt. Treatment allocation is 1/4/4/1 for dispatch/activities/budget/final, with up to 3 whole-system attempts only for approved transient provider codes. Every HTTP request is paced globally by 12 seconds; no parallel agents or repair loop are used. Retries discard earlier message state but retain their usage and traces. See `docs/M6_Experiment_Protocol.md` for the exact execution contract.

## Baseline comparability

The preserved M5 V3 cohort has 60 records, 58 parsed outputs and 49 structurally valid plans. Its primary means are APM 93.50%, RBM 96.67%, HBM 96.67%, IFR 81.67% and RTC 100%. These are historical M5 values, not M6 results.

V3's scheduling differs materially from the shared M6 policy, so it is retained for context rather than used as a perfectly controlled primary comparison. The new M6 baseline used the same policy as the treatment. V3 is not overwritten or repaired.

## Verification actually performed

- 17 new adversarial integration tests passed with the actual pinned SDK and mocked HTTP.
- 49 original M5 tests passed in the existing pinned environment, with no skips in that run.
- A full offline fixture grid of 120 records (60 per condition) exercised the SDK, tools, messages, storage, resume, scoring and summary path. A separate verifier recomputed its results. The fixtures use deterministic provider replies and a fake clock: they are not empirical model-quality, cost or latency observations.
- The existing M5 full-cohort evidence was independently rechecked. See `reports/M6_Verification.json` for exact scope and limitations.

The G01/seed11 pilot completed two live records using 9 HTTP requests. Both outputs received 100% on all five measures. The baseline recovered from an HTTP 504 error; all treatment requests succeeded. System wall times were 58.879s and 84.460s. See `M6_Pilot_Report.md` and `M6_Pilot_Audit.json`. The pilot remains separate; this single pair cannot establish treatment benefit.

## Controlled results — formal-v3

20 unchanged cases × 3 requested seeds × 2 conditions. All failures remain in the denominator. Each condition has 60 complete records.

| Metric (%) | Baseline mean ± sample SD | Three-agent mean ± sample SD | Paired difference (percentage points) |
|---|---:|---:|---:|
| APM | 95.17 ± 15.09 | 88.83 ± 28.21 | -6.33 |
| RBM | 98.33 ± 12.91 | 91.67 ± 27.87 | -6.67 |
| HBM | 98.33 ± 12.91 | 91.67 ± 27.87 | -6.67 |
| IFR | 83.33 ± 37.58 | 80.00 ± 40.34 | -3.33 |
| RTC | 100.00 ± 0.00 | 100.00 ± 0.00 | +0.00 |

| Resource/reliability | Baseline | Three-agent |
|---|---:|---:|
| Parsed outputs | 59 | 55 |
| Structurally valid plans | 50 | 48 |
| HTTP requests | 120 | 364 |
| Mean system wall time (s) | 23.818 | 72.777 |
| Mean processing time (s) | 2.465 | 6.832 |
| Mean pacing wait (s) | 21.353 | 65.945 |

Baseline failures: 1 final-parse failure and 9 structural-output failures. Treatment failures: 5 coordination-message failures and 7 structural-output failures. There were no terminal provider errors in this cohort and no whole-system retry waits. These retained failures are part of the architectural reliability comparison. All five coordination failures occurred at the budget stage (G06/G11/G15/G18/G19, seed33) with invalid budget JSON. The baseline parse failure occurred at G07/seed22. Structural failures involved repeated activities, concentrated in the unchanged constrained cases G05/G08/G15.

The treatment did not improve the observed mean scores: APM, RBM, HBM and IFR were lower; RTC remained 100% in both. Its mean wall time was about 3.06 times the baseline and observed total tokens were 541,612 versus 172,166 (about 3.15 times). These descriptive findings do not establish statistical significance or a universal ranking. Role-message failures are an added failure surface; the unchanged data ceilings also limit attainable preference matching.

Complete run/case/seed variation, seed means and paired differences are in `m6_runs/formal-v3/analysis/M6_Comparison.json`; per-record results are in `M6_Results.csv`. Cost estimates are separate in `M6_Cost_Estimates.json`: standard uncached list-price equivalents of observed usage, not a receipt. Actual monetary billing remains unknown.

## Tool-grounding exception found by independent review

Among the 114 parsed final outputs, treatment G05/seed11 selects ACT_00073, which does not appear in any successful activity-tool result from that final attempt. It is a valid dataset ID, so the unchanged M5 scorer still awards APM90 and IFR100. This is a task-grounding violation outside the frozen metric definitions; those scores are retained, not corrected or rerun. Thus even 100% RTC and a structurally valid plan do not prove that every chosen item came from the returned tools. The independent audit reports this exception explicitly in reports/M6_Formal_Audit.json.

## Interpretation and limitations

The parsed M5 outputs already reached case-specific APM ceilings and 100% hotel/restaurant budget matching, leaving little improvement headroom. Structural reliability, service failures, coordination failures and added resource use may distinguish the architectures more clearly. G05/G08/G15 remain in the study with their original APM ceilings.

Equal aggregate HTTP ceilings control maximum resources but do not guarantee equal practical difficulty: a fixed role split can disadvantage a specialist. Serial communication increases context and can increase latency. Model availability was observed in this pilot and completed formal cohort; future availability, quotas and seed effects remain uncertain. Token observations are not billing receipts; missing cost remains null. Any final claim of benefit must follow real comparative evidence, including negative or inconclusive findings.

## Formal-v1 evidence loss

The progress log reaches 114 records/463 requests, but only 12 raw records are durably recovered. No complete formal-v1 result is reported; its missing outputs are not pooled into formal-v3 or the pilot. See `M6_Execution_Incident.md` for the evidence, limits and verified persistent-storage recovery and subsequent daily-quota stop.

Formal-v2: durable Drive storage was independently verified before execution. The recovery stopped after five HTTP requests when the provider reported the daily free-tier request quota exhausted. One baseline record is complete; the treatment journal is interrupted. These do not constitute a paired comparison or a full formal cohort. No further automatic requests or billing changes were made.

## Persistent completion

Formal-v3 was a fresh cohort after the daily quota reset. It preserved the frozen experimental code and all model/data/scoring settings. Its controller changes only the version and remaining cumulative request budget to 2943, reserving 657 prior requests (conservative upper bound, including 5 from formal-v2). Journals and records were written directly to Drive, with a checked checkpoint ZIP after every six records. The complete archive was downloaded and CRC-checked locally. No paid upgrade or model substitution was used.
