# M6 Experiment Protocol — m6-shared-v1

Status: implementation/offline checks and the separately approved G01/seed11 paired live pilot are complete. Formal experiments require separate project-lead approval. Date: 8 November 2026.

## Research question and controlled factor

Does coordinated task organization by three model-based agents improve Riyadh itinerary planning compared with one generalist agent? The manipulated factor is architecture/task organization. Both conditions share unchanged M4 CSV bytes (1,125 activities/19,345 restaurants/55 hotels), twenty golden cases, requested seeds 11/22/33, model `gemini-3.5-flash-lite`, temperature 0, SDK 1.30.0, search functions/candidate fields/ranking/defaults, output requirements, final parser and `m5-offline-v3` scorer. Provider seed behavior and future model availability are unverified; do not silently switch models.

Both conditions must return one hotel for the trip, two activities and two restaurants each day, no repeated activities, existing dataset IDs and only tool-returned IDs. Restaurants may repeat. Locations do not authorize new routing/opening-hour/booking constraints. Budget categories are dataset labels, not SAR trip-cost estimates.

## Architecture and communication

Serial hub, three LLM-based roles, four bounded stages:

1. Coordinator: delegate tasks in a `dispatch` message with `activity_task` and `budget_task` strings.
2. Attraction/Preference specialist: call `find_activities`; send an `activities` message containing numbered days, activity IDs and notes.
3. Budget/Structural Feasibility specialist: receive the activities message; call `find_restaurants` and `find_hotels`; send a `budget` message containing hotel, daily restaurant IDs, structural/budget checks and notes.
4. The SAME Coordinator role: receive both messages plus actual tool-result payloads; resolve conflicts and return the final itinerary. No further tool calls or discussion.

Each stage is a model invocation through the pinned SDK; specialist tool calls are chosen by that model. The Python scheduler controls order and JSON message envelopes, not the actual recommendations. The final Coordinator has the same returned candidate information, not exclusive fallback IDs. Role prompts retain the baseline task requirements and express responsibilities. The baseline prompt is byte-for-byte unchanged.

Messages retain raw model text, parsed typed payloads, prompts, prompt hashes, tool arguments/results and HTTP request/response bodies with credential redaction. Intermediate envelopes/type errors terminate the workflow; content quality/counts/repetition are not silently repaired by the scheduler. The final output uses the frozen baseline normalization and strict parser.

Termination: one dispatch → one activity response → one budget/check response → one final response, or an earlier recorded failure. There is no iterative repair loop. Valid JSON with structural violations is scored unchanged. A structurally correct output is not a claim of real-world feasibility.

## Shared execution and failure policy

| Setting | Both conditions |
|---|---|
| Request timeout |30 seconds |
| SDK internal attempts |1; no hidden SDK retries |
| Whole-system HTTP ceiling |10 per workflow attempt, including tool follow-ups |
| Outer attempts |Up to 3; at most 30 HTTP per case/seed/condition |
| Treatment allocation |Coordinator dispatch 1; activities 4; budget 4; Coordinator final 1 |
| Baseline allocation |Same total 10; one generalist manages its tools |
| Parallelism |None; conditions and all agents run serially |
| Pacing |At least 12 seconds between starts of every HTTP request, across all agents and records in the session |
| Session startup |Live CLI waits 12 seconds before its first request, also protecting rapid resumes |
| Retriable provider codes |429/500/502/503/504 only |
| Retry delay |At least 5 seconds after attempt 1,10 after attempt 2; take the maximum with valid HTTP Retry-After/date and Google RetryInfo delay |
| Other errors |No outer retry for parse/type, budget exhaustion,404/authentication, or unclassified failures |

Stage caps count real HTTP follow-ups, not just Python/SDK calls. Coordinator stages have no tools and need one HTTP request each. The shared transport ceiling independently enforces aggregate attempt/record/session limits. A full worst-case 30-request reservation is required before starting a new record; unused capacity is retained. Pacing persists across roles/conditions; it is not 12 seconds per agent. Invalid/nonfinite provider retry hints are ignored, never passed as infinite sleeps. No claim is made that 12 seconds guarantees current quota availability. A long valid provider wait must be respected; the user can interrupt and preserve the journal.

