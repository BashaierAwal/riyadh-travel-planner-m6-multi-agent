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

The locally verified checkpoint contains 46 of 240 records and 359 generation requests. G01–G03 and H01–H04 each have both conditions and all three requested seeds; H05 has four of its six planned records. The hard group has 28 of 120 required records and remains incomplete.

Sixteen attempts ended at the registered model-stage request limit. Thirteen ended with provider-service errors: eleven HTTP 503 responses and two connection or timeout failures. All these attempts remain included. The saved HTTP 503 responses report temporary high demand. Source, data, record and journal checks passed in Colab and locally. The maximum route-only replay difference on the Mac was 7.106e-15 km; scores and rule decisions matched exactly.

The [request-configuration audit](MODEL_SETTINGS_CHECK_46.json) checked all 359 saved generation requests. Both systems and every serial role requested gemini-3.1-flash-lite, the recorded seed, temperature zero and the registered 8,192-output-token ceiling. This confirms requested settings, not that the provider produces deterministic outputs.

The priority appendix was registered before any hard-case model output. It finished G03 before H01. The snapshot includes the bounded continuation supervisor, controller and their policy. After repeated service failures, the supervisor stopped at its continuation limit. Two separate availability checks then returned HTTP 200: one short request with the shared tool declarations and one with a larger synthetic context. Their saved diagnostic trace is separate from the case records and is not scored or counted in the 359 study requests. A new bounded continuation was started after these checks; saved failed attempts are never retried or replaced.

[Second-model 46-record evidence](../evidence/Riyadh_Review_Second_Model_Checkpoint_46.zip). Archive SHA256: `f78ea726a8f6f6edce497d35853b5b18d88eab2fd19c6d0d82a94f58a812d2af`.

## Scope confirmed on 28 November

The full 840-record Gemini study is retained: main 240, component removals 240, second model 240 and coordinator-only 120. The submission deadline constraint has been removed. The registered case order and all generation settings remain unchanged. Hard-group completion remains an intermediate milestone; the remaining original cases still run afterward.

The two published snapshots contain 100 saved study attempts in total: 54 main-model and 46 second-model records, including failures. The grids remain incomplete. This page reports verified snapshots, not a live completion counter.
