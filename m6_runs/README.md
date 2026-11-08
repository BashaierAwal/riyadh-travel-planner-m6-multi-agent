# M6 run storage

`validation-*` contains OFFLINE SDK/HTTP fixtures. Its token counts and fake-clock timings are not measurements of Gemini. `pilot-*` and `formal-*` are separate live versions and do not exist until separately approved runs occur.

The earlier validation archive retains `validation-v1` (120 fixture records). This independent M6 source export stores the generator and audit summary; reproduce the fixtures with `python -m m6planner mock-smoke --version validation-reproduction`. Do not commit or upload credentials. Real experiment evidence must be retained and independently verified before reporting results.

Never replace M5/V3 or silently rerun a failed saved record. Download each live version after every approved chunk. See `docs/M6_Experiment_Protocol.md` and `M6_README.md`.
