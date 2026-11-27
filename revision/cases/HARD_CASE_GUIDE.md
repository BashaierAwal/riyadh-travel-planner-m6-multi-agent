# Why the added tests are harder

The original requests use a trip duration, interests and a budget category. The added requests also limit daily travel distance and the total hotel cost, and require a balanced number of activities from two interests. The same approved datasets supply every place.

For example, H01 needs one shopping activity and one entertainment activity, a hotel costing at most 350 SAR for its explicit one night, and a daily route of at most 25 straight-line kilometres. Choosing a well-rated place is not enough: the choices must work together.

Each row below has at least one checked feasible example. It is not the only correct itinerary. The automated checker counts broken rules in whichever plan the model produces. These candidate counts describe the data; they are not experimental success rates.

| Case | Days | Interests | Daily km cap | Hotel cap SAR | Nights | Hotels meeting cost and coordinate rules |
|---|---:|---|---:|---:|---:|---:|
| H01 | 1 | Shopping + Entertainment | 25 | 350 | 1 | 1 |
| H02 | 2 | Shopping + Entertainment | 40 | 750 | 1 | 4 |
| H03 | 2 | Shopping + Entertainment | 50 | 1400 | 1 | 3 |
| H04 | 3 | Shopping + Entertainment | 40 | 900 | 2 | 2 |
| H05 | 1 | Culture & History + Shopping | 25 | 350 | 1 | 1 |
| H06 | 2 | Culture & History + Shopping | 40 | 750 | 1 | 4 |
| H07 | 2 | Culture & History + Shopping | 50 | 1400 | 1 | 3 |
| H08 | 3 | Culture & History + Shopping | 40 | 900 | 2 | 2 |
| H09 | 1 | Nature & Outdoors + Entertainment | 25 | 350 | 1 | 1 |
| H10 | 2 | Nature & Outdoors + Entertainment | 40 | 750 | 1 | 4 |
| H11 | 2 | Nature & Outdoors + Entertainment | 50 | 1400 | 1 | 3 |
| H12 | 3 | Nature & Outdoors + Entertainment | 40 | 900 | 2 | 2 |
| H13 | 1 | Religious + Shopping | 25 | 350 | 1 | 1 |
| H14 | 2 | Religious + Shopping | 40 | 750 | 1 | 4 |
| H15 | 2 | Religious + Shopping | 50 | 1400 | 1 | 3 |
| H16 | 3 | Religious + Shopping | 40 | 900 | 2 | 2 |
| H17 | 1 | Landmarks & Sightseeing + Entertainment | 25 | 350 | 1 | 1 |
| H18 | 2 | Landmarks & Sightseeing + Entertainment | 40 | 750 | 1 | 4 |
| H19 | 2 | Landmarks & Sightseeing + Entertainment | 50 | 1400 | 1 | 3 |
| H20 | 3 | Landmarks & Sightseeing + Entertainment | 40 | 900 | 2 | 2 |

Distances use the fixed hotel → activity → restaurant → activity → restaurant → hotel sequence. The price cap covers the recorded hotel median price multiplied by the stated nights. The hotel remains in the requested Low, Medium or High category. Each interest must occupy at least as many distinct activity slots as the number of requested days.

Full acceptance rules and candidate counts are in [HARD_CASE_CONTRACT.json](HARD_CASE_CONTRACT.json). The original G01–G20 file remains unchanged.
