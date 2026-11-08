import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from m5eval.generation import GeminiBackend
from m6planner.mock_service import FakeClock, MockService
from m6planner.policy import Pacer
from m6planner.workflow import ControlledBackend

MODULE = Path(__file__).resolve().parents[1] / "scripts/M6_Run_Persistent.py"
spec = importlib.util.spec_from_file_location("persistent_control", MODULE)
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class PersistentStorageTests(unittest.TestCase):
    def test_unapproved_and_unmounted_paths_stop_before_client_creation(self):
        with TemporaryDirectory() as p, patch('m5eval.generation.GeminiBackend', side_effect=AssertionError('No client allowed')):
            with self.assertRaises(PermissionError):
                control.run_persistent_batch(p)
            with self.assertRaises(ValueError):
                control.run_persistent_batch(p, approved=True)

    def test_six_mock_records_are_in_external_destination_and_checkpoint(self):
        import httpx
        clock = FakeClock()
        service = MockService(clock)
        with TemporaryDirectory() as p, patch('socket.create_connection', side_effect=AssertionError('No network allowed')):
            raw = GeminiBackend('offline-test-key', allow_live=True, max_http_requests=180,
                                mock_transport=httpx.MockTransport(service))
            backend = ControlledBackend(raw, pacer=Pacer(clock=clock.clock, sleep=clock.sleep))
            destination = Path(p) / 'persistent/experiments'
            state = control.run_persistent_batch(destination, approved=True, backend=backend)
            self.assertEqual(state['records'], 6)
            self.assertEqual(state['http_requests'], 24)
            self.assertEqual(len(list((destination / 'formal-v2').glob('*/events.jsonl'))), 6)
            with zipfile.ZipFile(state['checkpoint']) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(sum(n.endswith('/record.json') for n in z.namelist()), 6)
