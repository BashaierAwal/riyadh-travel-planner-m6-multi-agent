# M6 Revised Evaluation Draft

The revised study asks whether a team that checks and repairs a complete itinerary can meet competing travel requirements more reliably than a single planner. Both systems use the same approved Riyadh data and the same tools. The formal experiments are in progress; this draft covers the study design and interpretation rules.

## Related work

Choi, Yoon, Chen, Jha and Pfister present [ATLAS: Constraints-Aware Multi-Agent Collaboration for Real-World Travel Planning](https://proceedings.iclr.cc/paper_files/paper/2026/hash/6c78ae0c1140902bf3a430b1725bcc4e-Abstract-Conference.html), ICLR 2026. Their framework uses constraint management and repeated plan critique. This motivates giving the feasibility specialist a full-plan checking role. Our experiment uses fixed local data and its own bounded repair workflow; it does not reproduce their benchmark results.

## Task and data

Each itinerary contains one hotel, two activities per day and two restaurants per day. Selected places must use existing dataset IDs, and activities must not repeat. The approved data contains 1,125 activities, 19,345 restaurants and 55 hotels. The CSV values and original twenty requests remain unchanged.

The original requests, G01–G20, specify duration, interests and a budget category. Twenty additional requests, H01–H20, introduce a daily distance limit, a hotel-cost cap and balanced activity requirements for two interests. Every added request has a checked feasible example. These examples are used to validate the requests and are not supplied to either model. The held-out hard cases are not used to tune prompts.

Daily distance follows hotel → activity → restaurant → activity → restaurant → hotel. It sums straight-line distances calculated from the recorded coordinates. It does not estimate road travel time. All activities and restaurants have coordinates, but only 23 of the 55 hotels do. Searches for the additional cases return hotels with recorded coordinates; original cases retain access to hotels without coordinates.

The hotel cap applies to its recorded median price multiplied by the case's stated nights. Nights are the larger of one and duration minus one, so even a one-day case explicitly includes one hotel night. The cap excludes food, transport and activities. Dataset prices are historical values.

## Systems and checking

The single agent prepares the whole plan. The team uses a coordinator, an activity specialist and a feasibility and budget specialist. The coordinator delegates work, the activity specialist proposes activities, and the feasibility specialist prepares and checks a full draft. The coordinator integrates the final plan.

Both systems can search the same three datasets and call the same deterministic plan checker. Search results include coordinates and can be ranked near a known place. Saved tool journals show whether the feasibility specialist actually called the whole-plan checker; its role name alone is not treated as evidence that checking occurred. The checker reports broken rules without changing the itinerary. Selected IDs must also have appeared in a successful search result.

After the initial plan, both systems receive deterministic feedback. The single agent makes its own repairs; the team's feasibility specialist reviews the findings before the coordinator repairs the plan. There are at most three outer repair rounds. Drafting and checking calls within a round are logged separately. Each model stage is limited to twelve HTTP requests, and each complete system run is limited to sixty.

The shared execution policy uses temperature zero, requested seeds 11, 22 and 33, an 8,192-output-token ceiling, a sixty-second timeout and at least twelve seconds between HTTP request starts. There are no hidden provider retries. Every completed failed record remains in the results. An intermediate draft cannot replace a missing final answer.

## Original M5 baseline

The original M5 V3 evidence was rechecked for all sixty records: twenty original requests and three seeds. Its saved scores are shown here as historical context. The revised baseline has different tools and a repair policy, so these records are not pooled with it or used as its paired comparison. V2 evidence is not used for the baseline claims below.

| Measure | Mean ± SD of three seed means (%) | SD across sixty runs (percentage points) |
|---|---:|---:|
| Activity preference match | 93.50 ± 2.89 | 19.44 |
| Restaurant budget match | 96.67 ± 2.89 | 18.10 |
| Hotel budget match | 96.67 ± 2.89 | 18.10 |
| Structural itinerary feasibility | 81.67 ± 2.89 | 39.02 |
| Search-tool coverage | 100.00 ± 0.00 | 0.00 |

Structural pass³ was 80%: sixteen of twenty original cases passed structural itinerary feasibility on all three seeds. This historical measure does not certify the new distance, hotel-cost, interest-quota or search-grounding rules. Search-tool coverage records whether each search tool was used; it does not prove that every selected place was returned by search.

Eleven original records failed structural feasibility: nine contained repeated activities and two had no readable output. For example, G05 with seed 33 selected ACT_00813 on both day 1 and day 5. G07 with seed 22 failed to return a readable itinerary. These are saved outcome examples, not evidence that removing or adding a particular team role caused the failure. The [recheck evidence](../revision/reports/M5_V3_RECHECK.json) contains all counts and examples.

## Experimental comparisons

The main grid contains forty requests, three seeds and two systems: 240 records. A dated execution appendix prioritises the twenty hard requests after finishing any started original case, preserving all registered units and their within-case condition order. Group completion and full-grid completion are reported separately. The primary model is gemini-3.5-flash-lite. Original and additional cases are reported separately. The historical M5 V3 baseline remains available as context, but its sixty runs are not pooled with the revised baseline because the tools and repair policy differ.

Two component-removal variants each run the same 120 case and seed combinations. One removes the feasibility specialist while leaving its tools available to the coordinator. The other removes the repair loop while keeping the initial team workflow. Each is compared with the full team from the main grid.

A second 240-record grid runs both systems with gemini-3.1-flash-lite. A further 120-record condition changes only the coordinator to gemini-3-flash-preview, keeping the specialists on the main model. This tests a different coordinator; an improvement is not assumed from its model name.

## Measures and analysis

The original scores remain visible: activity preference match, restaurant budget match, hotel budget match and structural itinerary feasibility. Search-tool coverage is reported separately. Structural feasibility and tool coverage alone do not certify distance, cost or search grounding.

The primary outcome is complete-constraint success on H01–H20, including search grounding. Other measures are broken-rule count, repair rounds, tool calls, HTTP requests, tokens, estimated cost and execution time. An unreadable output fails complete-constraint success and receives a no-output label. Its missing route cannot be interpreted as a successful distance check.

For each condition, the report gives the mean and sample standard deviation of the three seed means, alongside variation across runs. Pass³ is the share of cases that pass on all three runs. Conditions are compared using one mean paired difference per case, preserving its three seeds together. The 95% bootstrap interval uses 20,000 case resamples. A two-sided sign-flip test also operates on case means. Secondary outcomes and component-removal comparisons are exploratory.

Per-attempt execution time includes failed runs. Total elapsed time for an attempt, measured scheduled pacing and elapsed time excluding pacing are reported separately. Service checks, cooldowns and daily-quota waits occur between attempts and are logged separately; they are outside the measured time for an individual attempt. Time excluding pacing still includes network, tool and local processing. Cost estimates use dated official prices for the exact model and observed billable tokens, including thinking tokens where reported. List-price estimates remain separate from actual billing. Separate service-readiness requests are logged as operational overhead and excluded from individual planning-case costs. Cost and speed are interpreted alongside success, since an early failure can consume less time or fewer tokens.

## Failure interpretation and limits

Failure labels cover missing output, unknown places, repeated activities, budget, distance, preferences, structure, missing information and missing search grounding. The report retains all applicable labels and gives saved examples. Each failed attempt also receives one primary label, using the table order below when several apply.

| Primary label | Definition |
|---|---|
| No output | No readable final itinerary was returned. |
| Unknown place | A selected ID is absent from the approved dataset. |
| Repeated activity | An activity ID occurs more than once in the trip. |
| Budget | A restaurant or hotel category fails its budget rule, or total hotel cost exceeds the cap. |
| Distance | A measured daily route exceeds its stated kilometre limit. |
| Preference | The required number of distinct activities for an interest is not met. |
| Structure | The itinerary has a wrong number of days or slots, or another required structural field is invalid. |
| Missing information | A rule cannot be measured from the recorded coordinates or price. |
| Missing search grounding | A selected ID was not returned by a successful dataset search. |

Service errors and registered request-limit failures are counted separately within these outcomes. They remain in the denominator, but do not by themselves establish that one planning design is weaker.  Component-removal results are needed before attributing an observed failure to a particular role or repair mechanism.

The original data limits preference matching in G05, G08 and G15 when activities must be unique. Their maximum activity preference match is 90%, 66.67% and 80%, respectively. These ceilings do not make every structurally valid plan impossible: using another activity can fill a slot while lowering preference match. The requests remain unchanged, and such tradeoffs must be distinguished from model or coordination failures.

The study evaluates a fixed local dataset and a small set of designed requests. The added cases combine five interest pairs with four budget and distance scenarios. Shared templates limit diversity, so case-level intervals should not be read as uncertainty for every kind of travel request. Straight-line routes, historical median prices and a checked feasible example do not establish real-world booking feasibility. Model versions, service conditions and requested seed behavior can also affect reproducibility. Across-computer replay allows a 1e-12 km tolerance only for calculated route numbers; hashes, scores and rule decisions remain exact. The twenty deterministic feasible examples produced identical rule decisions in Colab and on the Mac. One same-seed case was repeated twice and produced the same readable plan; this does not establish general determinism.

Dataset sources and licences are documented in the revision. The restaurant source lists its licence as unknown, and the shopping source has conflicting licence information. These unresolved terms must remain visible. Credentials are kept outside source files and saved model journals.

## Dataset references

The source pages below were checked on 27 November 2026. They identify the upstream sources used for the frozen processed tables, rather than a claim that a current download matches the earlier snapshot.

| Dataset and owner | Licence shown |
|---|---|
| Meshal Alsanari, [Riyadh Entertainment](https://www.kaggle.com/datasets/meshalalsanari/riyadh-entertainment), Kaggle | MIT |
| Meshal Alsanari, [Riyadh Mall](https://www.kaggle.com/datasets/meshalalsanari/riyadh-mall), Kaggle | MIT metadata; its description also states non-commercial research use |
| Audiala, [Audiala Places](https://github.com/audiala/open-data), GitHub | CC BY 4.0. Data by Audiala — [audiala.com](https://audiala.com) |
| Fahd (fahd09), [Riyadh Restaurants 20K](https://www.kaggle.com/datasets/fahd09/riyadh-restaurants-20k), Kaggle | Unknown |
| Mohammed Alsubaie, [Riyadh Hotels](https://www.kaggle.com/datasets/mohammedalsubaie/riyadh-hotels), Kaggle | Apache 2.0 |

The unknown restaurant licence and conflicting shopping-source terms remain unresolved. The [source record](../revision/DATA_SOURCES.md) documents these limits. Public availability alone does not grant permission to redistribute a dataset.
