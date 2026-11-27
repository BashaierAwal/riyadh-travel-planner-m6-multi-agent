# Recovery after an interrupted batch

The first main batch stopped after eleven complete records and one unfinished baseline request for G02 with seed 33. The unfinished journal contains a tool-search response but no final plan or measured completion time. The complete records, including the earlier HTTP 503 failure, and the partial journal remain preserved under main-v1.

The primary comparison uses a fresh complete grid, main-v2, with the same frozen source commit 797621176f2148d804d111437713a7c1c3d899b8, datasets, cases, seeds, models and generation settings. The earlier partial grid is not pooled into it. No hard-case model outcomes had been examined when this recovery was chosen. Failures within the new complete grid remain in its denominators.

The second controller preserves the old folders and reserves the full 60-request allowance for the unfinished prior record when checking its resource cap. That reservation is not a claim that 60 requests were observed or charged. Completed records use their saved actual request counts.
