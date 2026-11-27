# Hard case execution priority

The submission deadline is three days. The main model reached its daily free request quota after 54 saved records, so the revised execution queue prioritises the twenty new hard cases. All forty registered requests remain planned. No case, input, seed, model, score or per-record limit is changed.

An already-started original case finishes before the queue moves to H01–H20. The original conditions and seed order within each case remain unchanged, including the alternating order of the two systems. Completed records, including failures, are never retried or relabelled. Remaining untouched original cases stay queued after the hard group.

`scripts/Run_Review_Priority.py` uses the frozen generator and changes only the order in which case blocks are supplied to it. Before any hard-case model record, it writes `priority_execution_v1.json`, tied to the original manifest hash, a hash of the complete execution queue and a saved copy of the priority worker. A resumed job refuses a changed registration. The independent replay verifier checks this appendix as well as the original source, data and record hashes.

`scripts/Run_Review_Study_v5.py` supports `--target-group hard` or `--target-group all`. The hard target is 120 records for the two-condition grids and 60 for the coordinator-only grid. Its status distinguishes completion of this group from completion of the full registered grid. The original cases are not deleted from the manifest when a hard-group job finishes.

Four additional scheduling and controller tests use explicitly marked temporary fixtures. They check preservation of all planned units, unchanged within-case order, finishing an already-started case, retention of existing record bytes, refusal of a changed worker snapshot, distinct hard-group/full-grid completion and the cumulative request guard. These are software checks, not model-performance evidence.

Comparative results may be reported only for a complete prespecified group of cases and seeds. Hard-case results require all twenty H cases, all three seeds and both systems. Combined forty-case results require the complete full grid. A submission must identify any original-case repeats or extra experiment groups still pending at the deadline.
