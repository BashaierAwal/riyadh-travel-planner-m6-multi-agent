# Numerical replay across computers

The frozen checker uses full-precision floating-point route distances. A deterministic cross-platform check of the twenty existing feasible examples found that eight matched exactly between Colab and the Mac. The other twelve differed only in calculated route kilometres, by at most 3.552713678800501e-15 km. All twenty had identical rule decisions and other check results.

[The calculation receipt](DISTANCE_REPLAY.json) records the comparison. [The Colab calculations](../evidence/Riyadh_Review_Distance_Replay.json) retain the computed checks and the hash of the unchanged reference examples. These are deterministic software checks, not model-performance results.

The original verifier remains unchanged and provides exact replay in the generation environment. The separate `scripts/Verify_Study_Replay.py` supports replay on another computer. It allows an absolute difference of at most 1e-12 km only for calculated `routes[index].km` fields. It still checks hashes, IDs, list ordering, scores, rule decisions and other values exactly. It changes no model input, dataset, saved record, acceptance rule or reported score. Each export writes `analysis/REPLAY_MODE.json`, including the verifier hash, tolerance and maximum observed difference.

Two additional adversarial tests passed in both working copies. A marked fixture demonstrates that the new replay accepts simulated route rounding after valid journal checks, while still rejecting a changed preference score even when that change is smaller than the route tolerance and its record hash is recomputed. Other checks reject altered hotel cost, IDs, ordering, pass flags and route errors beyond the tolerance. Fixture outputs remain software tests only.

For a complete cohort, run:

```bash
python scripts/Verify_Study_Replay.py RUN_FOLDER
```

For a progress snapshot, append `--allow-partial`. This still does not produce comparative statistics from an incomplete grid.
