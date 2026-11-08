# M6 — Riyadh Travel Planner

**Status, 8 November 2026:** implementation, offline validation and the live paired pilot are complete. A live paired G01/seed11 pilot completed with 2 records and 9 HTTP requests. Formal-v1 was attempted but its evidence is incomplete after runtime-storage loss. Only 12 raw records are durably recovered; the progress log reaches 114. The approved formal-v2 recovery used verified Drive storage, then stopped after five requests when the daily free-tier quota was exhausted. One complete baseline and one interrupted treatment journal are preserved. No complete formal comparison is reported. See reports/M6_Execution_Incident.md. Mock records are software fixtures, not research results. M6 submission is not complete until the approved live comparison and failure analysis are recorded.

Start with `docs/M6_Experiment_Protocol.md` and `M6_Team_Guide.html`. M5 remains unchanged in its separate repository. This M6 project contains only its runtime dependencies and new M6 work.

## What changed

`m6planner/` adds a three-role model workflow and a baseline runner using the same execution policy. `m6_tests/` tests the new behavior; `scripts/verify_m6.py` independently verifies saved evidence. The frozen scorer, search filters/ranking, M4 CSVs, twenty cases and seeds 11/22/33 are reused.

The independent private repository is `BashaierAwal/riyadh-travel-planner-m6-multi-agent`. Frozen shared components come from M5 commit `e59f1b49c0c6d7d695a885df6cf9fafe4113ab61`; their exact source/data hashes identify each run. The original M5 repository is separate and unchanged.

## Setup

Use Python 3.11 or 3.12. In an environment where installation has been authorized:

```sh
python -m pip install -r requirements.txt -r requirements-gemini.txt
```

The model SDK remains pinned to `google-genai==1.30.0`. No key is needed for tests, mock validation or saved-evidence analysis. The pinned dependencies are listed in requirements-gemini.txt.

## Offline checks

```sh
python -B -m unittest discover -s m6_tests -v
```

To reproduce all120mock records in a fresh version:

```sh
python -B -m m6planner mock-smoke --version validation-reproduction
python -B scripts/verify_m6.py m6_runs/validation-reproduction
python -B -m m6planner analyze m6_runs/validation-reproduction
```

This uses the real pinned SDK with `httpx.MockTransport`, a fake clock and a socket network guard. It makes zero live HTTP requests and does not model real cost, latency, or quality.

## Separately approved live execution

Open `notebooks/M6_Colab_Run.ipynb`. All installation/upload/live flags start false. Do not run archived M4/M5 notebooks. Use the existing Colab Secret `GEMINI_API_KEY`; never paste it into code, reports or chat.

The completed readiness step was a **paired pilot: G01/seed11, baseline + treatment**, at most2new records and60total HTTP requests. It is stored under a `pilot-` version and never substituted into the formal cohort. The code will not start another record unless30requests of approved session capacity remain. Unused capacity is not spent automatically.

After reviewing the pilot, a separately approved formal study uses all20cases ×3seeds ×2conditions =120records. A conservative session cap is6new records/180HTTP requests; actual requests may be fewer. Resume the SAME formal version without rerunning saved failures or completed records. Keep the environment/source/settings fixed. Download saved evidence after every chunk.

Terminal provider/budget/program errors stop the batch after saving the affected record. An incomplete folder after an interrupted process blocks automatic recovery: preserve its journal and inspect it before authorizing a separately versioned recovery. A changed source/data/configuration fingerprint blocks resume. A failed record is complete evidence, not an invitation to retry it later.

Full-cohort comparison refuses incomplete/extra records. `analysis/M6_Results.csv` and `analysis/M6_Comparison.json` contain all failures, three levels of variation, paired differences, observed usage, null monetary cost unless independently established, system latency and failure counts. These filenames inside `validation-*` remain mock artifacts.

## Files for delivery

- `m6planner/`: model workflow, shared policy, paired runner, analysis and mock service.
- `notebooks/M6_Colab_Run.ipynb`: safe default Colab entry point.
- `docs/M6_Experiment_Protocol.md`: frozen design and execution/measurement policy.
- `reports/M6_Report.md`: implementation report with formal comparative results explicitly pending.
- `M6_Team_Guide.html`: Arabic/English guide, opens locally without internet.
- `reports/M6_Verification.json`: executed verification checks and their scope.
- `m6_runs/`: separate validation/pilot/formal output versions. The original 120 mocked records remain in the validation archive; regenerate them with the command above.

The original 49 M5 tests and saved V3 verifier were executed against the preserved M5 source snapshot before this independent export. Their historical artifacts remain in the separate M5 repository/validation archive.

All historical M5 evidence and attribution are preserved. No merges, purchases or billing upgrades were performed. The approved pilot used the existing Colab Secret without exposing or copying its value outside Colab. See reports/M6_Pilot_Report.md.

## Pilot evidence storage

The two pilot records and their full request/response/tool journals are retained in the separate local M6_Pilot_Evidence.zip. Raw pilot traces are not uploaded to GitHub. Extract this evidence ZIP under m6_runs/ to audit pilot-v1 with scripts/verify_m6.py. Summary measurements are in reports/M6_Pilot_Report.md and reports/M6_Pilot_Audit.json.
