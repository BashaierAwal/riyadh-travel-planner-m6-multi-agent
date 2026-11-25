# M6 supplementary itinerary assessment

The live judge evaluation completed on 25 November 2026. It assessed all 114 readable plans from the saved M6 formal-v3 experiment: 59 single-agent baseline plans and 55 three-agent plans. All 120 original records remain accounted for. The six generation failures have no judge grade and are reported separately.

## Main finding

The mean judge score was **4.496/5 for the baseline** and **4.532/5 for the three-agent system**. The unpaired difference is 0.036 points on a five-point scale. Among the 54 case/seed pairs with two readable plans, the mean treatment-minus-baseline difference was **+0.032/5**, with sample SD 0.354. These are small descriptive differences, not evidence of statistical significance or overall superiority.

The results add a quality judgement to the original M6 measurements. They do not replace the original finding that the treatment had more generation failures, lower average automated scores, and greater latency and token use. A slightly higher conditional judge mean can coexist with worse all-run reliability because the failed plans are absent from that quality mean.

## Method

The evaluator was `gemini-3.1-flash-lite`, using the pinned `google-genai==1.30.0` SDK, temperature 0, a 1,600-token output ceiling and JSON responses. This differs from the planning model, `gemini-3.5-flash-lite`. There was one accepted judgement per readable plan; judge repeatability was not measured.

Both conditions used the same locked [rubric](rubric.json), instructions and model configuration. Four equally weighted integer scores, 1–5, cover personalization, budget alignment, itinerary coherence and evidence-supported feasibility. Every criterion has a saved reason. Overall quality is the arithmetic mean of those four scores.

Each request contained the user requirements, the saved final itinerary and selected-place evidence from the unchanged datasets. Explicit architecture labels, run IDs, original generation seeds, prior scores and internal agent discussions were withheld. A deterministic mixed order was used. This masks explicit labels but cannot rule out indirect architectural clues. Dataset coordinates were available; opening hours, route times, bookings and total monetary travel budgets were not verified.

No plan was regenerated or repaired. No rubric was tuned after the comparative results. The historical M5 judge average of 4.522/5 is not the matched baseline for this study; the M6 rubric is separately versioned.

## Results

| Criterion (1–5) | Single-agent baseline (n=59) | Three-agent system (n=55) |
|---|---:|---:|
| Personalization | 4.136 | 4.255 |
| Budget alignment | 5.000 | 5.000 |
| Itinerary coherence | 4.322 | 4.400 |
| Itinerary feasibility | 4.525 | 4.473 |
| Overall mean | **4.496** | **4.532** |
| Overall sample SD | 0.538 | 0.605 |

| Coverage | Baseline | Three-agent |
|---|---:|---:|
| Original generation records | 60 | 60 |
| Readable plans / judged plans | 59 / 59 | 55 / 55 |
| Generation failures retained separately | 1 | 5 |
| Unresolved judge failures | 0 | 0 |

The baseline generation failure is G07/seed22. The treatment failures are G06/G11/G15/G18/G19, all at seed33. These are the original M6 failures, not additional failures caused by the judge. Generation success was therefore 59/60 and 55/60, respectively.

The [120-row results table](JUDGE_RESULTS.csv) includes the failed generations with blank judge grades. Full-precision means, paired results and conditional means grouped by the original generation seed are in [JUDGE_ANALYSIS.json](JUDGE_ANALYSIS.json) and [the saved summary](runs/judge-formal-v2/summary.json). Judge scores are not converted to percentages or averaged with the five original metrics.

## What the reasons reveal

The judge often identified repeated activities, particularly in G08 and G15, and reduced coherence or feasibility scores. Its assessments were not fully consistent. For example, baseline G05/seed11, seed22 and seed33 received coherence 3 and feasibility 4 despite repeated activities. Treatment G05/seed22 received coherence 2 but feasibility 4, with a feasibility explanation describing the plan as structurally valid even though the unchanged deterministic checker rejected it. These saved grades and reasons are retained rather than corrected or rerun.

This illustrates why the judge complements the deterministic checks. A high judge score does not override an IFR failure. Both conditions also received budget alignment 5 throughout the judged subset, so that criterion provided no separation between the architectures.

The judge assessed final-plan quality, not whether all chosen places appeared in preceding tool results. The original treatment G05/seed11 tool-grounding exception remains reported in the main M6 report; it is not resolved by a judge score.

## Execution history and resource limits

The short preliminary attempt, `judge-formal-v1`, stopped after one accepted judgement and one observed HTTP 503 failure. Its two requests and saved partial evidence remain separate. Its grade is not pooled into the formal comparison.

The fresh primary evaluation, `judge-formal-v2`, kept the same rubric, input preparation and model settings. Before this run, its recorded execution policy allowed up to three attempts per plan for HTTP 500/502/503/504 only, with 12-second waits before retries. Non-transient errors were not retried. The formal ceiling was 126 HTTP requests, with a combined preliminary-plus-formal ceiling of 128. The SDK itself used one attempt per call.

The formal evaluation used **121 HTTP requests**: 114 accepted responses and seven recorded transient failures (six 504s and one 503), all recovered within the stated policy. Including the preliminary two requests, usage was **123 requests**, below the combined ceiling. These are judge requests, separate from the original M6 planning experiment's 484 requests. Source snapshots, policy, execution context, saved requests, provider responses and per-attempt receipts are included under [runs/judge-formal-v2](runs/judge-formal-v2/).

The successful formal responses reported 176,093 prompt tokens and 26,883 candidate tokens, or 202,976 total observed tokens. This does not account for any unreported usage in failed requests and is not a billing receipt. Actual monetary cost is unknown. No purchase, upgrade or model substitution was performed.

## Verification and limits

[The saved-evidence audit](JUDGE_AUDIT.json) reports `PASS_SAVED_JUDGE_EVIDENCE`. The offline verifier checked all 120 identities, source/rubric snapshots and fingerprints, exact prepared prompts and dataset evidence, saved-response/grade agreement, score ranges, HTTP receipts and caps, and independently recomputed the condition means and paired differences. The original M6 saved-evidence audit also still passes. These are integrity and arithmetic checks, not independent provider authentication or proof that the judge's reasoning is correct.

There was no claimed human calibration, and a single model pass does not establish judge reliability. The available dataset limits what can be assessed. Conditional quality excludes unreadable generations and may favour the system with more failures; the 54-pair comparison also conditions on both plans being readable. No significance test or universal architectural ranking is claimed.

The appropriate conclusion is that the readable plans received similarly high judge scores, while the original automated evaluation and resource measurements remain necessary to explain the reliability and cost of the two architectures.
