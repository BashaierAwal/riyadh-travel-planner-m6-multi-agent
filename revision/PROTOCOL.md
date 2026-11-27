# Revised evaluation protocol

## Purpose

The original tests often give full marks for budget matching and tool coverage. This extension tests whether checking and repairing a whole plan helps when requirements compete. It preserves the approved data, original cases and original scores.

## What stays unchanged

The three M4 CSV files, their IDs and values stay unchanged. G01–G20 keep their exact inputs. The original M5 scorer still calculates APM, RBM, HBM and structural IFR. RTC remains a separate measure of search-tool coverage. The original V3 baseline has 60 saved records; its results remain the M5 baseline. V2 is history, not evidence for the final comparison.

## What is added

H01–H20 are twenty new requests, each with two interests, a daily distance limit and a total hotel-cost cap. They use the same three CSVs. Both interests compete for the two activity slots per day. Each interest must occupy at least one slot per requested day, counted over the full trip using distinct activities.

Each case has a checked example proving that its rules can be met. These examples support case design. They are not the only correct answers and are never supplied to the planning models. The published case files are frozen before any model response to the new cases is examined. Prompts must not be tuned on H01–H20. P00 is a separate development case for checking the connection and output format.

Daily distance is the sum of great-circle distances along this fixed sequence: hotel → first activity → first restaurant → second activity → second restaurant → hotel. It is a straight-line distance measure, not a road route or journey-time estimate. Only recorded finite coordinates are used; a missing coordinate prevents a distance pass. Coordinates are not filled in or guessed.

Coordinate coverage is 1,125/1,125 activities, 19,345/19,345 restaurants and 23/55 hotels. For H01–H20, the shared searches return places with recorded coordinates, so the route rules are checkable. For G01–G20, which have no route limit, hotels without coordinates remain eligible. This is a search rule for the new requests, not a modification of the approved CSVs.

Hotel cost is the recorded median price multiplied by the explicit number of nights. Nights are `max(1, trip_duration − 1)`: even a one-day request explicitly includes one night. The hotel cap covers accommodation only. It excludes food, activities, flights and transport. These are historical dataset prices, not current quotes.

## Fair comparison

Both systems receive the same request, datasets, candidate fields, search ranking, checking tool, model, temperature, requested seed, output rules, maximum repair rounds and overall request cap. The revised search tools return coordinates and allow results to be ranked near a known place. These tools are shared by both systems. They do not alter the CSVs.

Because the prompts, tools and repair policy change, the original V3 runs cannot be substituted for the new matched baseline. The revised comparison runs both systems again under the shared policy. Original V3 and earlier M6 results remain separate historical evidence.

The single agent handles the complete plan and its repairs. The team uses three roles: coordinator, activity specialist, and feasibility and budget specialist. The coordinator delegates; the activity specialist suggests activities; the feasibility specialist prepares and checks a full draft; the coordinator returns a full plan. Both systems then receive the same deterministic checker findings. In the team, the feasibility specialist reviews the findings before the coordinator repairs the plan.

The checker never changes a plan. It records problems. Only a model may propose a repair. At most three repair rounds are allowed. Stop earlier when all registered checks and search grounding pass. An unreadable output or failed required stage remains a failure; an intermediate draft is never substituted for a final answer.

## Measurements

Keep APM, RBM, HBM, structural IFR and RTC with their stated meanings. Add the number of broken rules per final plan, complete-constraint success, repair rounds, executed tool calls, HTTP requests, tokens and system latency. Complete-constraint success also requires each selected ID to have appeared in a successful search result. Structural IFR alone does not certify distance or hotel-cost limits.

The broken-rule count is the number of entries in the checker's violation list. It includes each failed structural rule, each daily route over its limit, a hotel-cost or hotel-category failure, each mismatching restaurant slot, and each unmet interest quota. An unreadable output receives a no-output violation and fails complete-constraint success. Report no-output failures separately so they cannot appear better merely because no route could be measured. Report both violation count and complete-constraint success.

Save every initial and repaired plan, problems found, problems fixed, newly introduced problems and tool calls. Save model requests and responses, model-version metadata when returned, usage metadata, errors and timing. Never save authentication headers or keys.

## Runs and component-removal checks

The main comparison uses 40 cases × 3 requested seeds × 2 systems = 240 records. Report G01–G20 and H01–H20 separately; a combined table is supplementary. The hard-case complete-constraint success rate is the primary outcome. The original four metrics remain visible.

Use the same cases and seeds for two team variants: remove the feasibility specialist, then remove the repair loop. Compare each variant with the full revised team from the main comparison. In the first variant, the coordinator handles feasibility with the same tools; tools are not removed along with the role. In the second variant, keep the initial team workflow but allow no repair rounds. These experiments explain which design choice may account for the result. They do not assume the team wins.

