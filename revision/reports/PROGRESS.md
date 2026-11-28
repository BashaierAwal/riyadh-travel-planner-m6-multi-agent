# Current experiment progress

Updated 28 November 2026, 20:06 Riyadh. The revised comparison is incomplete. Counts below describe verified saved snapshots, including failed attempts.

## Main grid

The gemini-3.5-flash-lite grid has 103 of 240 saved records: 54 original-case records covering G01–G09, and 49 hard-case records. H01–H08 are complete with both systems and three requested seeds; H09 has one of six records. The full hard group requires 120 records, so no hard-case performance comparison is claimed.

The checkpoint contains 875 generation requests. Six attempts ended at the registered model-stage request limit, two with HTTP 503 service errors, and two with HTTP 429 daily model-quota errors. The latest quota stop was baseline H09, seed 11. The quota identifier was `GenerateRequestsPerDayPerProjectPerModel-FreeTier`. All failed records remain included and will not be replaced.

[Main 103-record evidence](../evidence/Riyadh_Review_Main_Checkpoint_103.tar.xz). Published archive SHA256: `940357e1df70aa5b3519e29015e79fe28c7f641702af5ebe5c42618ff5e243ce`. Its files match the downloaded ZIP exactly; ZIP SHA256: `d7ce673af0d7f4449370936bfce2d6c3444750b90fdfa611fee56bce5e2b9d87`.

## Second-model grid

The gemini-3.1-flash-lite checkpoint contains 79 of 240 records: 18 original-case records covering G01–G03, and 61 hard-case records. H01–H10 are complete; H11 has one of six records. This hard group also remains incomplete.

The checkpoint contains 670 generation requests. Twenty-nine attempts ended at the registered model-stage request limit. Twenty-one ended with provider-service errors: sixteen HTTP 503 responses, four connection or timeout failures, and one earlier HTTP 429 daily-quota response. The scheduled continuation stopped after its bounded temporary-error continuations were used. All failed attempts remain included.

[Second-model 79-record evidence](../evidence/Riyadh_Review_Second_Model_Checkpoint_79.tar.xz). Published archive SHA256: `a6408c049e0f6a017bff85cfbc759d55981bb6eac6fb1a85a67956f3cbf62c72`. Its files match the downloaded ZIP exactly; ZIP SHA256: `e752b595cf4873d47760bd4088a4c98fefec3379d07198017d9c700bce92ba80`.

## Verification

Both archives passed native exact verification in Colab with Python 3.13.18, including source and dataset checksums, record and journal integrity, scores and dataset-backed tool replay. No unfinished record existed when the snapshots were taken. The [main settings audit](MAIN_SETTINGS_CHECK_103.json) and [second-model settings audit](SECOND_MODEL_SETTINGS_CHECK_79.json) checked every saved generation request against its registered model, requested seed, temperature zero and 8,192-output-token ceiling. Requested settings do not prove provider seed determinism.

The second-model archive also passed the Mac replay check with the documented route-only 1e-12 km tolerance. The main archive has two additional cross-version text differences: Python 3.13 qualifies a missing-argument error with `Tools.`, while local Python 3.9 omits that prefix. The [explicit replay note](MAIN_REPLAY_NOTE_103.json) lists both occurrences. A separate local check with only those exact error-text mappings passed; raw journals were not rewritten. Scores and rule decisions matched exactly. The maximum route-number difference in each archive was 1.4211e-14 km. The unchanged Mac verifier alone does not pass the main archive, so that limitation remains visible. Native exact verification is the reference.

## Continuation and remaining work

The queued 28 November continuation ran after the daily quota reset. Main advanced from 54 to 103 records and second model from 61 to 79. The scheduled sequence finished at 11:03 UTC. Reconnecting the notebook later recovered the same runtime and saved source.

At 17:07 UTC (20:07 Riyadh), a new bounded second-model continuation was started after several hours without requests. It checks availability with separate synthetic text before starting an unstarted study case. This is an operational start receipt, not a claim that a new planning case has succeeded. Saved failed attempts are never retried. The main grid remains stopped at its daily model quota. Component-removal and coordinator-only grids remain pending.

All generation uses frozen source commit `797621176f2148d804d111437713a7c1c3d899b8`, approved data, cases, seeds, prompts, tools and limits. The [execution appendix](PRIORITY_EXECUTION.md) records the order: finish a started original case, then H01–H20, then remaining original cases. All forty inputs remain registered. Hard-group completion is an intermediate milestone, not a reduced study.

## Interpretation and full scope

The full 840-record Gemini study is retained: main 240, component removals 240, second model 240 and coordinator-only 120. No paid upgrade or provider switch was made. The deadline constraint has been removed.

These snapshots contain 182 of 840 planned study attempts (21.67%), including failures. This percentage measures saved experimental attempts, not overall submission readiness. Complete predefined groups are required before reporting paired estimates, confidence intervals and pass³. The remaining experiments, revised result tables, error analysis and final M6 report are still required.

The [role-tool audit](ROLE_TOOL_AUDIT_54.json) and [original-case coverage note](ORIGINAL_CASE_COVERAGE.md) remain diagnostics. They do not replace a complete comparison or establish the cause of a revised failure.
