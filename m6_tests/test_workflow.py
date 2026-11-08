from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx

from m5eval.evaluate import ROOT
from m5eval.experiment import golden_cases
from m5eval.generation import GeminiBackend, RequestBudgetExceeded, build_prompt
from m6planner.analysis import comparison, export_comparison
from m6planner.experiment import PairedExperiment
from m6planner.mock_service import FakeClock, MockService, response_body, tool_response
from m6planner.policy import Pacer, Policy, retry_delay
from m6planner.workflow import ControlledBackend, MessageError, decode_message, generate_condition


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.case = golden_cases()[0]
        self.clock = FakeClock()
        self.service = MockService(self.clock)
        self.guard = patch("socket.create_connection", side_effect=AssertionError("No real network allowed"))
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def backend(self, handler=None, cap=60):
        raw = GeminiBackend("offline-test-key", allow_live=True, max_http_requests=cap,
                            mock_transport=httpx.MockTransport(handler or self.service))
        controlled = ControlledBackend(raw, pacer=Pacer(clock=self.clock.clock, sleep=self.clock.sleep))
        self.addCleanup(controlled.close)
        return controlled

    def run_condition(self, condition="treatment", backend=None):
        return generate_condition(self.case, 11, condition, backend or self.backend(), ROOT / "data", lambda e: None,
                                  clock=self.clock.clock, sleep=self.clock.sleep)

    def test_real_pinned_sdk_runs_four_stages_and_tools_with_shared_pacing(self):
        g = self.run_condition()
        self.assertTrue(g["generation_success"])
        self.assertEqual(g["http_requests"], 6)
        self.assertEqual([e["stage"] for e in g["trace"] if e["kind"] == "agent_started"],
                         ["coordinator_dispatch", "activities", "budget", "coordinator_final"])
        self.assertEqual(set(g["tool_calls"]), {"find_activities", "find_restaurants", "find_hotels"})
        self.assertEqual(len(g["executed_tool_calls"]), 3)
        self.assertEqual(len(self.clock.waits), 5)
        self.assertAlmostEqual(g["timing"]["system_wall_ms"], 60050, places=4)
        self.assertEqual(g["usage"]["observed_tokens"]["totalTokenCount"], 90)
        self.assertIsNone(g["usage"]["actual_cost_usd"])
        self.assertNotIn("offline-test-key", json.dumps(g))
        self.assertTrue(all(r["generationConfig"]["seed"] == 11 and r["generationConfig"]["temperature"] == 0 for r in self.service.calls))

    def test_baseline_prompt_is_unchanged_and_pacer_survives_condition_switch(self):
        backend = self.backend()
        a = self.run_condition("baseline", backend)
        b = self.run_condition("treatment", backend)
        self.assertEqual(self.service.calls[0]["contents"][0]["parts"][0]["text"], build_prompt(self.case))
        self.assertEqual(a["http_requests"], 2)
        self.assertEqual(b["http_requests"], 6)
        self.assertEqual(len(self.clock.waits), 7)
        self.assertEqual(backend.request_count, 8)

    def test_malformed_dispatch_stops_without_specialists_or_retry(self):
        g = self.run_condition(backend=self.backend(lambda r: httpx.Response(200, json=response_body({"type": "dispatch"}))))
        self.assertFalse(g["generation_success"])
        self.assertEqual(g["http_requests"], 1)
        self.assertEqual(len(g["attempts"]), 1)
        self.assertEqual(g["generation_error"]["type"], "MessageError")

    def test_structural_invalidity_is_scored_without_repair(self):
        trip = deepcopy(self.service.itinerary(self.case))
        trip["days"][0]["activities"][1] = trip["days"][0]["activities"][0]
        g = self.run_condition("baseline", self.backend(lambda r: httpx.Response(200, json=response_body(trip))))
        self.assertTrue(g["generation_success"])
        self.assertEqual(g["http_requests"], 1)
        from m5eval.scoring import load_datasets, score_itinerary
        self.assertEqual(score_itinerary(g["itinerary"], self.case, load_datasets(ROOT / "data"))["IFR"], 0)

    def test_final_parse_failure_no_retry(self):
        body = response_body(None)
        body["candidates"][0]["content"]["parts"][0]["text"] = "unexpected prefix {}"
        g = self.run_condition("baseline", self.backend(lambda r: httpx.Response(200, json=body)))
        self.assertFalse(g["generation_success"])
        self.assertEqual(g["raw_text"], "unexpected prefix {}")
        self.assertEqual(len(g["attempts"]), 1)

    def test_retry_discards_earlier_attempt_rtc_but_retains_usage_and_journal(self):
        calls = []
        def handler(request):
            calls.append(request)
            if len(calls) == 1:
                return httpx.Response(200, json=tool_response(self.case, ["find_activities", "find_restaurants", "find_hotels"]))
            if len(calls) == 2:
                return httpx.Response(503, headers={"Retry-After": "20"}, json={"error": {"code": 503, "message": "busy", "status": "UNAVAILABLE"}})
            return httpx.Response(200, json=response_body(self.service.itinerary(self.case)))
        g = self.run_condition("baseline", self.backend(handler))
        self.assertTrue(g["generation_success"])
        self.assertEqual(g["tool_calls"], [])
        self.assertEqual(len(g["all_attempt_tool_calls"]), 3)
        self.assertEqual(len(g["attempts"]), 2)
        self.assertEqual(g["usage"]["observed_tokens"]["totalTokenCount"], 30)
        self.assertTrue(any(e["kind"] == "retry_wait" and e["requested_ms"] == 20000 for e in g["trace"]))

    def test_team_retry_restarts_coordinator_and_clears_message_state(self):
        count = 0
        def handler(request):
            nonlocal count
            count += 1
            if count == 2:
                return httpx.Response(503, json={"error": {"code": 503, "message": "busy", "status": "UNAVAILABLE"}})
            return self.service(request)
        g = self.run_condition(backend=self.backend(handler))
        dispatches = [e for e in g["trace"] if e["kind"] == "agent_started" and e["stage"] == "coordinator_dispatch"]
        self.assertEqual(len(dispatches), 2)
        self.assertIn('"messages": {}', dispatches[1]["prompt"])
        self.assertTrue(g["generation_success"])
        self.assertEqual(len(g["attempts"]), 2)

    def test_provider_retries_three_only_and_404_never_retries(self):
        for code in (503, 404):
            with self.subTest(code=code):
                g = self.run_condition("baseline", self.backend(lambda r: httpx.Response(code, json={"error": {"code": code, "message": "failure"}})))
                self.assertEqual(len(g["attempts"]), 3 if code == 503 else 1)
                self.assertFalse(g["generation_success"])

    def test_automatic_tool_followups_obey_specialist_cap(self):
        def handler(request):
            if not self.service.calls:
                return self.service(request)
            return httpx.Response(200, json=tool_response(self.case, ["find_activities"]))
        g = self.run_condition(backend=self.backend(handler))
        requests = [e for e in g["trace"] if e["kind"] == "http_request"]
        self.assertEqual(sum(e["stage"] == "activities" for e in requests), 4)
        self.assertFalse(g["generation_success"])
        self.assertLessEqual(g["http_requests"], 5)

    def test_shared_attempt_cap_holds_for_baseline_followups(self):
        g = self.run_condition("baseline", self.backend(lambda r: httpx.Response(200, json=tool_response(self.case, ["find_activities"]))))
        self.assertLessEqual(g["http_requests"], 10)
        self.assertFalse(g["generation_success"])
        self.assertEqual(len(g["attempts"]), 1)

    def test_session_reservation_is_checked_before_any_http(self):
        b = self.backend(cap=29)
        with self.assertRaises(RequestBudgetExceeded):
            self.run_condition(backend=b)
        self.assertEqual(b.request_count, 0)

    def test_typed_messages_reject_duplicate_keys_nonfinite_and_boolean_days(self):
        for text in ('{"type":"dispatch","type":"dispatch","activity_task":"x","budget_task":"y"}',
                     '{"type":"activities","days":[{"day":true,"activities":[]}],"notes":""}',
                     '{"type":"activities","days":[],"notes":NaN}'):
            with self.assertRaises(MessageError):
                decode_message(text, "activities" if "activities" in text else "dispatch")

    def test_retry_after_date_body_and_nonfinite(self):
        now = datetime(2026, 11, 8, tzinfo=timezone.utc)
        self.assertEqual(retry_delay([{"kind": "http_response", "retry_after": "Sun, 08 Nov 2026 00:00:25 GMT"}], 1, now=now), 25)
        self.assertEqual(retry_delay([{"kind": "http_response", "retry_after": "inf", "body": {"error": {"details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "30s"}]}}}], 1), 30)

    def test_frozen_policy_validation_and_live_gate(self):
        with self.assertRaises(ValueError):
            Policy(temperature=1)
        with self.assertRaises(ValueError):
            Policy(temperature=False)
        with self.assertRaises(PermissionError):
            GeminiBackend("offline-test-key")

    def test_pair_storage_resume_counterbalance_and_mock_comparison(self):
        with TemporaryDirectory() as directory:
            exp = PairedExperiment(directory, "sdk-validation", self.backend(), cases=[self.case], seeds=[11], study_kind="validation")
            records = exp.run_batch(max_new_records=2, clock=self.clock.clock, sleep=self.clock.sleep)
            self.assertEqual(len(records), 2)
            before = len(self.service.calls)
            self.assertEqual(exp.run_batch(max_new_records=2), [])
            self.assertEqual(len(self.service.calls), before)
            summary = export_comparison(exp.root)
            self.assertFalse(summary["is_formal_experimental_evidence"])
            self.assertEqual(summary["conditions"]["treatment"]["records"], 1)
            self.assertIsNone(summary["conditions"]["baseline"]["actual_cost_usd"])
            self.assertEqual(export_comparison(exp.root), summary)
            exp2 = PairedExperiment(directory, "order", self.backend(), cases=golden_cases()[:2], seeds=[11])
            self.assertEqual([k for c, s, k in exp2.schedule()], ["baseline", "treatment", "treatment", "baseline"])

    def test_incomplete_cohort_and_altered_journal_are_rejected(self):
        with TemporaryDirectory() as directory:
            exp = PairedExperiment(directory, "partial", self.backend(), cases=[self.case], seeds=[11])
            exp.run_batch(max_new_records=1, clock=self.clock.clock, sleep=self.clock.sleep)
            with self.assertRaises(ValueError):
                comparison(exp.root)
            folder = exp.folder(self.case, 11, "baseline")
            (folder / "events.jsonl").write_text("")
            with self.assertRaises(ValueError):
                exp.read_record(self.case, 11, "baseline")

    def test_interrupted_runs_changed_inputs_and_protected_outputs_rejected(self):
        with TemporaryDirectory() as directory:
            exp = PairedExperiment(directory, "incomplete", self.backend(), cases=[self.case], seeds=[11])
            exp.folder(self.case, 11, "baseline").mkdir()
            with self.assertRaises(ValueError):
                exp.run_record(self.case, 11, "baseline")
            changed = deepcopy(self.case)
            changed["budget_level"] = "High" if changed["budget_level"] != "High" else "Low"
            with self.assertRaises(ValueError):
                PairedExperiment(directory, "changed", self.backend(), cases=[changed], seeds=[11])
            with self.assertRaises(ValueError):
                PairedExperiment(directory, "incomplete", self.backend(), cases=[self.case], seeds=[22])
        with self.assertRaises(ValueError):
            PairedExperiment(ROOT / "source", "bad", self.backend(), cases=[self.case], seeds=[11])
        with self.assertRaises(ValueError):
            PairedExperiment(ROOT / "m6_runs", "bad", self.backend(), cases=[self.case], seeds=[11], study_kind="formal")


if __name__ == "__main__":
    unittest.main()
