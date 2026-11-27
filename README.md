# M6 review revision

The revised comparison follows the updated M5 evaluation. It keeps the approved datasets and G01–G20, adds H01–H20, and gives both systems the same checking tools and a maximum of three repairs.

- [Revised protocol](revision/PROTOCOL.md)
- [Current status](revision/STATUS.md)
- [Original and harder cases](revision/cases/)
- [Shared implementation and run instructions](revision/README.md)
- [Verified development pilot](revision/reports/PILOT_v1.md)
- [Dataset references and licence checks](revision/DATA_SOURCES.md)

The new formal comparison is not yet complete. The earlier experiment and its evidence are preserved below as history. Its results are not results for the harder requests or the revised repair workflow.

## Earlier M6 experiment

**Updated 9 November 2026: formal-v3 completed and verified — 120 live records, 484 HTTP requests. See reports/M6_Report.md for the completed comparison. Earlier incomplete versions are preserved separately.**

# M6 — Riyadh Travel Planner

مشروع M6 مستقل عن M5، بدفتر Colab وتسليم مستقلين.

Independent three-agent implementation and controlled evaluation. M5 is preserved in its separate repository.

Start with [M6_README.md](M6_README.md), [the protocol](docs/M6_Experiment_Protocol.md), and [the bilingual team guide](M6_Team_Guide.html).

Notebook: [M6_Colab_Run.ipynb](notebooks/M6_Colab_Run.ipynb). All live flags are false by default.

Status: offline implementation/tests and the two-record live pilot complete; formal comparison complete. Mock results are not research evidence. See [the pilot report](reports/M6_Pilot_Report.md).

Working Drive notebook: [M6_Colab_Run.ipynb](https://colab.research.google.com/drive/1q633AqPjDEXYOWSFh70txF9yJooBnG-O).

The frozen scorer, search tools, data and golden cases are copied from verified M5 commit e59f1b49c0c6d7d695a885df6cf9fafe4113ab61. See M6_Provenance.json.

GitHub includes the [120 complete formal-v3 records and tool journals](m6_runs/formal-v3/), [comparison, per-record scores and cost estimates](reports/formal-v3/), and [saved-evidence audit](reports/M6_Formal_Audit.json). No separate archive or model key is needed to verify the formal results. See [run storage and verification](m6_runs/README.md).

Formal-v1 is incomplete after runtime-storage loss: only 12 raw records are recovered despite a 114-record progress log. See [the execution incident](reports/M6_Execution_Incident.md). No complete formal-v1 comparison is claimed; formal-v2 then stopped after five requests because the provider reported its daily free-tier quota exhausted. Its one complete record and interrupted journal are preserved in Drive and locally.

## Supplementary itinerary judge

The [supplementary judge evaluation](evaluation/llm_judge/JUDGE_REPORT.md) completed on 25 November 2026: all 114 readable plans were graded (59 baseline, 55 three-agent), with six generation failures reported separately. Mean quality scores were **4.496/5** and **4.532/5**. The small conditional difference does not establish overall superiority. [Grades, reasons and saved evidence](evaluation/llm_judge/) and an offline verifier are included. The original formal-v3 results and evidence remain unchanged.

## Dataset sources and licences

Source pages were checked on 27 November 2026. The approved processed CSVs remain unchanged.

| Source | Owner | Licence shown |
|---|---|---|
| [Riyadh Entertainment](https://www.kaggle.com/datasets/meshalalsanari/riyadh-entertainment) | Meshal Alsanari | MIT |
| [Riyadh Mall](https://www.kaggle.com/datasets/meshalalsanari/riyadh-mall) | Meshal Alsanari | MIT metadata; the description also states non-commercial research use |
| [Audiala Places](https://github.com/audiala/open-data) | Audiala | CC BY 4.0; Data by Audiala — [audiala.com](https://audiala.com) |
| [Riyadh Restaurants 20K](https://www.kaggle.com/datasets/fahd09/riyadh-restaurants-20k) | Fahd (fahd09) | Unknown |
| [Riyadh Hotels](https://www.kaggle.com/datasets/mohammedalsubaie/riyadh-hotels) | Mohammed Alsubaie | Apache 2.0 |

The restaurant licence and the conflicting shopping-source description remain unresolved. See [the full source references and checks](revision/DATA_SOURCES.md). No claim of complete redistribution clearance is made.
