"""Independently check saved judge outputs and arithmetic; no network requests."""
import argparse
import importlib.util
import json
from pathlib import Path
import statistics

CRITERIA = ('personalization', 'budget_alignment', 'itinerary_coherence', 'itinerary_feasibility')
ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify(directory):
    source = {read(p)['run_id']: read(p) for p in (ROOT / 'm6_runs/formal-v3').glob('*/record.json')}
    if len(source) != 120:
        raise ValueError('Expected 120 original M6 records')
    spec = importlib.util.spec_from_file_location('frozen_judge', Path(__file__).with_name('evaluate.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prepared, fingerprint = module.prepare()
    prompts = {x['run_id']: x['prompt'] for x in prepared}
    results = read(directory / 'results.json')
    if set(results) != set(source):
        raise ValueError('Judge coverage differs from original cohort')
    manifest = read(directory / 'manifest.json')
    policy = read(directory / 'execution_policy.json')
    if manifest['input_fingerprint'] != fingerprint:
        raise ValueError('Current input/rubric fingerprint differs')
    if manifest['judge_model'] != policy['judge_model'] or manifest['input_fingerprint'] != policy['input_fingerprint']:
        raise ValueError('Conflicting judge configuration')
    if manifest['temperature'] != 0 or manifest['max_output_tokens'] != 1600:
        raise ValueError('Unexpected judge settings')
    # The frozen evaluation implementation/rubric must remain identical.
    for name in ('evaluate.py', 'rubric.json'):
        if (directory / 'source_snapshot' / name).read_bytes() != (Path(__file__).parent / name).read_bytes():
            raise ValueError('Frozen source snapshot differs')
    graded = {}
    observed_usage = {'prompt_token_count': 0, 'candidates_token_count': 0, 'total_token_count': 0}
    for rid, original in source.items():
        result = results[rid]
        if original['generation_result'].get('itinerary') is None:
            if result != {'status': 'generation_failed'}:
                raise ValueError('Generation failure incorrectly graded')
            continue
        if result['status'] != 'judged':
            raise ValueError('Readable plan lacks a validated judgement: ' + rid)
        request = read(directory / rid / 'request.json')
        if request['model'] != manifest['judge_model'] or request['temperature'] != 0:
            raise ValueError('Mixed model or temperature')
        if request['prompt'] != prompts[rid]:
            raise ValueError('Prompt or dataset evidence differs from frozen preparation')
        if rid in request['prompt'] or '"condition"' in request['prompt']:
            raise ValueError('Explicit architecture label in judge input')
        payload = json.loads(request['prompt'].split('\nCASE:\n', 1)[1])
        expected_input = {k: original['user_input'][k] for k in ('trip_duration', 'interests', 'budget_level')}
        if payload['request'] != expected_input or payload['itinerary'] != original['generation_result']['itinerary']:
            raise ValueError('Judge input differs from saved plan')
        response = read(directory / rid / 'response.json')
        text = ''.join(p.get('text', '') for p in response['candidates'][0]['content']['parts'] if not p.get('thought'))
        output = json.loads(text)
        if output != result['output']:
            raise ValueError('Saved grades differ from provider response')
        if set(output['scores']) != set(CRITERIA) or set(output['reasons']) != set(CRITERIA):
            raise ValueError('Wrong rubric criteria')
        for criterion in CRITERIA:
            score = output['scores'][criterion]
            if type(score) is not int or not 1 <= score <= 5 or not output['reasons'][criterion].strip():
                raise ValueError('Invalid score or reason')
        graded[rid] = sum(output['scores'].values()) / 4
        usage = response.get('usage_metadata') or {}
        for field in observed_usage:
            observed_usage[field] += usage.get(field) or 0
    receipts = [read(p) for p in sorted((directory / 'http_attempts').glob('*.json'))]
    if [r['request_number'] for r in receipts] != list(range(1, len(receipts) + 1)):
        raise ValueError('HTTP journal is not contiguous')
    success = [r['run_id'] for r in receipts if r['status'] == 'response_received']
    if sorted(success) != sorted(graded) or len(receipts) > policy['http_cap']:
        raise ValueError('HTTP evidence coverage/cap mismatch')
    if len(receipts) + policy['previous_attempt_requests'] > policy['combined_cap']:
        raise ValueError('Combined request cap exceeded')
    for rid in graded:
        attempts = [r for r in receipts if r['run_id'] == rid]
        if not 1 <= len(attempts) <= policy['max_attempts_per_plan']:
            raise ValueError('Per-plan retry cap exceeded')
        if [r['attempt'] for r in attempts] != list(range(1, len(attempts) + 1)) or attempts[-1]['status'] != 'response_received':
            raise ValueError('Inconsistent per-plan request history')
    failures = [r for r in receipts if r['status'] != 'response_received']
    if any(r['status'] != 'provider_error' or r['provider_code'] not in policy['retry_codes'] for r in failures):
        raise ValueError('Unresolved or unapproved provider failure')
    summary = read(directory / 'summary.json')
    if summary['status'] != 'complete':
        raise ValueError('Summary is not marked complete')
    conditions = {}
    for condition in ('baseline', 'treatment'):
        values = [v for rid, v in graded.items() if rid.startswith(condition + '_')]
        means = {c: statistics.mean(results[rid]['output']['scores'][c] for rid in graded if rid.startswith(condition + '_')) for c in CRITERIA}
        actual = summary['conditions'][condition]
        for field, value in [('overall_mean', statistics.mean(values)), ('overall_sample_sd', statistics.stdev(values))]:
            if abs(actual[field] - value) > 1e-10:
                raise ValueError('Judge summary arithmetic mismatch')
        if actual['criterion_means'] != means or actual['judged'] != len(values):
            raise ValueError('Criterion arithmetic/count mismatch')
        conditions[condition] = actual
    differences = []
    for rid in graded:
        if rid.startswith('baseline_'):
            other = rid.replace('baseline_', 'treatment_', 1)
            if other in graded:
                differences.append(graded[other] - graded[rid])
    pair = summary['paired_complete_outputs']
    if pair['pairs'] != len(differences) or abs(pair['mean_treatment_minus_baseline'] - statistics.mean(differences)) > 1e-10:
        raise ValueError('Paired arithmetic mismatch')
    return {'status': 'PASS_SAVED_JUDGE_EVIDENCE', 'original_records': len(source), 'judged': len(graded),
            'http_requests': len(receipts), 'temporary_provider_errors': len(failures),
            'conditions': conditions, 'paired_complete_outputs': pair, 'observed_usage': observed_usage,
            'scope': 'Saved response integrity, input identity and independent arithmetic; no provider attestation or human calibration'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), ensure_ascii=False, indent=2))
