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

The locally verified checkpoint contains 24 of 240 records and 173 generation requests. G01, G02, G03 and H01 each have both conditions and all three requested seeds. This is six of the 120 required hard-group records; it is not a completed hard-case comparison.

Seven attempts ended at the registered model-stage request limit. Eight ended with provider-service errors: six HTTP 503 responses and two connection or timeout failures. All fifteen failed attempts remain included. The source, data, record and journal checks passed in Colab and locally. Calculated route differences on the Mac were at most 3.553e-15 km, within the disclosed route-only tolerance; scores and rule decisions matched exactly.

The priority appendix was registered before any hard-case model output. It finished G03 before moving to H01. The saved checkpoint also includes the continuation supervisor, controller and their policy. Their source hashes match that policy. The supervisor waits for an existing controller to stop before any continuation, waits five minutes after a temporary service error, and allows at most four continuations per invocation. Quota, access and inspection failures stop it.

[Second-model 24-record evidence](../evidence/Riyadh_Review_Second_Model_Checkpoint_24.zip). Archive SHA256: `396bd9696179bdf6c072b507dab0875747981f63a84183098564c74ee22cf601`.

## Scope confirmed on 28 November

The full 840-record Gemini study is retained: main 240, component removals 240, second model 240 and coordinator-only 120. The submission deadline constraint has been removed. The registered case order and all generation settings remain unchanged. Hard-group completion remains an intermediate milestone; the remaining original cases still run afterward. This page reports a verified saved snapshot, not a live completion counter.
