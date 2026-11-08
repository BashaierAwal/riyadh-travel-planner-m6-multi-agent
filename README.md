# M6 — Riyadh Travel Planner

مشروع M6 مستقل عن M5، بدفتر Colab وتسليم مستقلين.

Independent three-agent implementation and controlled evaluation. M5 is preserved in its separate repository.

Start with [M6_README.md](M6_README.md), [the protocol](docs/M6_Experiment_Protocol.md), and [the bilingual team guide](M6_Team_Guide.html).

Notebook: [M6_Colab_Run.ipynb](notebooks/M6_Colab_Run.ipynb). All live flags are false by default.

Status: offline implementation/tests and the two-record live pilot complete; formal comparison pending. Mock results are not research evidence. See [the pilot report](reports/M6_Pilot_Report.md).

Working Drive notebook: [M6_Colab_Run.ipynb](https://colab.research.google.com/drive/1q633AqPjDEXYOWSFh70txF9yJooBnG-O).

The frozen scorer, search tools, data and golden cases are copied from verified M5 commit e59f1b49c0c6d7d695a885df6cf9fafe4113ab61. See M6_Provenance.json.

Detailed pilot prompts, responses and tool traces are preserved in the separate local evidence archive. This repository publishes the implementation, reports and aggregate audit only. To verify raw pilot evidence, extract M6_Pilot_Evidence.zip under m6_runs/.

Formal-v1 is incomplete after runtime-storage loss: only 12 raw records are recovered despite a 114-record progress log. See [the execution incident](reports/M6_Execution_Incident.md). No complete formal comparison is claimed; formal-v2 then stopped after five requests because the provider reported its daily free-tier quota exhausted. Its one complete record and interrupted journal are preserved in Drive and locally.
