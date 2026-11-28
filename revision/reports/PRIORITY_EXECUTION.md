# Hard case execution priority

The execution order was registered on 27 November 2026 while a three-day deadline was in place. The main model had reached its daily free request quota after 54 saved records, so the revised queue prioritised the twenty new hard cases. On 28 November the deadline constraint was removed and the full 840-run plan was explicitly retained. The registered queue remains unchanged. All forty registered requests remain planned. No case, input, seed, model, score or per-record limit is changed.

An already-started original case finishes before the queue moves to H01–H20. The original conditions and seed order within each case remain unchanged, including the alternating order of the two systems. Completed records, including failures, are never retried or relabelled. Remaining untouched original cases stay queued after the hard group.

`scripts/Run_Review_Priority.py` uses the frozen generator and changes only the order in which case blocks are supplied to it. Before any hard-case model record, it writes `priority_execution_v1.json`, tied to the original manifest hash, a hash of the complete execution queue and a saved copy of the priority worker. A resumed job refuses a changed registration. The independent replay verifier checks this appendix as well as the original source, data and record hashes.

`scripts/Run_Review_Study_v5.py` supports `--target-group hard` or `--target-group all`. The hard target is 120 records for the two-condition grids and 60 for the coordinator-only grid. Its status distinguishes completion of this group from completion of the full registered grid. The original cases are not deleted from the manifest when a hard-group job finishes.

Four additional scheduling and controller tests use explicitly marked temporary fixtures. They check preservation of all planned units, unchanged within-case order, finishing an already-started case, retention of existing record bytes, refusal of a changed worker snapshot, distinct hard-group/full-grid completion and the cumulative request guard. These are software checks, not model-performance evidence.

Comparative results may be reported only for a complete prespecified group of cases and seeds. Hard-case results require all twenty H cases, all three seeds and both systems. Combined forty-case results require the complete full grid. A submission must identify any original-case repeats or extra experiment groups still pending at the deadline.

## Complete-group reports

`scripts/Report_Study_Group.py` verifies saved evidence before reporting a predefined group. `--group hard` requires all twenty unchanged H cases, seeds 11, 22 and 33, and every registered condition. `--group original` applies the same rule to G01–G20. Missing or duplicate cells stop report creation. The output states both group completion and full-grid completion, keeps every failed attempt, and includes paired case-level estimates, pass³, execution-error counts, per-case cost estimates and elapsed time with and without scheduled pacing.

Component-removal and coordinator comparisons additionally require a matching complete group in the main grid. They refuse changes to shared cases, source, data, models or generation settings. Three reporting tests passed in both project copies using explicitly synthetic evidence. The current incomplete live snapshot was also refused for hard-group reporting. No comparative hard-case result has been produced.

## Bounded service-error continuation

A separate supervisor, `scripts/Continue_Review_Study.py`, was added after the first two hard-case attempts because temporary service failures repeatedly stopped batches. It waits for an existing controller to finish, then waits five minutes before continuing only unstarted records after connection errors, timeouts or HTTP 408/500/502/503/504. It allows at most four such continuations per invocation. It stops on HTTP 429, authentication errors, inspection failures, the session request cap or group completion. It never retries a saved attempt, changes its outcome, alters a generation setting or changes the case queue. The original controller remains pinned by its SHA256 hash.

Its source copy, hashed policy, timestamped status and log are saved alongside the experiment folders. Three synthetic supervisor tests passed in each project copy, checking saved-record preservation, bounded cooldowns, waiting for an existing controller, and immediate stops for quota, access or inspection problems. These logistical checks are not new model results.
