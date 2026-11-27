# Evaluation updates

This folder addresses the review of the M5 evaluation and prepares a revised M6 comparison. The approved CSVs and the original 20 cases are unchanged. The earlier baseline remains available with its original evidence.

Read [the revised protocol](PROTOCOL.md), [the case files](cases/), and [the rechecked original baseline](reports/M5_V3_RECHECK.md). The new checker evaluates distance, accommodation cost and competing interests using the existing data. It does not claim to check road travel times, bookings or current prices.

The original cases are in `cases/original.json`; the twenty extra cases are in `cases/hard.json`. `cases/all.json` combines them. The feasibility examples prove the added requests can be satisfied; they are not sent to the models.

## Check the software

The new extension uses Python 3.11 or later and the standard library. It does not require a model key for offline checks.

```bash
python -m unittest discover -s revision/tests -v
```

The original M5 audit and baseline recheck are available in the [M5 repository](https://github.com/BashaierAwal/riyadh-travel-planner-m5-final). The `analyze_saved` command is intended for that repository, which includes the original baseline archive.

## Run a separate pilot

Store the model credential in an environment variable or Colab Secrets. Never paste it into this repository or a notebook cell. Supply the exact available model ID and an explicit request cap. The following is an example command, not a claim that the model has been checked or that a run has completed:

```bash
python -m revision.run --study pilot --version pilot-v1 \
  --model gemini-3.5-flash-lite --max-requests 120 --max-new-records 2
```

The command makes live model requests. The pilot uses P00 only, separate from the held-out hard cases. Run `python -m revision.verify revision/runs/pilot-v1` to check its evidence. Pilot scores are not formal comparative results.

For the full study, choose `main`, `ablation`, `second_model`, `strong_coordinator` or `seed_check`. A second model needs `--second-model`; a different coordinator needs `--coordinator-model`. Each experiment has a separate version. Run records and manifests are saved under `revision/runs`, or in an explicit separate output directory such as persistent Drive storage. Completed records are never overwritten on resume.

After both grids are complete, compare a component-removal condition with the full team using `python -m revision.compare MAIN_FOLDER ABLATION_FOLDER without_feasibility` (or `without_repair`). Use the same command with the coordinator-only folder and `strong_coordinator`. The comparison refuses mismatched cases, data, models or shared policies. `python -m revision.cost RUN_FOLDER` exports per-case usage-based list-price estimates separately from actual billing.

## Current scope

The revised code and offline checks can be inspected before live execution. New experimental results must be backed by saved complete run records. Preparation, fixture checks, earlier M5 results and earlier M6 results must not be described as completed hard-case experiments.
