# Connection and workflow pilot

Both systems completed the separate P00 development request and passed the registered checks. This confirms that the published code can call the model, use the shared tools, save records to Drive and reproduce the results locally. It does not answer the research question.

| System | Complete plan passed | Repair rounds | HTTP requests | Measured system time |
|---|---:|---:|---:|---:|
| Single agent | Yes | 0 | 6 | 72.89 seconds |
| Three-agent team | Yes | 0 | 8 | 95.81 seconds |

The model was gemini-3.5-flash-lite with temperature zero and requested seed 11. P00 is not part of G01–G20 or H01–H20. The example used for designing hard cases was not supplied to the model. Neither system needed a repair on this request, so repair behavior is supported by the software tests rather than demonstrated by this pilot.

The [complete evidence archive](../evidence/Riyadh_Review_Pilot_v1.zip) contains the requests, responses, tool calls, records, source snapshot, scores and analysis. Its SHA-256 is `22f9610ac8585a8f8ea5aa63ca390ce340deedaba377453098ef93626f939a30`. Both records passed the evidence verifier in Colab and again locally using the saved source snapshot and unchanged datasets.

The pilot used source commit `40f6e340ab0ac7049d4be6a89a0ce2ac73c677e5`. Use that commit or its saved snapshot when reproducing this older version. The final comparison separately records an explicit output-token ceiling and the exact source commit before any formal runs. These preparation changes are shared by both conditions and do not change the approved data or original cases.

This two-record pilot supplies no confidence interval, no repeated-seed verification and no evidence that either architecture is better. Those questions require the registered formal experiments.
