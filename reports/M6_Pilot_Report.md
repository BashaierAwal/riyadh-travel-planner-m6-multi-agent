# M6 paired pilot — G01 / requested seed 11

Date: 8 November 2026. Status: two live pilot records completed and independently checked. This is a readiness test, not the formal comparison; neither pilot record substitutes for a formal record.

Model: `gemini-3.5-flash-lite`; requested temperature: 0; SDK: `google-genai==1.30.0`. The observed model-version field matches the requested model. Seed 11 was present in every request; its provider-side effect is not established. Runtime: Colab Python 3.13, with the pinned project dependencies.

| Observation | Single-agent baseline | Three-agent treatment |
|---|---:|---:|
| Parsed and structurally valid |Yes |Yes |
| APM / RBM / HBM / IFR / RTC (%) |100 / 100 / 100 / 100 / 100 |100 / 100 / 100 / 100 / 100 |
| HTTP requests, including failures |3 |6 |
| Whole-workflow attempts |2 |1 |
| System wall time (s) |58.879 |84.460 |
| Measured pacing waits (s) |22.482 |55.626 |
| Measured retry wait (s) |5.000 |0 |
| Residual processing time (s) |31.397 |28.834 |
| Observed prompt tokens |3,121 |10,020 |
| Observed candidate tokens |156 |425 |
| Observed total tokens |3,277 |10,445 |
| Responses with usage / HTTP responses |2 / 3 |6 / 6 |
| Currency cost |Unknown |Unknown |

The first baseline request received HTTP 504. The shared policy retained that attempt, waited, restarted the workflow, and produced a valid final output. The baseline HTTP statuses were 504/200/200; all six treatment requests returned200. The treatment's stage counts were 1/2/2/1 within its 1/4/4/1 allocation. Across both conditions there were 9 requests, below the approved 60-request session cap; the shortest consecutive start gap was 12.000532 seconds.

Checks verified code/data identities, journal/record linkage, independent scores and RTC, request/model/seed settings, final recommendations' membership in final-attempt tool results, limits, token aggregation and timing decomposition. See `M6_Pilot_Audit.json`. Raw outputs, HTTP/tool traces, errors and comparisons are retained in the separate local `M6_Pilot_Evidence.zip`; extract it under `m6_runs/` to restore `pilot-v1/`. They are not uploaded to GitHub.

The 504 response provided no usage metadata. Baseline token values are therefore the observed sums, not proof of complete billed usage. Payment and price-based estimates remain unknown/null; no zero-cost claim is made.

One paired case cannot establish superiority, variance or general reliability. The observed longer treatment wall time includes more paced requests; the baseline also had a service failure. The pilot supports proceeding with the unchanged frozen design in separately approved formal chunks, with 120 new formal records (60 per condition) and all failures retained.
