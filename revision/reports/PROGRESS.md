# Current experiment progress

Updated 28 November 2026. The revised comparison is incomplete.

## Main grid

The main gemini-3.5-flash-lite grid has 54 of 240 saved records. These cover G01–G09 with both systems and all three requested seeds. No formal H01–H20 result is claimed.

Five records ended at the registered model-stage request limit. A further record, treatment G09 with seed 33, ended at coordinator dispatch when the provider returned HTTP 429. Its quota identifier was `GenerateRequestsPerDayPerProjectPerModel-FreeTier`. All six error records remain in the grid and will not be replaced. A model-stage limit and a provider quota are different failure categories.

The snapshot contains 405 generation requests. This excludes earlier pilots, the earlier partial main grid and the controller's conservative reservation for its interrupted record. Checksums, journal integrity, rescoring and dataset-backed tool replay passed both in Colab and locally.

[Saved 54-record evidence](../evidence/Riyadh_Review_Checkpoint_54.zip). Archive SHA256: `52e731b204dee9f640e0ba7df4f81b765e21f0f4b2152b7789052e307c4b942a`.

## Remaining execution

The main grid waits for its daily model quota to reset. The registered second-model grid has started with gemini-3.1-flash-lite; its model access and successful generation responses were checked. It uses the frozen cases, seeds, prompts, tools and limits. This changes the order of independent grids, without selecting a model from observed hard-case performance. Component-removal and coordinator-only grids remain pending.

The [priority controller](../../scripts/Run_Review_Study_v5.py) can select a registered stage and a hard-group or full-grid target. The [execution appendix](PRIORITY_EXECUTION.md) describes the registered order and complete-group reporting guard. It retains failed records and stops on service or session-resource errors. Source commit `797621176f2148d804d111437713a7c1c3d899b8`, generation settings and approved data remain fixed. No paid upgrade was made.

## Checking role and interpretation

The [role-tool audit](ROLE_TOOL_AUDIT_54.json) counts executed feasibility-stage calls to check_plan, excluding global controller checks. The [activity coverage note](ORIGINAL_CASE_COVERAGE.md) explains the unchanged original-data limits. Neither diagnostic replaces a complete comparison. Paired estimates, intervals and pass³ for revised model performance require a complete predefined group; combined forty-case results require the full grid.

## Second-model saved checkpoint

The locally verified checkpoint contains 61 of 240 records and 490 generation requests. G01–G03 and H01–H07 each have both conditions and all three requested seeds; H08 has one of its six planned records. The hard group has 43 of 120 required records and remains incomplete.

Twenty-one attempts ended at the registered model-stage request limit. Sixteen ended with provider-service errors: thirteen HTTP 503 responses, two connection or timeout failures and one HTTP 429 daily-quota response. All these attempts remain included. Source, data, record and journal checks passed in Colab and locally. The maximum route-only replay difference on the Mac was 7.106e-15 km; scores and rule decisions matched exactly.

The [request-configuration audit](MODEL_SETTINGS_CHECK_61.json) checked all 490 saved generation requests. Both systems and every serial role requested gemini-3.1-flash-lite, the recorded seed, temperature zero and the registered 8,192-output-token ceiling. This confirms requested settings, not that the provider produces deterministic outputs.

The priority appendix was registered before any hard-case model output. It finished G03 before H01. The snapshot includes the bounded continuation supervisors, controller, policies and separate synthetic service-readiness traces. These diagnostic requests are not scored or counted in the 490 study requests. Saved failed attempts are never retried or replaced.

[Second-model 61-record evidence](../evidence/Riyadh_Review_Second_Model_Checkpoint_61.zip). Archive SHA256: `376f85e16cae1931ce44de7d582b325c30ca84adfbcf616ca8ea6404ff969c2a`.

## Recovery and next continuation

After the daily-quota stop, Colab disconnected. A fresh runtime was connected on 28 November, restored at the same frozen source commit and Python 3.13.18, and audited both saved grids. All 54 main and 61 second-model records passed the native exact replay; neither grid had an unfinished record.

A background launcher was verified running at 07:17 UTC. It waits until 08:00:30 UTC (11:00:30 AM Riyadh) on 28 November, then invokes the unchanged readiness supervisor for the main grid and second-model grid in sequence. Each invocation checks service availability before starting an unstarted case. This is a queued continuation, not evidence that Google has reset the quota or that a new attempt has finished. It depends on Colab keeping the runtime connected. The full 840-record plan remains unchanged.

## Scope confirmed on 28 November

The full 840-record Gemini study is retained: main 240, component removals 240, second model 240 and coordinator-only 120. The submission deadline constraint has been removed. The registered case order and all generation settings remain unchanged. Hard-group completion remains an intermediate milestone; the remaining original cases still run afterward.

The two published snapshots contain 115 saved study attempts in total: 54 main-model and 61 second-model records, including failures. The grids remain incomplete. This page reports verified snapshots, not a live completion counter.
