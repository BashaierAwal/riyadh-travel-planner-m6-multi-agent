**Updated 9 November 2026: formal-v3 completed and verified — 120 live records, 484 HTTP requests. See reports/M6_Report.md for the completed comparison. Earlier incomplete versions are preserved separately.**

# M6 — Riyadh Travel Planner

The paired pilot finished on 8 November. The first two formal attempts stopped before a complete cohort was saved. Their recovered evidence is documented in the [execution incident report](reports/M6_Execution_Incident.md). Formal-v3 completed on 9 November and is the source of the [reported comparison](reports/M6_Report.md).

Start with `docs/M6_Experiment_Protocol.md` and `M6_Team_Guide.html`. M5 remains unchanged in its separate repository. This M6 project contains only its runtime dependencies and new M6 work.

## What changed

`m6planner/` adds a three-role model workflow and a baseline runner using the same execution policy. `m6_tests/` tests the new behavior; `scripts/verify_m6.py` independently verifies saved evidence. The frozen scorer, search filters/ranking, M4 CSVs, twenty cases and seeds 11/22/33 are reused.

The public M6 repository is `BashaierAwal/riyadh-travel-planner-m6-multi-agent`. Frozen shared components come from M5 commit `e59f1b49c0c6d7d695a885df6cf9fafe4113ab61`; their exact source/data hashes identify each run. The original M5 repository is separate and unchanged.

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

The completed formal-v3 study used 20 cases × 3 seeds × 2 conditions, yielding 120 records. The original operating procedure used the following limits. A conservative session cap is6new records/180HTTP requests; actual requests may be fewer. Resume the SAME formal version without rerunning saved failures or completed records. Keep the environment/source/settings fixed. Download saved evidence after every chunk.

Terminal provider/budget/program errors stop the batch after saving the affected record. An incomplete folder after an interrupted process blocks automatic recovery: preserve its journal and inspect it before authorizing a separately versioned recovery. A changed source/data/configuration fingerprint blocks resume. A failed record is complete evidence, not an invitation to retry it later.

Full-cohort comparison refuses incomplete/extra records. `analysis/M6_Results.csv` and `analysis/M6_Comparison.json` contain all failures, three levels of variation, paired differences, observed usage, null monetary cost unless independently established, system latency and failure counts. These filenames inside `validation-*` remain mock artifacts.

## Files for delivery

- `m6planner/`: model workflow, shared policy, paired runner, analysis and mock service.
- `notebooks/M6_Colab_Run.ipynb`: safe default Colab entry point.
- `docs/M6_Experiment_Protocol.md`: frozen design and execution/measurement policy.
- `reports/M6_Report.md`: implementation report with completed formal-v3 comparative results.
- `M6_Team_Guide.html`: Arabic/English guide, opens locally without internet.
- `reports/M6_Verification.json`: executed verification checks and their scope.
- `m6_runs/`: separate validation/pilot/formal output versions. The original 120 mocked records remain in the validation archive; regenerate them with the command above.

The original 49 M5 tests and saved V3 verifier were executed against the preserved M5 source snapshot before this independent export. Their historical artifacts remain in the separate M5 repository/validation archive.

All historical M5 evidence and attribution are preserved. No merges, purchases or billing upgrades were performed. The approved pilot used the existing Colab Secret without exposing or copying its value outside Colab. See reports/M6_Pilot_Report.md.

## Saved evidence and verification

See [run storage and verification](m6_runs/README.md) for the formal-v3 archive layout and offline audit command. The two pilot records remain in the separate pilot evidence archive. Pilot measurements are in the [pilot report](reports/M6_Pilot_Report.md).
