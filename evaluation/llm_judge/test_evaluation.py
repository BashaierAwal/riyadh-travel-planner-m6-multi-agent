"""Offline checks; no provider SDK or model calls required."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('m6judge', Path(__file__).with_name('evaluate.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def output():
    return {'scores': {c: 4 for c in module.CRITERIA},
            'reasons': {c: 'Supported by supplied evidence.' for c in module.CRITERIA},
            'limitations': ['Opening hours unknown.']}


class JudgeTests(unittest.TestCase):
    def test_real_grid_and_blinding(self):
        items, fingerprint = module.prepare()
        self.assertEqual(len(items), 120)
        self.assertEqual(sum(x['prompt'] is not None for x in items), 114)
        for item in items:
            if item['prompt']:
                self.assertNotIn(item['run_id'], item['prompt'])
                self.assertNotIn('"condition"', item['prompt'])
        self.assertEqual(len(fingerprint), 64)

    def test_invalid_scores_rejected(self):
        for bad in (True, 0, 6, 4.5):
            data = output()
            data['scores']['personalization'] = bad
            with self.assertRaises(ValueError):
                module.validate(data)

    def test_cap_resume_and_failure_denominators(self):
        items = [{'run_id': c + '_G01_seed11', 'condition': c, 'case_id': 'G01',
                  'seed': 11, 'prompt': 'case', 'status': 'eligible'} for c in ('baseline', 'treatment')]
        items.append({'run_id': 'treatment_G02_seed11', 'condition': 'treatment',
                      'case_id': 'G02', 'seed': 11, 'prompt': None, 'status': 'generation_failed'})
        calls = []
        def provider(prompt):
            calls.append(prompt)
            return {'usage_metadata': {'total_token_count': 30}}, json.dumps(output())
        with tempfile.TemporaryDirectory() as temp, patch.object(module.time, 'sleep'):
            path = Path(temp)
            module.run(items, 'fixed', path, 'test-model', 1, True, provider)
            self.assertEqual(len(calls), 1)
            module.run(items, 'fixed', path, 'test-model', 1, True, provider)
            self.assertEqual(len(calls), 2)
            module.run(items, 'fixed', path, 'test-model', 1, True, provider)
            self.assertEqual(len(calls), 2)
            summary = module.read(path / 'summary.json')
            self.assertEqual(summary['conditions']['treatment']['generation_failed'], 1)
            self.assertEqual(summary['paired_complete_outputs']['pairs'], 1)
            with self.assertRaises(ValueError):
                module.run(items, 'changed', path, 'test-model', 1, True, provider)

    def test_error_retained_and_no_automatic_retry(self):
        item = {'run_id': 'baseline_G01_seed11', 'condition': 'baseline',
                'case_id': 'G01', 'seed': 11, 'prompt': 'case'}
        calls = []
        def provider(prompt):
            calls.append(prompt)
            raise RuntimeError('not saved')
        with tempfile.TemporaryDirectory() as temp, patch.object(module.time, 'sleep'):
            for _ in range(2):
                module.run([item], 'fixed', Path(temp), 'test-model', 1, True, provider)
            self.assertEqual(len(calls), 1)
            self.assertEqual(module.read(Path(temp) / 'results.json')[item['run_id']]['status'], 'judge_error')

    def test_live_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                module.run([], 'fixed', Path(temp), 'test-model', 1, False)


if __name__ == '__main__':
    unittest.main()
