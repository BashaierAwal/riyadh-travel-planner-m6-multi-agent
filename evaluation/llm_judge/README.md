# M6 supplementary LLM judge

**Status: live evaluation complete and verified, 25 November 2026.** All 114 readable formal-v3 plans were judged: 59 baseline and 55 three-agent plans. The six original generation failures remain separate. Start with [JUDGE_REPORT.md](JUDGE_REPORT.md), [the results table](JUDGE_RESULTS.csv), and [JUDGE_AUDIT.json](JUDGE_AUDIT.json).

This is a separate evaluation of the saved formal-v3 itineraries. It does not change the planner, prompts, datasets, original scores or original experiment records. The main comparison remains in `reports/M6_Report.md`.

## Purpose

The existing APM/RBM/HBM/IFR/RTC measures check specific properties reproducibly. A judge adds reasons about personalization, budget alignment, itinerary coherence and evidence-supported feasibility. It can help explain weaknesses that a single percentage conceals. It is a fallible supplementary measurement, not proof of real-world travel feasibility or a replacement for deterministic checks.

The course's Module 6 distinguishes outcome, trajectory and judge evaluation; Module 7 discusses judge-based evaluation and judge bias. This addition combines outcome judgement with the existing automated checks and preserved traces. The instructor's exact reason should not be inferred beyond her feedback.

## Fair comparison

- Evaluate the **new M6 baseline and treatment**, not the historical M5 baseline. Use the same judge model, locked rubric, temperature 0 and output limit for both.
- All 120 records are tracked: **59 baseline plans and 55 treatment plans** are readable and eligible. The other **one baseline and five treatment failures** remain reported separately; no invented judge grades or repaired plans.
- The judge sees the user request, final plan and selected-place dataset evidence. It sees no architecture label, run ID, seed, original score or internal agent discussion. Requests use a deterministic mixed order. This masks explicit labels; stylistic clues could still reveal the architecture.
- Four equal-weight scores, 1–5, each with a reason. Repeated activities must be penalized consistently; restaurant repetition is allowed. Unknown opening hours, bookings, travel times and complete trip costs must remain unknown.
- Report quality means and sample SD with eligible/judged/error counts, plus paired differences only where **both** plans were judged. Conditional quality and generation reliability are different measurements. Complete-readable-pair analysis is subject to selection bias.
- Historical M5 judge **4.522/5 is not a matched comparator**. This rubric is explicitly versioned for M6; do not claim rubric identity or direct score comparability with M5.

## Verify the completed evaluation offline

From the repository root:

```sh
python3 evaluation/llm_judge/verify_results.py evaluation/llm_judge/runs/judge-formal-v2
```

Expected: `PASS_SAVED_JUDGE_EVIDENCE`, 120 original records, 114 judgements, 121 formal HTTP requests and seven recovered provider errors. No model key or live request is needed. Raw evidence is included under `runs/judge-formal-v2/`; the separate short preliminary attempt is under `runs/judge-formal-v1/`.

## Offline input preparation

From the repository root:

```sh
python3 evaluation/llm_judge/evaluate.py
python3 -B -m unittest discover -s evaluation/llm_judge -p 'test_*.py' -v
```

This command reports `PREPARED_NOT_EXECUTED` because preparation itself makes no live calls; it does not describe the status of the completed saved evaluation. Preparation verifies source record checksums, all 120 case/seed/condition identities, and fingerprints the rubric, instructions, datasets, code and saved records. It makes no model calls and writes no results. Expected status: `PREPARED_NOT_EXECUTED`, eligible baseline 59 and treatment 55.

## Colab walkthrough and any future run

Open `M6_Judge_Evaluation.ipynb` in this folder. Its offline cells read and verify the completed evidence without a key. A separate optional live cell remains disabled; do not rerun the completed evaluation merely to view its results. For a live run, confirm the model's availability, approved request cap and account quota/cost first. Model names are not silently substituted. Use the existing Colab secret `GEMINI_API_KEY`; never paste the key into a notebook or repository.

After that decision, the command structure is:

```sh
python3 evaluation/llm_judge/evaluate.py --run --approve-live --model MODEL_ID --max-requests 2 --version judge-v1
```

`MODEL_ID` is a placeholder, not an executable default. Start with a small reviewed pilot before committing the formal judge configuration; if the rubric or model changes, use a new version. A pilot should use a separate version directory and must not be pooled silently into formal results.

The generic CLI has at most **114 model calls**, one per readable plan, excluding any separately approved pilot. Each invocation also has its own explicit cap. This generic CLI has no automatic retries, including SDK retries; it stops on a judge error and records it. The actual completed evaluation used the separately recorded bounded service-recovery driver described below. Interrupted/failed calls are retained and skipped on resume. Use the same version/configuration to continue untouched records. Changing the fingerprint/model blocks resume. Run only one process per version; avoid simultaneous Colab sessions. The script waits 12 seconds before every request; this is not a quota guarantee.

Outputs go only to `evaluation/llm_judge/runs/VERSION/`: locked manifest, saved requests, provider responses including available usage, validated grades/reasons, per-record status and summary. Save that directory to persistent storage after each small batch; a Colab runtime alone is temporary. Copy back the **same** version directory before resuming in a new runtime. Request caps are local to the persisted version; losing it must not lead to rerunning records blindly. No output contains the API key; unexpected exception text is not saved.

The raw generation evidence is unchanged. The judge evaluates final-plan quality, not whether every selected ID appeared in prior tool results. The already documented G05/seed11 grounding exception therefore remains a separate finding. Estimated judge cost is not an actual bill. The completed saved evidence in `runs/judge-formal-v2/` passed the offline verification above. Do not label any future run complete before checking its evidence.

## Interpretation and checks

Before accepting live findings, inspect a small balanced sample of grades/reasons for both systems, especially repeated activities in G05/G08/G15. Record any human calibration actually performed; do not claim it in advance. One judge pass does not measure judge repeatability. A different judge model from the generator may reduce shared-model bias but does not remove it. Do not tune the rubric after seeing comparative results without declaring a new evaluation version.

Offline tests check case coverage/blinding, score validation, request caps, resume/configuration guards, failure counts and absence of automatic error retries using simulated responses. These tests are not evidence that a live judge is calibrated or that a particular model is currently available.

## Actual completed execution policy

The short preliminary attempt stopped after one grade and one observed 503 failure; its two requests are excluded from the primary quality results. A fresh formal judge version kept the same rubric and model but added a recorded provider-recovery policy before bulk execution: at most three attempts per plan for 500/502/503/504, 12-second retry spacing, a 126-request formal cap and 128 including the preliminary attempt. It used 121 formal requests, or 123 combined. All 114 formal grades are present, with no unresolved judge failures.

The exact Colab execution driver is preserved at `runs/judge-formal-v2/execution_driver.py`, together with its execution context, policy, source snapshots and per-attempt receipts. This archived driver references Colab setup variables; it is a provenance snapshot, not an automatic replay command. The standard CLI above does not silently acquire its retry policy. Any new live reproduction needs a fresh version, explicit request budget and checked persistent storage. Model determinism and future availability are not guaranteed.
