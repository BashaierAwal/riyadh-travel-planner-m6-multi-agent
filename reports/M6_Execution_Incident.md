# M6 execution incident — formal-v1

Status: incomplete evidence; no complete formal comparison can be reported. Date: 8 November 2026.

The preserved notebook control output reports 114 completed records and 463 HTTP requests at 2026-11-08T16:38:48Z (19:38:48 Riyadh). It does not contain a 120-record completion marker or a completed final audit. The final six records and final total request count are unknown.

Only the 006- and 012-record checkpoint ZIPs were downloaded and verified outside Colab. They overlap, so the durable evidence contains 12 unique formal records (6 per condition), with 48 HTTP requests. At least 102 records reported complete by the controller lack recovered raw outputs and journals. Counters do not substitute for those outputs. The two pilot records are separate and are not pooled into the formal cohort.

On reconnection, Colab supplied a new runtime containing only sample_data; the previous runtime was absent from Active sessions. Chrome download history and a filename search of Downloads/Desktop/the workspace showed no later checkpoint archive. The recovered notebook contains progress messages and small download instructions, not the missing ZIP data. A separate read-only review confirmed the 12 raw records and the 114-record progress log. The exact time/cause of the earlier runtime's termination is not established.

The persistence failure was that later archives remained in temporary runtime storage and their transfers outside the runtime were not confirmed. Programmatic download requests stayed pending during the long-running cell. Two native file-pane downloads succeeded, but a durable later transfer was not established before the session was lost. The original notebook snapshot, control outputs, available records and checkpoint ZIPs are preserved; nothing is rewritten as a successful complete cohort.

## Persistent-storage recovery — formal-v2

`scripts/M6_Run_Persistent.py` writes every event and record directly to an authorized mounted Google Drive destination, reads back checksums/journal linkage and creates/verifies a separate ZIP after each batch. It refuses live temporary-storage destinations, prior incomplete records and saved terminal service failures. Two mocked tests passed. After explicit Drive authorization, an actual Colab write/fsync/readback, independent Drive web preview and browser download produced the identical SHA256 ed9379a331913068ad0b55393d1991718dcdc517c362b285758bbe3665d1add6.

A fresh `formal-v2` cohort was explicitly approved and started instead of silently replacing missing `formal-v1` evidence or rewriting old records. The frozen model, cases, seeds, prompts, scorer and per-record retry/pacing policy stay unchanged. Storage and its logging overhead must be documented for both conditions. No model request was made until the durable-storage check passed.

The conservative prior-use reservation is 652 requests: 463 observed formal requests, up to 180 for the unknown final six records, plus 9 pilot requests. The prepared recovery cap is 2948, keeping the combined M6 request ceiling at 3600. This is a budget reservation, not a claim that 652 requests actually occurred. Actual billing and the missing tail's usage remain unknown.

## Service stop on 8 November 2026

Formal-v2 made five HTTP requests: the baseline G01/seed11 completed with two requests; the treatment made three requests before the provider returned HTTP 429 RESOURCE_EXHAUSTED. Its saved response states that the daily free-tier limit of 500 requests per project/model was exhausted, with retryDelay 43404 seconds (approximately 12 hours). This is the provider response for this account at that time, not a general pricing or quota guarantee.

The shared retry policy entered that long provider-directed wait. Once identified, execution was interrupted at 2026-11-08T20:09:12Z (23:09 Riyadh), before another request. No purchase, plan change or model substitution occurred. One complete baseline record and one interrupted treatment journal are preserved directly in Drive and in the downloaded M6_Formal_V2_Stopped.zip (SHA256 bcdb357b2a93138ce2b90b5db4adbd0d6d19b1d8a723ad2edac40a020caae44d). The archive CRC and local/download hash match.

The interrupted treatment has no completed record and must not be scored as a completed run or silently retried. No further automatic live execution is enabled. A full 120-record comparison remains unfinished; all pilot and formal versions stay separate. The daily quota prevented completing the comparison that evening.

## Subsequent completion — 9 November 2026

Formal-v3 completed a fresh 120-record cohort with 484 requests after quota reset. Direct Drive storage and checkpoint ZIPs preserved all records. The complete archive passed local CRC and independent scoring/integrity verification. Earlier incomplete attempts remain separate and are not pooled. See M6_Report.md for completed results.
