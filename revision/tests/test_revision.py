import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from m5eval.scoring import load_datasets, score_itinerary
from revision.constraints import check_plan, coordinates, distance, validate_constraints
from revision.provider import BudgetError, Gemini, clean_json
from revision.run import Experiment, ROOT, digest, file_hash
from revision.statistics import paired_inference, summarize
from revision.tools import Tools
from revision.workflow import run_workflow
from revision.verify import audit, export
from revision.cost import estimate_events
from revision.compare import compare


class GeometryAndScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_datasets(ROOT / "data")
        cls.cases = json.loads((ROOT / "revision/cases/hard.json").read_text())
        cls.proofs = json.loads((ROOT / "revision/cases/feasibility_witnesses.json").read_text())

    def test_known_equatorial_distance_and_antipode(self):
        self.assertAlmostEqual(distance((0,0),(0,1)), 111.1950802335, places=6)
        self.assertAlmostEqual(distance((0,0),(0,180)), math.pi*6371.0088, places=6)
        self.assertEqual(distance((24,46),(24,46)), 0)

    def test_all_20_cases_have_independently_checked_feasible_routes(self):
        self.assertEqual(len(self.cases),20)
        for case, proof in zip(self.cases,self.proofs):
            checked = check_plan(proof["witness"],case,self.data)
            self.assertTrue(checked["passed"],(case["case_id"],checked))
            plan = proof["witness"]
            hp = coordinates(self.data["hotels"][plan["hotel_id"]])
            for day, route in zip(plan["days"],checked["routes"]):
                a,b = [coordinates(self.data["activities"][p]) for p in day["activities"]]
                r,s = [coordinates(self.data["restaurants"][p]) for p in day["restaurants"]]
                # Independent spherical cosine formula, not the production haversine.
                total = 0
                for x,y in zip([hp,a,r,b,s],[a,r,b,s,hp]):
                    u,v = map(math.radians,x)
                    w,z = map(math.radians,y)
                    total += 6371.0088*math.acos(min(1,max(-1,math.sin(u)*math.sin(w)+math.cos(u)*math.cos(w)*math.cos(v-z))))
                self.assertAlmostEqual(total,route["km"],places=5)

    def sample(self):
        return copy.deepcopy(self.cases[0]),copy.deepcopy(self.proofs[0]["witness"])

    def test_cost_uses_explicit_nights_and_exact_boundary(self):
        case,plan = self.sample()
        nightly=float(self.data["hotels"][plan["hotel_id"]]["median_price"])
        case["constraints"]["hotel_cap_sar"]=nightly
        self.assertTrue(check_plan(plan,case,self.data)["passed"])
        case["constraints"]["hotel_cap_sar"]=nightly-.01
        self.assertIn("budget",[v["kind"] for v in check_plan(plan,case,self.data)["violations"]])

    def test_missing_coordinates_do_not_pass_as_zero_distance(self):
        case,plan=self.sample()
        data=copy.deepcopy(self.data)
        data["hotels"][plan["hotel_id"]]["latitude"]="NaN"
        result=check_plan(plan,case,data)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checkable"])
        self.assertIsNone(result["routes"][0]["km"])

    def test_repeated_interest_activity_counts_once(self):
        case,plan=self.sample()
        plan["days"][0]["activities"][1]=plan["days"][0]["activities"][0]
        kinds={v["kind"] for v in check_plan(plan,case,self.data)["violations"]}
        self.assertTrue({"preference","repeated_place"}<=kinds)

    def test_invented_id_and_distance_failure(self):
        case,plan=self.sample()
        plan["days"][0]["activities"][0]="ACT_INVENTED"
        result=check_plan(plan,case,self.data)
        self.assertFalse(result["passed"])
        self.assertTrue(any(v["kind"]=="invented_place" for v in result["violations"]))
        case,plan=self.sample()
        case["constraints"]["max_km_per_day"]=.001
        self.assertTrue(any(v["kind"]=="distance" for v in check_plan(plan,case,self.data)["violations"]))

    def test_missing_output_is_a_failure_without_changing_original_ifr(self):
        case,plan=self.sample()
        self.assertFalse(check_plan(None,case,self.data)["passed"])
        case["constraints"]["max_km_per_day"]=.001
        self.assertEqual(score_itinerary(plan,case,self.data)["IFR"],100)
        self.assertFalse(check_plan(plan,case,self.data)["passed"])

    def test_reject_invalid_case_and_json(self):
        case,_=self.sample()
        for bad in (True,float("nan"),-1):
            case["constraints"]["hotel_cap_sar"]=bad
            with self.assertRaises(ValueError):validate_constraints(case,self.data)
        for raw in ('{"x":1,"x":2}','{"x":NaN}','[]','garbage'):
            self.assertIsNone(clean_json(raw))

    def test_tools_expose_coordinates_and_track_returned_ids(self):
        case,plan=self.sample()
        tools=Tools(self.data,case,lambda e:None)
        hotels=tools.call("find_hotels",{"budget_level":"Low","limit":100})
        self.assertIn("latitude",hotels[0])
        self.assertEqual(len(tools.grounding_errors(plan)),4)
        bad=tools.call("find_hotels",{"budget_level":"Low","limit":True})
        self.assertIn("error",bad)

    def test_original_cases_keep_hotels_without_coordinates(self):
        original=json.loads((ROOT/"revision/cases/original.json").read_text())[0]
        tools=Tools(self.data,original,lambda e:None)
        hotels=tools.find_hotels("Low",limit=100)
        expected=sum(r["budget_level"]=="Low" for r in self.data["hotels"].values())
        self.assertEqual(len(hotels),expected)
        self.assertTrue(any(r["latitude"] is None for r in hotels))


