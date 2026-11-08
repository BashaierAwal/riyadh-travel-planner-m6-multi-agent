# M6: Coordinated Riyadh Travel Planner

**Current status:** implementation and offline verification complete; live pilot and controlled experiments pending approval. This is an implementation report, not a completed experimental-results report. Prepared 8 November 2026.

## Problem and design

We investigate whether splitting the Riyadh planning task among a Coordinator, an Attraction/Preference specialist and a Budget/Structural Feasibility specialist improves plans relative to a single generalist. These are three model-based roles. The Coordinator delegates, receives specialist messages and integrates the final itinerary. The budget specialist receives the proposed activities before reporting constraints. The serial topology and one-round stopping rule make communication observable and bound its cost.

The M2 inputs, M4 datasets, twenty M5 cases, requested seeds 11/22/33 and frozen scorer are unchanged. Both conditions must return one hotel, two activities and two restaurants per day, existing IDs and no repeated activities. Restaurants may repeat. Structural feasibility does not establish routing, opening hours, booking or real-world budget sufficiency.

## Implementation

`m6planner/workflow.py` implements typed messages, four model stages, frozen search-tool access and final parsing. `policy.py` specifies shared timeout/retry/pacing/resource limits. `experiment.py` creates counterbalanced paired records with immutable manifests, resumable complete records and interruption guards. `analysis.py` verifies and summarizes both complete conditions, retaining all failures. The Colab notebook disables live execution by default.

Both conditions share model/temperature/SDK/parser/data/cases/scoring and a 10 HTTPrequest ceiling per whole-system attempt. Treatment allocation is 1/4/4/1 for dispatch/activities/budget/final, with up to 3 whole-system attempts only for approved transient provider codes. Every HTTP request is paced globally by 12 seconds; no parallel agents or repair loop are used. Retries discard earlier message state but retain their usage and traces. See `docs/M6_Experiment_Protocol.md` for the exact execution contract.

## Baseline comparability

The preserved M5 V 3 cohort has 60 records,58 parsed outputs and 49 structurally valid plans. Its primary means are APM 93.50%, RBM 96.67%, HBM 96.67%, IFR 81.67% and RTC 100%. These are historical M5 values, not M6 results.

V 3's scheduling differs materially from the shared M6 policy, so it is retained for context rather than used as a perfectly controlled primary comparison. A separately approved M6 baseline will use the same policy as the treatment. V 3 is not overwritten or repaired.

## Verification actually performed

- 17 new adversarial integration tests passed with the actual pinned SDK and mocked HTTP.
- 49 original M5 tests passed in the existing pinned environment, with no skips in that run.
- A full offline fixture grid of 120 records (60 per condition) exercised the SDK, tools, messages, storage, resume, scoring and summary path. A separate verifier recomputed its results. The fixtures use deterministic provider replies and a fake clock: they are not empirical model-quality, cost or latency observations.
- The existing M5 full-cohort evidence was independently rechecked. See `reports/M6_Verification.json` for exact scope and limitations.

No live M6 model requests have been performed. Experimental results remain pending.

## Controlled results — pending

| Required comparison | New baseline | Three-agent treatment |
|---|---|---|
| Expected formal records |60; not run |60; not run |
| APM/RBM/HBM/IFR/RTC mean |Pending |Pending |
| Run/case/seed sampleSD and seed means |Pending |Pending |
| Measured system latency and waits |Pending |Pending |
| Observed usage and monetary-cost status |Pending |Pending |
| Trace-supported failure analysis |Pending |Pending |

The software exports these tables from saved complete cohorts; it does not fill them with mock results. The approved live pilot, formal 120 records and final analysis are required before M6 can be declared complete.

## Interpretation and limitations

The parsed M5 outputs already reached case-specific APM ceilings and 100% hotel/restaurant budget matching, leaving little improvement headroom. Structural reliability, service failures, coordination failures and added resource use may distinguish the architectures more clearly. G05/G08/G15 remain in the study with their original APM ceilings.

Equal aggregate HTTP ceilings control maximum resources but do not guarantee equal practical difficulty: a fixed role split can disadvantage a specialist. Serial communication increases context and can increase latency. Provider quotas/model availability and seed effects remain unverified. Token observations are not billing receipts; missing cost remains null. Any final claim of benefit must follow real comparative evidence, including negative or inconclusive findings.
