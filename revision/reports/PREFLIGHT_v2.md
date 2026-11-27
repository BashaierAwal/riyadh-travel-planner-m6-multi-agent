# Final pilot and repeated-seed check

The final shared policy passed a separate development pilot before formal execution. Both systems completed P00 and met its requirements. The single agent used six HTTP requests and the team used eight; neither needed a repair on this request.

We also ran original case G01 twice with seed 11 using the same model and settings. Both plans were readable, passed the checks and were identical. Each run used three HTTP requests. This supports repeatability for this one pair. It does not establish that the provider honors seeds on every request, or that different seeds produce different outputs.

The model was gemini-3.5-flash-lite. The generation source was frozen at commit `797621176f2148d804d111437713a7c1c3d899b8`, with temperature zero, an 8,192-output-token ceiling per request and the shared checking and repair policy. P00 is separate from the formal forty-case grid. The seed-check records also remain separate and do not replace formal G01 runs.

The [saved preflight evidence](../evidence/Riyadh_Review_Preflight_v2.zip) includes all four records, requests, responses, tool calls, source snapshots, scores and usage estimates. SHA-256: `e7a2fd0e892e15235497604268ed0b19a81dd763a67ef78ed9d661f746fc89cc`. Both version folders passed verification in Colab and again locally against the unchanged approved datasets.

These four records are preparation checks. Formal comparisons, confidence intervals and component-removal conclusions require their own complete experiment grids.
