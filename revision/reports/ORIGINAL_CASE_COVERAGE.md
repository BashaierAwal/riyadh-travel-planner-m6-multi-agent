# Activity coverage in the original cases

This check describes the unchanged approved data and G01–G20 requests. It does not add experimental outcomes or change any request.

An itinerary has two activities per day, and repeated activity IDs fail the structural check. Some requests have fewer matching unique activities than their required slots. Such a plan can satisfy the unique-slot structure by including an activity outside the requested interests, but then its activity preference match (APM) is below 100%. These requests do not make every structurally valid itinerary impossible.

For G05, the five-day Religious request needs ten activity slots, but the CSV contains nine distinct Religious place IDs. Its APM ceiling with unique activities is therefore 90%. A repeated religious activity and an out-of-interest activity have different effects: the former breaks the no-repeat rule, while the latter lowers APM. Actual failed records must still be inspected before attributing a failure to this limitation.

| Case | Days | Interests | Activity slots | Matching unique IDs | Maximum APM with unique activities |
|---|---:|---|---:|---:|---:|
| G01 | 1 | Shopping | 2 | 858 | 100.0% |
| G02 | 2 | Entertainment | 4 | 207 | 100.0% |
| G03 | 3 | Culture & History | 6 | 9 | 100.0% |
| G04 | 4 | Nature & Outdoors | 8 | 9 | 100.0% |
| G05 | 5 | Religious | 10 | 9 | 90.0% |
| G06 | 1 | Sports | 2 | 4 | 100.0% |
| G07 | 2 | Landmarks & Sightseeing | 4 | 4 | 100.0% |
| G08 | 3 | Sports | 6 | 4 | 66.7% |
| G09 | 4 | Shopping + Entertainment | 8 | 1065 | 100.0% |
| G10 | 5 | Culture & History + Religious | 10 | 18 | 100.0% |
| G11 | 1 | Nature & Outdoors + Sports | 2 | 13 | 100.0% |
| G12 | 2 | Shopping + Landmarks & Sightseeing | 4 | 862 | 100.0% |
| G13 | 3 | Entertainment + Culture & History | 6 | 216 | 100.0% |
| G14 | 4 | Religious + Nature & Outdoors | 8 | 18 | 100.0% |
| G15 | 5 | Sports + Landmarks & Sightseeing | 10 | 8 | 80.0% |
| G16 | 1 | Shopping + Culture & History + Sports | 2 | 871 | 100.0% |
| G17 | 2 | Entertainment + Religious + Nature & Outdoors | 4 | 225 | 100.0% |
| G18 | 3 | Shopping + Entertainment + Landmarks & Sightseeing | 6 | 1069 | 100.0% |
| G19 | 4 | Culture & History + Religious + Sports | 8 | 22 | 100.0% |
| G20 | 5 | Shopping + Entertainment + Nature & Outdoors | 10 | 1074 | 100.0% |

These are data-coverage ceilings, not observed model scores. They assume the whole approved activity table is available; a limited search result can supply fewer candidates. No distance or budget constraint is added to the original cases by this check. H01–H20 have separate acceptance rules and checked feasible examples.