A transient provider failure restarts the ENTIRE workflow, not just the failed specialist. Message/candidate state resets; all prior traces/usage remain. Final RTC uses only the final workflow attempt. A malformed required specialist message produces a coordination failure and no final itinerary. A malformed final response is a parse failure. Structural failure is an evaluated final itinerary, not a generation retry trigger. Abandoned attempts never supply final candidates or RTC. Terminal service/budget/program failures stop the current batch after saving their record; saved failed records are not regenerated on resume.

The same caps are a resource-controlled design choice; fixed role allocation can constrain the treatment differently and is an explicit limitation. Tests establish that the workflow fits this allocation under simulated responses, not that live models will always do so.

## Baseline decision, cohort and ordering

V3 remains immutable historical evidence. The new 12 second **per-HTTP** scheduler differs materially from V3's initially unpaced chunks and later 12 second **inter-record** pauses. Therefore the primary M6 comparison requires a separately versioned baseline generated under this shared policy; V3 is not labelled a perfectly controlled comparator. No formal M6 baseline cohort has been run yet; the single pilot baseline is stored separately. Architecture change alone is not a reason to regenerate it.

Formal grid:20 unchanged cases ×3 requested seeds ×2 conditions =120 records (60 each). Case-major/seed-minor order; within each consecutive pair alternate baseline→treatment and treatment→baseline to reduce one-sided order effects. Scheduling is determined before outcomes. Temporal provider variability remains a limitation.

G01/seed11 paired pilot uses a separate version and does not count toward the formal 120. If pilot findings require a protocol/prompt/code change, freeze a new version before formal runs. Do not tune after comparative outcomes, drop difficult cases or change scoring. G05/G08/G15 retain APM ceilings 90/66.67/80%. Baseline headroom is limited: parsed V3 outputs already reached APM ceilings and 100% RBM/HBM.

## Scoring, statistics and evidence

Reuse the frozen scorer without changes: APM credits matching unique valid activity IDs over 2×days; RBM uses matching restaurant slots over 2×days; HBM checks the single hotel budget; IFR checks structural/dataset rules only. Missing outputs receive zero output scores. Parsed structural failures keep component credit. RTC measures required-name coverage across agents from first-candidate model HTTP response function calls in the final attempt, with executed calls separate. An output may fail with RTC 100%.

Primary analysis includes every expected record, including provider/parse/coordination failures. Means and sampleSD(n−1) are reported separately across 60 runs,20 case means and 3 seed means, plus per-seed means and paired treatment−baseline differences. A pilot does not yield formal seed variation. Parsed-only quality, if added, is supplementary and labelled as such.

For each record, measure system wall time ONCE from workflow start through tool calls, serialization/logging and all attempts/waits. Report actual measured pacing waits, retry waits and residual processing time separately. Do not sum agent wall times. Setup/download/installation are outside this measure. Mock/fake-clock timings are not real latency measurements.

Sum observed HTTP response usage across every agent and retry; retain missing observations as unknown and report coverage. Currency cost starts null. Free-tier availability is not proof of zero billing. Actual paid cost, unknown billing and any later documented price estimate must remain distinct. Current official prices are checked only when preparing an approved run budget; no monetary estimate is invented from token counts.

Each version saves a manifest of source/data/policy/cases/dependency hashes. Each run saves request, append-only JSONL events, record and checksum. Resume checks identity, checksum, journal linkage and scores; interrupted folders block automatic reruns. Analysis refuses partial or extra cohort folders. Independent verification recomputes scores/RTC/usage/statistics without the main scorer. Checksums provide integrity, not independent provider authentication.

## Required final evidence, still pending

Real 120 records; comparative means/SD/seedmeans; actual measured system latency and observable usage/cost status; trace-supported failure analysis; updated `M6_Report.md`; saved outputs/errors/traces; reproducible ZIP and bilingual guide. Only the two-record live pilot is complete; no formal comparative or treatment-improvement claim is currently supported.
