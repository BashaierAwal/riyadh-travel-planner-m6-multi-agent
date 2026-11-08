"""Read-only independent M6 saved-evidence audit. No model SDK or network."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {'find_activities', 'find_restaurants', 'find_hotels'}
METRICS = ('APM', 'RBM', 'HBM', 'IFR', 'RTC')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def loads(text):
    return json.loads(text, object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scores(trip, case, data):
    result = dict.fromkeys(METRICS[:-1], 0.0)
    if not isinstance(trip, dict):
        return result
    days = trip.get('days')
    days = days if isinstance(days, list) else []
    count = {'activities': 0, 'restaurants': 0}
    seen = set()
    for day in days[:case['trip_duration']]:
        if not isinstance(day, dict):
            continue
        for field in count:
            ids = day.get(field)
            for pid in (ids[:2] if isinstance(ids, list) else []):
                if not isinstance(pid, str):
                    continue
                if field == 'activities':
                    if pid in seen:
                        continue
                    seen.add(pid)
                row = data[field].get(pid)
                if row:
                    count[field] += (row['interest_group'] in case['interests'] if field == 'activities'
                                     else row['budget_level'] == case['budget_level'])
    hotel = trip.get('hotel_id')
    row = data['hotels'].get(hotel) if isinstance(hotel, str) else None
    result.update(APM=round(100*count['activities']/(2*case['trip_duration']), 2),
                  RBM=round(100*count['restaurants']/(2*case['trip_duration']), 2),
                  HBM=100.0 if row and row['budget_level'] == case['budget_level'] else 0.0)
    valid = bool(row) and isinstance(trip.get('days'), list) and len(days) == case['trip_duration']
    acts = []
    for index, day in enumerate(days, 1):
        if not isinstance(day, dict):
            valid = False
            continue
        valid &= type(day.get('day')) is int and day['day'] == index
        for field in count:
            ids = day.get(field)
            if not isinstance(ids, list):
                valid = False
                continue
            valid &= len(ids) == 2 and all(isinstance(i, str) and i in data[field] for i in ids)
            if field == 'activities':
                acts.extend(i for i in ids if isinstance(i, str))
    valid &= len(acts) == len(set(acts))
    result['IFR'] = 100.0 if valid else 0.0
    return result


def audit(directory):
    directory = Path(directory).resolve()
    manifest = loads((directory/'manifest.json').read_text())
    ident = manifest['identity']
    hashed = hashlib.sha256(json.dumps(ident, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    require(hashed == manifest['identity_sha256'], 'Manifest fingerprint mismatch')
    for relative, expected in ident['source_sha256'].items():
        path = (ROOT/relative).resolve()
        require(ROOT in path.parents and digest(path) == expected, 'Source mismatch: '+relative)
    data = {}
    for name, expected in ident['dataset_sha256'].items():
        path = ROOT/'data'/f'{name}.csv'
        require(digest(path) == expected, 'Dataset mismatch: '+name)
        with path.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        data[name] = {r['place_id']: r for r in rows}
        require(len(data[name]) == len(rows), 'Duplicate data IDs')
    expected = {(condition, c['case_id'], seed): c for condition in ('baseline', 'treatment')
                for c in ident['cases'] for seed in ident['seeds']}
    found, groups = set(), {'baseline': [], 'treatment': []}
    for folder in sorted(directory.iterdir()):
        if not folder.is_dir() or folder.name == 'analysis':
            continue
        require((folder/'record.json').is_file(), 'Incomplete record: '+folder.name)
        require(digest(folder/'record.json') == (folder/'record.sha256').read_text().strip(), 'Record checksum mismatch')
        record = loads((folder/'record.json').read_text())
        generation, meta = record['generation_result'], record['metadata']
        key = (meta['condition'], record['case_id'], record['seed'])
        require(key in expected and key not in found, 'Unexpected/duplicate record')
        found.add(key)
        require(record['user_input'] == expected[key] and record['experiment_version'] == ident['version'], 'Input/version mismatch')
        require(meta['experiment_identity_sha256'] == hashed and meta['evidence_mode'] == ident['evidence_mode'], 'Record identity mismatch')
        trace = [loads(s) for s in (folder/'events.jsonl').read_text().splitlines()]
        require(trace == generation['trace'], 'Journal mismatch')
        require([e['event_number'] for e in trace] == list(range(1, len(trace)+1)), 'Event numbering')
        result = scores(generation['itinerary'], expected[key], data)
        for metric, value in result.items():
            require(value == record['evaluation'][metric], 'Score mismatch '+metric)
        final = generation['attempts'][-1]['number']
        calls = []
        for e in trace:
            if e['kind'] == 'http_response' and e['attempt'] == final:
                body = e.get('body')
                for candidate in (body.get('candidates', [])[:1] if isinstance(body, dict) else []):
                    calls.extend(p['functionCall']['name'] for p in candidate.get('content', {}).get('parts', [])
                                 if isinstance(p.get('functionCall'), dict) and isinstance(p['functionCall'].get('name'), str))
        require(calls == generation['tool_calls'], 'Final-attempt requested names mismatch')
        result['RTC'] = round(100*len(set(calls)&TOOLS)/3, 2)
        require(result['RTC'] == record['RTC'], 'RTC mismatch')
        requests = [e for e in trace if e['kind'] == 'http_request']
        require(len(requests) == generation['http_requests'] <= 30, 'Record request cap/count')
        for attempt in generation['attempts']:
            require(sum(e['attempt'] == attempt['number'] for e in requests) <= 10, 'Attempt request cap')
        for stage, cap in {'coordinator_dispatch': 1, 'activities': 4, 'budget': 4, 'coordinator_final': 1}.items():
            for attempt in generation['attempts']:
                require(sum(e['stage'] == stage and e['attempt'] == attempt['number'] for e in requests) <= cap, 'Stage cap')
        timing = generation['timing']
        require(all(type(timing[k]) in (int, float) and math.isfinite(timing[k]) and timing[k] >= 0
                    for k in ('system_wall_ms', 'pacing_wait_ms', 'retry_wait_ms', 'processing_ms')), 'Invalid timing')
        require(abs(timing['system_wall_ms']-timing['processing_ms']-timing['pacing_wait_ms']-timing['retry_wait_ms']) < 1, 'Timing decomposition')
        usages = [e['body']['usageMetadata'] for e in trace if e['kind']=='http_response'
                  and isinstance(e.get('body'), dict) and isinstance(e['body'].get('usageMetadata'), dict)]
        for name, saved in generation['usage']['observed_tokens'].items():
            vals = [u[name] for u in usages if type(u.get(name)) is int and u[name] >= 0]
            require(saved == (sum(vals) if vals else None), 'Token aggregation mismatch')
        require(not generation['generation_success'] or isinstance(generation['itinerary'], dict), 'Missing successful itinerary')
        groups[key[0]].append(result)
    require(found == set(expected), 'Partial cohort: no complete comparison')
    result = {'status': 'PASS_SAVED_EVIDENCE', 'scope': 'Integrity and independent arithmetic; no provider attestation',
            'evidence_mode': ident['evidence_mode'], 'records': len(found),
            'conditions': {name: {k: {'mean': mean(r[k] for r in rows),
                                      'sample_sd': stdev(r[k] for r in rows) if len(rows)>1 else None}
                                  for k in METRICS} for name, rows in groups.items()}}
    comparison_file = directory/'analysis'/'M6_Comparison.json'
    if comparison_file.is_file():
        saved = loads(comparison_file.read_text())
        for condition, metrics in result['conditions'].items():
            for metric, stats in metrics.items():
                actual = saved['conditions'][condition]['metrics'][metric]
                sd = actual['across_runs']['sample_sd'] if 'across_runs' in actual else actual['sample_sd']
                require(abs(actual['mean']-stats['mean']) < 1e-9, 'Comparison mean mismatch')
                require(sd == stats['sample_sd'] or (sd is not None and stats['sample_sd'] is not None
                        and abs(sd-stats['sample_sd']) < 1e-9), 'Comparison SD mismatch')
        result['saved_comparison_verified'] = True
    else:
        result['saved_comparison_verified'] = False
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    args = parser.parse_args()
    print(json.dumps(audit(args.directory), indent=2, ensure_ascii=False, allow_nan=False))
