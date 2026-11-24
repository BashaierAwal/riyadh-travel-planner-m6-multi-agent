# M6 supplementary LLM judge

**Status: prepared and tested offline; no live judge requests or judge results yet.**

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

## Offline preparation

From the repository root:

```sh
python3 evaluation/llm_judge/evaluate.py
python3 -B -m unittest discover -s evaluation/llm_judge -p 'test_*.py' -v
```

Preparation verifies source record checksums, all 120 case/seed/condition identities, and fingerprints the rubric, instructions, datasets, code and saved records. It makes no model calls and writes no results. Expected status: `PREPARED_NOT_EXECUTED`, eligible baseline 59 and treatment 55.

## Colab walkthrough

Open `M6_Judge_Evaluation.ipynb` in this folder. Its offline cells work without a key. A separate guarded live cell remains disabled. For a live run, confirm the model's availability, approved request cap and account quota/cost first. Model names are not silently substituted. Use the existing Colab secret `GEMINI_API_KEY`; never paste the key into a notebook or repository.

After that decision, the command structure is:

```sh
python3 evaluation/llm_judge/evaluate.py --run --approve-live --model MODEL_ID --max-requests 2 --version judge-v1
```

`MODEL_ID` is a placeholder, not an executable default. Start with a small reviewed pilot before committing the formal judge configuration; if the rubric or model changes, use a new version. A pilot should use a separate version directory and must not be pooled silently into formal results.

For the formal version, at most **114 total requests**, one per readable plan, excluding any separately approved pilot. Each invocation also has its own explicit cap. There are no automatic retries, including SDK retries; the runner stops on a judge error and records it. Interrupted/failed calls are retained and skipped on resume. Use the same version/configuration to continue untouched records. Changing the fingerprint/model blocks resume. Run only one process per version; avoid simultaneous Colab sessions. The script waits 12 seconds before every request; this is not a quota guarantee.

Outputs go only to `evaluation/llm_judge/runs/VERSION/`: locked manifest, saved requests, provider responses including available usage, validated grades/reasons, per-record status and summary. Save that directory to persistent storage after each small batch; a Colab runtime alone is temporary. Copy back the **same** version directory before resuming in a new runtime. Request caps are local to the persisted version; losing it must not lead to rerunning records blindly. No output contains the API key; unexpected exception text is not saved.

The raw generation evidence is unchanged. The judge evaluates final-plan quality, not whether every selected ID appeared in prior tool results. The already documented G05/seed11 grounding exception therefore remains a separate finding. Estimated judge cost is not an actual bill. Do not publish `runs/` as completed research until real execution, review and verification have occurred.

## Interpretation and checks

Before accepting live findings, inspect a small balanced sample of grades/reasons for both systems, especially repeated activities in G05/G08/G15. Record any human calibration actually performed; do not claim it in advance. One judge pass does not measure judge repeatability. A different judge model from the generator may reduce shared-model bias but does not remove it. Do not tune the rubric after seeing comparative results without declaring a new evaluation version.

Offline tests check case coverage/blinding, score validation, request caps, resume/configuration guards, failure counts and absence of automatic error retries using simulated responses. These tests are not evidence that a live judge is calibrated or that a particular model is currently available.
