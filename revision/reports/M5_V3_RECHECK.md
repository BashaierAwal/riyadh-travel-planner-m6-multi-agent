# Review of the original M5 baseline

The baseline is V3: 60 saved runs from 20 fixed cases and three requested seeds. All scores below were recalculated from the saved plans and unchanged CSVs. V2 is historical only. This review does not contain results for the new hard cases.

| Metric | Mean (%) | SD of three seed means |
|---|---:|---:|
| APM | 93.50 | 2.89 |
| RBM | 96.67 | 2.89 |
| HBM | 96.67 | 2.89 |
| IFR | 81.67 | 2.89 |
| RTC | 100.00 | 0.00 |

**Success on all three runs (pass³): 80.0% of cases.** A case counts only when all three saved outputs pass structural IFR. This does not verify that the provider honors seeds.

The eleven structural failures comprise nine plans with repeated activities and two missing or unreadable outputs. The repeated activities occur in G05, G08 and G15 at all three seeds. G07/11 ends with a provider quota error; G07/22 has an unexpected text prefix before JSON. Full examples and their saved plans are in M5_V3_RECHECK.json.

The current tests leave little room for improvement: all readable plans match the hotel and restaurant budget labels. RTC also reaches 100% for the two failed generations. It therefore measures tool coverage, not successful planning. The new distance, SAR hotel cap and competing-interest cases address this limit.

The original design can reuse a highly ranked activity when too few matching unique activities exist. That observation motivates checking and repairing complete plans, but the new component-removal experiments are still required to test whether repairs or the feasibility specialist explain any improvement.

Per-case list-price estimates are in M5_V3_COST_ESTIMATES.json. They use the exact recorded model and official prices checked on 27 November 2026. Failed requests or missing usage leave a partial observed subtotal rather than an invented complete cost. These estimates do not establish what the account was charged.