class InferenceTests(unittest.TestCase):
    def test_component_removal_comparison_requires_shared_settings(self):
        shared={k:0 for k in ("policy","evidence_mode","temperature","max_repairs","http_per_record","max_output_tokens_per_request",
                            "pacing_seconds","timeout_seconds","retries","dataset_sha256","source_sha256")}
        shared.update(model="test-model",cases=[{"case_id":"G01"},{"case_id":"H01"}],seeds=[11,22,33])
        def rows(condition,value):
            return [{"condition":condition,"case_id":c,"seed":s,"constraint_pass":value,
                     "violation_count":1 if value==0 else 0,"IFR":100,"repair_rounds":0,
                     "tool_calls":3,"system_wall_seconds":1} for c in ("G01","H01") for s in (11,22,33)]
        main={"status":"complete","study":"main","evidence_mode":"fixture","identity":shared,"rows":rows("treatment",100)}
        changed={"status":"complete","study":"ablation","evidence_mode":"fixture","identity":copy.deepcopy(shared),"rows":rows("without_repair",0)}
        with patch("revision.compare.audit",side_effect=[main,changed]):
            result=compare("main","variant","without_repair")
            self.assertEqual(result["statistics"]["combined"]["constraint_pass"]["paired_second_minus_first"]["mean_difference"],-100)
        changed["identity"]["model"]="other-model"
        with patch("revision.compare.audit",side_effect=[main,changed]):
            with self.assertRaises(ValueError):compare("main","variant","without_repair")

    def test_cost_includes_thinking_and_remains_separate_from_billing(self):
        prices=json.loads((ROOT/"revision/PRICING.json").read_text())
        events=[{"kind":"http_request","number":1,"model":"gemini-3.5-flash-lite"},
                {"kind":"http_response","number":1,"status":200,"body":{"usageMetadata":{
                    "promptTokenCount":1000,"candidatesTokenCount":100,"thoughtsTokenCount":200,"totalTokenCount":1300}}}]
        result=estimate_events(events,prices)
        self.assertAlmostEqual(result["estimated_cost_usd"],.00105)
        self.assertIsNone(result["actual_cost_usd"])
        events.append({"kind":"http_request","number":2,"model":"gemini-3.5-flash-lite"})
        result=estimate_events(events,prices)
        self.assertIsNone(result["estimated_cost_usd"])
        self.assertAlmostEqual(result["observed_usage_subtotal_usd"],.00105)

    def test_cost_does_not_invent_missing_thinking_usage(self):
        prices=json.loads((ROOT/"revision/PRICING.json").read_text())
        events=[{"kind":"http_request","number":1,"model":"gemini-3.5-flash-lite"},
                {"kind":"http_response","number":1,"status":200,"body":{"usageMetadata":{
                    "promptTokenCount":1000,"candidatesTokenCount":100,"totalTokenCount":1300}}}]
        self.assertIsNone(estimate_events(events,prices)["estimated_cost_usd"])
    def test_known_sign_flip_probabilities(self):
        zero=paired_inference([0,0,0,0],draws=100)
        self.assertEqual(zero["p_value"],1)
        self.assertEqual(zero["ci95"],[0,0])
        one=paired_inference([1,1,1,1],draws=100)
        self.assertEqual(one["p_value"],.125)
        self.assertEqual(one["ci95"],[1,1])

    def test_grid_checks_and_pass3(self):
        rows=[{"condition":k,"case_id":c,"seed":s,"IFR":100 if k=="baseline" or s!=33 else 0}
              for k in ("baseline","treatment") for c in ("G01","G02") for s in (11,22,33)]
        result=summarize(rows,"IFR",draws=100)
        self.assertEqual(result["conditions"]["baseline"]["pass3"],1)
        self.assertEqual(result["conditions"]["treatment"]["pass3"],0)
        self.assertEqual(result["paired_second_minus_first"]["n_cases"],2)
        with self.assertRaises(ValueError):summarize(rows[:-1],"IFR",draws=100)
        with self.assertRaises(ValueError):summarize(rows+rows[:1],"IFR",draws=100)


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_datasets(ROOT/"data")
        cls.case=json.loads((ROOT/"revision/cases/hard.json").read_text())[0]
        cls.plan=json.loads((ROOT/"revision/cases/feasibility_witnesses.json").read_text())[0]["witness"]

    def backend(self,initial_bad=True):
        case,plan=self.case,self.plan
        class Scripted:
            count=0
            def complete(s,prompt,tools,seed,model,emit,**kwargs):
                s.count+=1
                if "Role: coordinator_dispatch" in prompt:
                    return {"activity_task":"choose", "feasibility_task":"check"}
                # Fixture actions are explicit tool calls, never experimental evidence.
                for day in plan["days"]:
                    for pid in day["activities"]:
                        tools.call("find_activities",{"interests":case["interests"],"limit":1,"center_id":pid})
                    for pid in day["restaurants"]:
                        tools.call("find_restaurants",{"budget_level":case["budget_level"],"limit":1,"center_id":pid})
                tools.call("find_hotels",{"budget_level":case["budget_level"],"limit":100})
                value=copy.deepcopy(plan)
                if initial_bad and "repair" not in prompt.split("Context:")[0]:
                    value["days"][0]["activities"][1]=value["days"][0]["activities"][0]
                return value
        return Scripted()

    def test_single_agent_and_team_repair_then_stop(self):
        for condition in ("baseline","treatment","without_feasibility"):
            events=[]
            result=run_workflow(self.case,11,condition,self.backend(),self.data,"test-model",events.append)
            self.assertTrue(result["success"],result)
            self.assertEqual(result["repair_rounds"],1)
            self.assertEqual(len(result["rounds"]),2)
            self.assertTrue(result["rounds"][1]["fixed_since_previous"])

    def test_no_repair_ablation_retains_initial_failures(self):
        result=run_workflow(self.case,11,"without_repair",self.backend(),self.data,"test-model",lambda e:None)
        self.assertFalse(result["success"])
        self.assertEqual(result["repair_rounds"],0)

    def test_at_most_three_repairs_and_request_cap(self):
        backend=self.backend()
        original=backend.complete
        def always_bad(prompt,*args,**kwargs):
            return original(prompt.replace("repair","fix"),*args,**kwargs)
        backend.complete=always_bad
        result=run_workflow(self.case,11,"baseline",backend,self.data,"test-model",lambda e:None)
        self.assertEqual(result["repair_rounds"],3)
        self.assertFalse(result["success"])
        result=run_workflow(self.case,11,"treatment",self.backend(),self.data,"test-model",lambda e:None,request_cap=1)
        self.assertEqual(result["error"]["type"],"BudgetError")
        self.assertIsNone(result["itinerary"])


