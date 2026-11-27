# Current experiment progress

Updated 27 November 2026. The revised comparison is incomplete.

## Main grid

The main gemini-3.5-flash-lite grid has 54 of 240 saved records. These cover G01–G09 with both systems and all three requested seeds. No formal H01–H20 result is claimed.

Five records ended at the registered model-stage request limit. A further record, treatment G09 with seed 33, ended at coordinator dispatch when the provider returned HTTP 429. Its quota identifier was `GenerateRequestsPerDayPerProjectPerModel-FreeTier`. All six error records remain in the grid and will not be replaced. A model-stage limit and a provider quota are different failure categories.

The snapshot contains 405 generation requests. This excludes earlier pilots, the earlier partial main grid and the controller's conservative reservation for its interrupted record. Checksums, journal integrity, rescoring and dataset-backed tool replay passed both in Colab and locally.

[Saved 54-record evidence](../evidence/Riyadh_Review_Checkpoint_54.zip). Archive SHA256: `52e731b204dee9f640e0ba7df4f81b765e21f0f4b2152b7789052e307c4b942a`.

## Remaining execution

The main grid waits for its daily model quota to reset. The registered second-model grid has started with gemini-3.1-flash-lite; its model access and successful generation responses were checked. It uses the frozen cases, seeds, prompts, tools and limits. This changes the order of independent grids, without selecting a model from observed hard-case performance. Component-removal and coordinator-only grids remain pending.

The [controller](../../scripts/Run_Review_Study_v4.py) can select a registered stage and uses larger batches to reduce startup scans. It retains failed records and stops on service or session-resource errors. Source commit `797621176f2148d804d111437713a7c1c3d899b8`, generation settings and approved data remain fixed. No paid upgrade was made.

## Checking role and interpretation

The [role-tool audit](ROLE_TOOL_AUDIT_54.json) counts executed feasibility-stage calls to check_plan, excluding global controller checks. The [activity coverage note](ORIGINAL_CASE_COVERAGE.md) explains the unchanged original-data limits. Neither diagnostic replaces a complete comparison. Paired estimates, intervals and pass³ for revised model performance require the completed registered grids.
