# M6 run storage and verification

Formal-v3 is the completed experiment. It contains 120 records from 20 cases and three requested seeds under each of the two conditions. The public repository contains the [comparison data](../reports/formal-v3/), the [report](../reports/M6_Report.md), and the [audit summary](../reports/M6_Formal_Audit.json).

## Verify the full saved experiment offline

Use the full formal-v3 evidence archive held by the project team. From the root of a checkout of this branch, place the extracted `formal-v3` directory under `m6_runs/`. The directory must contain `manifest.json`, 120 run folders with `record.json`, `record.sha256`, and `events.jsonl`, and `analysis/M6_Comparison.json`. The published comparison JSON can also be copied from `reports/formal-v3/` into that `analysis/` directory.

```sh
python3 scripts/verify_m6.py m6_runs/formal-v3
```

The verifier uses the Python standard library and requires no model credentials. A successful audit reports `PASS_SAVED_EVIDENCE`, 120 records, and `saved_comparison_verified: true`. It checks experiment identity, record hashes, journals and score arithmetic. The [audit summary](../reports/M6_Formal_Audit.json) separately records the tool-grounding exception. A GitHub-only checkout includes the published results, but full verification requires the archive.

## Other runs

The pilot and the incomplete formal-v1 and formal-v2 attempts are documented in the [execution incident report](../reports/M6_Execution_Incident.md). Formal-v3 alone supplies the primary results. Offline validation fixtures can be regenerated with `python3 -m m6planner mock-smoke --version validation-reproduction`. Their timings and token counts are fixture values.