class ProviderTests(unittest.TestCase):
    def test_complete_pilot_journals_replay_and_report(self):
        case=json.loads((ROOT/"revision/cases/hard.json").read_text())[0]
        plan=json.loads((ROOT/"revision/cases/feasibility_witnesses.json").read_text())[0]["witness"]
        def response(parts):
            return {"candidates":[{"content":{"role":"model","parts":parts}}],
                    "usageMetadata":{"promptTokenCount":10,"candidatesTokenCount":5,"totalTokenCount":15}}
        def transport(model,body):
            prompt=body["contents"][0]["parts"][0]["text"]
            if "Role: coordinator_dispatch" in prompt:
                return response([{"text":json.dumps({"activity_task":"choose","feasibility_task":"check"})}])
            if len(body["contents"])==1:
                calls=[{"name":"find_hotels","args":{"budget_level":"Low","limit":100}}]
                if "Role: activities\n" not in prompt:
                    calls.extend({"name":"find_restaurants","args":{"budget_level":"Low","center_id":p,"limit":1}}
                                 for d in plan["days"] for p in d["restaurants"])
                calls.extend({"name":"find_activities","args":{"interests":case["interests"],"center_id":p,"limit":1}}
                             for d in plan["days"] for p in d["activities"])
                return response([{"functionCall":c} for c in calls])
            return response([{"text":json.dumps(plan)}])
        backend=Gemini("test-secret-key",200,transport=transport,sleep=lambda t:None)
        with tempfile.TemporaryDirectory() as tmp:
            exp=Experiment(tmp,"pilot",backend,"test-model",study="pilot")
            exp.run(2)
            result=export(exp.root)
            self.assertEqual(result["status"],"complete")
            self.assertEqual(result["evidence_mode"],"fixture")
            self.assertTrue((exp.root/"analysis/REPORT.md").exists())
            self.assertEqual(result["statistics"]["combined"]["constraint_pass"]["conditions"]["baseline"]["mean"],100)
            self.assertIsNone(result["statistics"]["combined"]["IFR"]["conditions"]["baseline"]["pass3"])
            # Even if a changed journal and record are re-hashed, the audit must
            # reject a tool payload that does not replay from the frozen CSVs.
            case_,seed,condition,repeat=next(exp.schedule())
            folder=exp.folder(case_,seed,condition,repeat)
            events=[json.loads(x) for x in (folder/"events.jsonl").read_text().splitlines()]
            next(e for e in events if e["kind"]=="tool_result" and e["name"]=="find_hotels")["result"]=[]
            (folder/"events.jsonl").write_text("\n".join(json.dumps(e) for e in events)+"\n")
            saved=json.loads((folder/"record.json").read_text())
            saved["events_sha256"]=digest(events)
            (folder/"record.json").write_text(json.dumps(saved))
            (folder/"record.sha256").write_text(file_hash(folder/"record.json"))
            with self.assertRaisesRegex(ValueError,"replay"):
                audit(exp.root)

    def test_partial_cohort_has_no_formal_summary(self):
        backend=Gemini("test-secret-key",200,transport=lambda m,b:{},sleep=lambda t:None)
        with tempfile.TemporaryDirectory() as tmp:
            exp=Experiment(tmp,"partial",backend,"test-model",study="pilot")
            exp.run(1)
            with self.assertRaises(ValueError):export(exp.root)
            progress=export(exp.root,allow_partial=True)
            self.assertEqual(progress["status"],"incomplete")
            self.assertEqual(progress["statistics"],{})

    def test_failed_seed_pair_does_not_verify_seed_behavior(self):
        backend=Gemini("test-secret-key",200,transport=lambda m,b:{},sleep=lambda t:None)
        with tempfile.TemporaryDirectory() as tmp:
            exp=Experiment(tmp,"seeds",backend,"test-model",study="seed_check")
            exp.run(2)
            result=export(exp.root)
            self.assertFalse(result["seed_check"]["both_readable"])
            self.assertIsNone(result["seed_check"]["same_plan"])

    def test_manual_function_cycle_and_thought_signature_preserved(self):
        bodies=[]
        def transport(model,body):
            bodies.append(copy.deepcopy(body))
            if len(bodies)==1:
                return {"candidates":[{"content":{"role":"model","parts":[{"functionCall":{"name":"find_hotels","args":{"budget_level":"Low"}},"thoughtSignature":"retained"}]}}]}
            return {"candidates":[{"content":{"role":"model","parts":[{"text":"{\"done\":true}"}]}}]}
        backend=Gemini("test-secret-key",3,transport=transport,sleep=lambda t:None)
        class FakeTools:
            def call(self,name,args):return [{"place_id":"HOT_1"}]
        events=[]
        result=backend.complete("test",FakeTools(),11,"test-model",events.append,allowed=["find_hotels"])
        self.assertEqual(result,{"done":True})
        self.assertEqual(bodies[1]["contents"][1]["parts"][0]["thoughtSignature"],"retained")
        self.assertEqual(bodies[0]["generationConfig"]["seed"],11)
        self.assertNotIn("test-secret-key",json.dumps(events))
        self.assertEqual(backend.sanitize("test-secret-key"),"[REDACTED]")
        backend.request("test-model",{},events.append)
        with self.assertRaises(BudgetError):backend.request("test-model",{},events.append)

    def test_manifest_resume_and_tampering(self):
        backend=Gemini("test-secret-key",100,transport=lambda m,b:{},sleep=lambda t:None)
        with tempfile.TemporaryDirectory() as tmp:
            a=Experiment(tmp,"test",backend,"test-model",study="pilot")
            Experiment(tmp,"test",backend,"test-model",study="pilot")
            with self.assertRaises(ValueError):Experiment(tmp,"test",backend,"different-model",study="pilot")
            rows=a.run(1)
            self.assertEqual(len(rows),1)
            case,seed,condition,repeat=next(a.schedule())
            folder=a.folder(case,seed,condition,repeat)
            a.read_record(folder,case,seed,condition,repeat)
            with (folder/"events.jsonl").open("a") as f:f.write('{}\n')
            with self.assertRaises(ValueError):a.read_record(folder,case,seed,condition,repeat)


if __name__=="__main__":
    unittest.main()