Run both systems with an explicitly selected second model. Separately, keep the specialist model fixed and change only the coordinator model to a higher-capacity model. Do not silently replace unavailable model IDs. Model choice and availability must be recorded before each experiment.

Repeat one original case twice with the same model and seed 11 in a separate seed check. Compare the readable plans and recorded outputs. Matching this pair is limited evidence; it does not prove deterministic behavior for every case. Two missing outputs cannot verify a seed.

## Statistics

Report mean and sample SD of the three seed means for each condition, as well as across-run SD. For binary success, report pass³: the share of cases where all three runs pass. Seeds are requested repeated-run labels until their effect is checked.

Compare conditions using the mean of the three paired differences within each case. Resample cases, keeping their seeds together, for a 95% percentile bootstrap interval with 20,000 draws. Use a two-sided paired sign-flip test on case means: exact for at most 16 cases, otherwise 20,000 random sign assignments with a plus-one correction. The analysis random seed is 683. Do not treat 120 repeated runs as 120 independent travel requests. Secondary outcomes and component-removal comparisons are exploratory; report uncertainty and avoid a blanket superiority claim.

## Failure analysis

Retain all failed records. Label problems as no output, unknown dataset place, repeated activity, budget, distance, preference, structure, missing information or missing search grounding. Keep every applicable label. For a single count per failed plan, use that priority order and state it. Show a real saved example of each main label for each system. A label describes the observed problem; use the component-removal results before presenting a design choice as its cause.

## Execution and recovery

Temperature is zero. Each request has an 8,192-output-token ceiling, including thinking tokens when counted by the provider. Each stage has at most 12 HTTP requests; each record has at most 60. Use at least 12 seconds between HTTP request starts and a 60-second request timeout. Both systems use the same ceilings. There are no hidden provider retries. On a service or request-budget error, preserve the failed record and stop the batch. Do not delete and retry a failed completed record to obtain a better result. An interrupted folder needs inspection before a separately documented recovery.

The session has an explicit HTTP cap and maximum number of new records. The source, datasets, cases, model settings and ordering are fingerprinted. The run writes and flushes each event immediately. Resume checks identity, record hashes, journal hashes and scores. Formal analysis refuses an incomplete grid. Fixture runs test software and must never appear as model-performance results.

## Costs and data sources

Sum observed provider usage, retaining missing values as unknown. Estimate cost only using a dated official price for the exact model, including billable thinking tokens when applicable. Separate a list-price estimate from actual billing. Do not call free-tier usage an actual zero bill without billing evidence. Dataset source and licence checks are documented separately; no licence is invented when a source lists it as unknown.

## Selected models

Metadata access was checked on 27 November 2026 for gemini-3.5-flash-lite, gemini-3.1-flash-lite and gemini-3-flash-preview. All three advertised generateContent support. The main comparison uses gemini-3.5-flash-lite; the second-model comparison uses gemini-3.1-flash-lite. The coordinator-only variant uses gemini-3-flash-preview, a Flash-family alternative to the Lite specialist model. Its performance advantage is a question for the experiment, not an assumed result. These models list a free tier, but account quotas and actual billing are not established by a model metadata response. No paid upgrade is part of this work.

## Related design

Choi, Yoon, Chen, Jha and Pfister describe constraint management and repeated plan critique in [ATLAS Constraints-Aware Multi-Agent Collaboration for Real-World Travel Planning](https://proceedings.iclr.cc/paper_files/paper/2026/hash/6c78ae0c1140902bf3a430b1725bcc4e-Abstract-Conference.html), ICLR 2026. Their work motivates giving the feasibility role explicit checking work. This study evaluates a bounded local-data workflow and reports its own results.

The repair-round metric counts the outer complete-plan/check/revision cycles managed by the controller. Tool calls made while a model prepares a draft, including check_plan calls, are recorded separately and are bounded by the per-stage and per-record HTTP ceilings. The three-round limit is not a count of a model’s internal reasoning steps.

## Dated execution-order appendix

For the three-day submission deadline, a separately hashed execution appendix prioritises H01–H20 before untouched original cases, after finishing an already-started original case. It preserves all requests, seeds, models and within-case condition order. Registration is required before any hard-case model record. The original manifest remains intact; `priority_execution_v1.json` and its saved worker specify the added case-block priority. All failures remain included, and original-case reruns stay planned. Each reported prespecified group must have its complete case/seed/condition grid; an incomplete overall forty-case grid cannot support a combined result.
