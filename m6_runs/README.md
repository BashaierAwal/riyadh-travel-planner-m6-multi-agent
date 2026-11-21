# M6 run storage and verification

Formal-v3 is the completed experiment. It contains 120 records from 20 cases and three requested seeds under each of the two conditions. The public repository contains the [comparison data](../reports/formal-v3/), the [report](../reports/M6_Report.md), and the [audit summary](../reports/M6_Formal_Audit.json).

## Verify the full saved experiment offline

The full formal-v3 directory is included in this branch: manifest.json, 120 run folders with requests, records, checksums and tool journals, and the saved analysis. Download or clone this branch, then run from the repository root:

```sh
python3 scripts/verify_m6.py m6_runs/formal-v3
```

The verifier uses the Python standard library and requires no model credentials. A successful audit reports `PASS_SAVED_EVIDENCE`, 120 records, and `saved_comparison_verified: true`. It checks experiment identity, record hashes, journals and score arithmetic. The [audit summary](../reports/M6_Formal_Audit.json) separately records the tool-grounding exception. A checkout of this branch contains everything needed for this formal-v3 audit. No live model calls are made.

## Other runs

The pilot and the incomplete formal-v1 and formal-v2 attempts are documented in the [execution incident report](../reports/M6_Execution_Incident.md). Formal-v3 alone supplies the primary results. Offline validation fixtures can be regenerated with `python3 -m m6planner mock-smoke --version validation-reproduction`. Their timings and token counts are fixture values.
