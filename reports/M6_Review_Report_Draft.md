# M6 Revised Evaluation Draft

The revised study asks whether a team that checks and repairs a complete itinerary can meet competing travel requirements more reliably than a single planner. Both systems use the same approved Riyadh data and the same tools. The formal experiments are in progress; this draft covers the study design and interpretation rules.

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

## Experimental comparisons

The main grid contains forty requests, three seeds and two systems: 240 records. The primary model is gemini-3.5-flash-lite. Original and additional cases are reported separately. The historical M5 V3 baseline remains available as context, but its sixty runs are not pooled with the revised baseline because the tools and repair policy differ.

Two component-removal variants each run the same 120 case and seed combinations. One removes the feasibility specialist while leaving its tools available to the coordinator. The other removes the repair loop while keeping the initial team workflow. Each is compared with the full team from the main grid.

A second 240-record grid runs both systems with gemini-3.1-flash-lite. A further 120-record condition changes only the coordinator to gemini-3-flash-preview, keeping the specialists on the main model. This tests a different coordinator; an improvement is not assumed from its model name.

## Measures and analysis

The original scores remain visible: activity preference match, restaurant budget match, hotel budget match and structural itinerary feasibility. Search-tool coverage is reported separately. Structural feasibility and tool coverage alone do not certify distance, cost or search grounding.

The primary outcome is complete-constraint success on H01–H20, including search grounding. Other measures are broken-rule count, repair rounds, tool calls, HTTP requests, tokens, estimated cost and execution time. An unreadable output fails complete-constraint success and receives a no-output label. Its missing route cannot be interpreted as a successful distance check.

For each condition, the report gives the mean and sample standard deviation of the three seed means, alongside variation across runs. Pass³ is the share of cases that pass on all three runs. Conditions are compared using one mean paired difference per case, preserving its three seeds together. The 95% bootstrap interval uses 20,000 case resamples. A two-sided sign-flip test also operates on case means. Secondary outcomes and component-removal comparisons are exploratory.

Execution time includes failed runs. Total elapsed time, measured scheduled pacing and elapsed time excluding pacing are reported separately. Time excluding pacing still includes network, tool and local processing. Cost estimates use dated official prices for the exact model and observed billable tokens, including thinking tokens where reported. List-price estimates remain separate from actual billing.

## Failure interpretation and limits

Failure labels cover missing output, unknown places, repeated activities, budget, distance, preferences, structure, missing information and missing search grounding. The report retains all applicable labels and gives saved examples. Component-removal results are needed before attributing an observed failure to a particular role or repair mechanism.

The original data limits preference matching in G05, G08 and G15 when activities must be unique. Their maximum activity preference match is 90%, 66.67% and 80%, respectively. These ceilings do not make every structurally valid plan impossible: using another activity can fill a slot while lowering preference match. The requests remain unchanged, and such tradeoffs must be distinguished from model or coordination failures.

The study evaluates a fixed local dataset and a small set of designed requests. The added cases combine five interest pairs with four budget and distance scenarios. Shared templates limit diversity, so case-level intervals should not be read as uncertainty for every kind of travel request. Straight-line routes, historical median prices and a checked feasible example do not establish real-world booking feasibility. Model versions, service conditions and requested seed behavior can also affect reproducibility. One same-seed case was repeated twice and produced the same readable plan; this does not establish general determinism.

Dataset sources and licences are documented in the revision. The restaurant source lists its licence as unknown, and the shopping source has conflicting licence information. These unresolved terms must remain visible. Credentials are kept outside source files and saved model journals.
