"""Paired case-level inference, retaining all requested seeds and failures."""

from collections import defaultdict
from itertools import product
from random import Random
from statistics import mean, stdev


def quantile(values, p):
    values = sorted(values)
    x = (len(values)-1)*p
    lo = int(x)
    return values[lo] + (x-lo)*(values[min(lo+1, len(values)-1)]-values[lo])


def paired_inference(differences, draws=20000, random_seed=683):
    """One mean difference per case; the three repeated seeds are not independent cases."""
    values = list(differences)
    if len(values) < 2:
        raise ValueError("At least two paired cases required")
    rng = Random(random_seed)
    boot = [mean(rng.choices(values, k=len(values))) for _ in range(draws)]
    observed = abs(mean(values))
    if len(values) <= 16:
        distribution = (abs(mean(v*s for v, s in zip(values, signs)))
                        for signs in product((-1, 1), repeat=len(values)))
        p = sum(v >= observed-1e-12 for v in distribution)/(2**len(values))
        method = "exact paired sign-flip on case means"
    else:
        hits = sum(abs(mean(v*rng.choice((-1, 1)) for v in values)) >= observed-1e-12 for _ in range(draws))
        p = (hits+1)/(draws+1)
        method = "Monte Carlo paired sign-flip on case means"
    return {"n_cases": len(values), "mean_difference": mean(values),
            "ci95": [quantile(boot, .025), quantile(boot, .975)],
            "ci_method": "percentile bootstrap of paired case means; seeds remain within case",
            "p_value": p, "test": method, "draws": draws, "random_seed": random_seed,
            "interpretation": "Secondary outcomes and multiple comparisons are exploratory; no automatic superiority claim."}


def summarize(rows, metric, *, seeds=(11, 22, 33), expected_cases=None, conditions=("baseline", "treatment"), draws=20000):
    index = {}
    for r in rows:
        key = r["condition"], r["case_id"], r["seed"]
        if key in index:
            raise ValueError("Duplicate condition/case/seed")
        index[key] = r
    cases = sorted(set(r["case_id"] for r in rows)) if expected_cases is None else sorted(expected_cases)
    expected = {(k, c, s) for k in conditions for c in cases for s in seeds}
    if set(index) != expected:
        raise ValueError("Incomplete, extra or mismatched comparison grid")
    result = {"metric": metric, "conditions": {}}
    case_means = {}
    for condition in conditions:
        values = [index[condition, case, seed][metric] for case in cases for seed in seeds]
        if any(type(v) not in (int, float) for v in values):
            raise ValueError("Missing metric observations must be reported separately")
        seed_means = {str(seed): mean(index[condition, c, seed][metric] for c in cases) for seed in seeds}
        case_means[condition] = {c: mean(index[condition, c, s][metric] for s in seeds) for c in cases}
        result["conditions"][condition] = {"n_runs": len(values), "n_cases": len(cases),
            "mean": mean(values), "sd_across_runs": stdev(values) if len(values)>1 else 0,
            "seed_means": seed_means, "sd_across_seed_means": stdev(seed_means.values()) if len(seeds)>1 else 0}
        if metric in ("IFR", "constraint_pass"):
            result["conditions"][condition]["pass3"] = mean(
                all(index[condition, c, s][metric] == 100 for s in seeds) for c in cases) if len(seeds)==3 else None
    if len(conditions) == 2 and len(cases)>=2:
        a, b = conditions
        result["paired_second_minus_first"] = paired_inference(
            [case_means[b][c]-case_means[a][c] for c in cases], draws=draws)
    return result
