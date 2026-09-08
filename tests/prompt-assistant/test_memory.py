"""CLI integration tests. All identities, feedback and prompts are synthetic."""
import concurrent.futures
import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "prompt-assistant/scripts/memory.py"


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="prompt-assistant-test-")
        self.root = Path(self.tmp.name)
        self.data = self.root / "personal"
        self.call("init")

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, *args, payload=None, ok=True, directory=None):
        cmd = [sys.executable, str(SCRIPT), "--data-dir", str(directory or self.data), *args]
        run = subprocess.run(cmd, input=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
                             text=True, capture_output=True)
        output = json.loads(run.stdout if run.returncode == 0 else run.stderr)
        self.assertEqual(run.returncode, 0 if ok else 2, (args, output))
        self.assertEqual(output["ok"], ok)
        return output

    def item(self, kind="preference", key="tone", body="清楚表达并保留原意", scope=None, source="user_statement", data=None):
        if data is None and kind in {"preference", "project"}:
            data = {"evidence": "合成测试：用户明确表达的偏好"}
        return dict(kind=kind, key=key, title=key, body=body, scope=scope or {}, source=source, data=data or {})

    def record(self, value):
        return self.call("record", "--input", "-", payload=value)["entries"][0]["id"]

    def case(self, task="task-1", scope=None, parent=None, related=None):
        data = dict(task_id=task, request="生成无字封面", prompt="沿用角色参考，封面不放文字。")
        if parent:
            data["parent_id"] = parent
        value = self.item("case", "cover." + task, "封面保留角色轮廓", scope, data=data)
        if related:
            value["related_ids"] = related
        return self.record(value)

    def signal(self, entry_id, signal="result_good", source="user_report"):
        return self.call("feedback", entry_id, "--input", "-", payload={"signal": signal, "source": source, "evidence": "合成测试：用户报告试用后角色轮廓符合参考。"})

    def method(self, scope=None, related=None):
        value = self.item("method", "cover.identity", "封面显式保留角色轮廓", scope,
                          source="inference", data={"rationale": "减少不必要的变化", "when_not": "重新设计角色时不适用"})
        value["related_ids"] = related or []
        return self.record(value)

    def trials(self, *cases):
        return {"conclusion": "合成测试中的范围内比较有帮助", "trials": [
            {"case_id": c, "verdict": "helpful", "source": "user_report", "baseline_result": "轮廓改变",
             "candidate_result": "轮廓保留", "controls": "工具与材料相同，只增加保留条件", "evidence": "合成的用户对比报告"} for c in cases]}

    def validate(self, method, *cases, ok=True):
        return self.call("validate", method, "--input", "-", payload=self.trials(*cases), ok=ok)

    def state(self, entry_id):
        return self.call("get", entry_id)["entry"]["state"]

    def recall(self, *args):
        return self.call("context", *args)["entries"]

    def test_status_does_not_initialize(self):
        missing = self.root / "absent"
        self.assertFalse(self.call("status", directory=missing)["initialized"])
        self.assertFalse(missing.exists())

    def test_runtime_rejects_skill_directory(self):
        forbidden = SCRIPT.parents[1] / ".test-private-must-not-exist"
        self.call("init", directory=forbidden, ok=False)
        self.assertFalse(forbidden.exists())

    def test_scope_isolation_and_project_override(self):
        general = self.record(self.item(body="默认简洁"))
        project = self.record(self.item(body="这个项目详细展开", scope={"project": "A"}))
        tool = self.record(self.item(key="camera", scope={"tool": "Veo"}))
        self.assertEqual([e["id"] for e in self.recall()], [general])
        self.assertEqual([e["id"] for e in self.recall("--project", "A")], [project])
        self.assertEqual([e["id"] for e in self.recall("--project", "B")], [general])
        self.assertEqual({e["id"] for e in self.recall("--tool", "Veo")}, {general, tool})

    def test_inference_never_overwrites_explicit(self):
        entry = self.record(self.item())
        self.call("record", "--input", "-", payload=self.item(source="inference", body="猜测喜欢极简"), ok=False)
        self.assertEqual(self.call("get", entry)["entry"]["revision"], 1)
        guess = self.record(self.item(key="tone.guess", source="inference"))
        self.assertNotIn(guess, {e["id"] for e in self.recall()})
        self.assertIn(guess, {e["id"] for e in self.call("review")["entries"]})

    def test_atomic_batch_does_not_leave_partial_records(self):
        bad = self.item(key="bad")
        bad["unknown"] = True
        self.call("record", "--input", "-", payload=[self.item(), bad], ok=False)
        self.assertEqual(self.call("list")["total"], 0)

    def test_missing_required_case_fields_rejected(self):
        self.call("record", "--input", "-", payload=self.item("case"), ok=False)
        self.assertEqual(self.call("list")["total"], 0)

    def test_case_feedback_preserves_evidence_and_versions(self):
        first = self.case()
        self.assertEqual(self.state(first), "draft")
        self.assertEqual(self.recall("--query", "封面"), [])
        self.signal(first, "prompt_accepted")
        self.assertEqual(self.recall("--query", "封面")[0]["use_as"], "accepted_prompt_only")
        second = self.case(parent=first)
        self.signal(first, "result_bad")
        self.assertEqual(self.state(second), "draft")
        self.signal(first, "prompt_accepted")
        self.assertEqual(self.state(first), "failed")
        self.assertEqual(self.recall("--query", "封面")[0]["use_as"], "pitfall")
        info = self.call("get", first)
        self.assertEqual(len(info["events"]), 3)
        self.assertEqual(info["entry"]["data"]["last_feedback"]["source"], "user_report")
        self.call("rollback", first, "--revision", "1", ok=False)

    def test_case_parent_must_share_task(self):
        parent = self.case()
        value = self.item("case", data={"task_id": "different", "request": "a", "prompt": "b", "parent_id": parent})
        self.call("record", "--input", "-", payload=value, ok=False)

    def test_feedback_rejects_self_rating_and_missing_evidence(self):
        case = self.case()
        self.call("feedback", case, "--input", "-", payload={"signal": "result_good", "source": "inference", "evidence": "我觉得不错"}, ok=False)
        self.call("feedback", case, "--input", "-", payload={"signal": "result_good", "source": "observation", "evidence": ""}, ok=False)
        self.assertEqual(self.state(case), "draft")

    def test_teaching_stages_require_evidence(self):
        bad = self.item("learning", source="assistant_explanation", data={"stage": "applied", "evidence": "我解释过了"})
        self.call("record", "--input", "-", payload=bad, ok=False)
        bad["data"]["stage"] = "introduced"
        item = self.record(bad)
        self.assertEqual(self.state(item), "introduced")

    def test_promotion_requires_distinct_real_outcomes(self):
        a, b = self.case(), self.case()
        method = self.method()
        self.signal(a, "prompt_accepted")
        self.signal(b)
        self.validate(method, a, b, ok=False)
        self.signal(a)
        self.validate(method, a, b, ok=False)  # two versions, one task
        c = self.case("task-2")
        self.signal(c)
        self.validate(method, a, c)
        self.assertEqual(self.state(method), "validated")
        self.assertIn(method, {e["id"] for e in self.recall("--query", "封面")})

    def test_scope_and_harmful_trials_block_promotion(self):
        a, b = self.case("task-1", {"project": "A"}), self.case("task-2", {"project": "B"})
        for case in (a, b):
            self.signal(case)
        method = self.method({"project": "A"})
        self.validate(method, a, b, ok=False)
        global_method = self.method()
        trials = self.trials(a, b)
        trials["trials"][1]["verdict"] = "harmful"
        self.call("validate", global_method, "--input", "-", payload=trials, ok=False)
        self.assertEqual(self.state(global_method), "candidate")

    def test_counterexample_suspends_supported_method(self):
        a, b = self.case("a"), self.case("b")
        self.signal(a)
        self.signal(b)
        method = self.method()
        self.validate(method, a, b)
        result = self.signal(a, "result_mixed")
        self.assertEqual(result["methods_needing_review"], [method])
        self.assertEqual(self.state(method), "review")
        self.assertNotIn(method, {e["id"] for e in self.recall("--query", "封面")})

    def test_new_positive_cases_do_not_hide_known_counterexamples(self):
        a, b, c = self.case("a"), self.case("b"), self.case("c")
        for case in (a, b, c):
            self.signal(case)
        method = self.method()
        self.validate(method, a, b)
        self.signal(a, "result_bad")
        self.validate(method, b, c, ok=False)
        payload = self.trials(b, c)
        payload["counterexamples"] = [{"case_id": a, "resolution": "合成测试：检查发现该案例的参考图损坏，现已补齐；限制方法仅用于完整参考图。",
                                       "source": "observation", "evidence": "合成的材料检查记录"}]
        self.call("validate", method, "--input", "-", payload=payload)
        self.assertEqual(self.state(method), "validated")

    def test_personal_preferences_cannot_come_from_assistant_explanation(self):
        self.call("record", "--input", "-", payload=self.item(source="assistant_explanation"), ok=False)
        self.call("record", "--input", "-", payload=self.item(data={}), ok=False)

    def test_method_rewrite_and_rollback_cannot_retain_validation(self):
        a, b = self.case("a"), self.case("b")
        self.signal(a)
        self.signal(b)
        method = self.method()
        self.validate(method, a, b)
        validated_revision = self.call("get", method)["entry"]["revision"]
        self.assertEqual(self.method(), method)
        self.assertEqual(self.state(method), "candidate")
        self.call("rollback", method, "--revision", str(validated_revision))
        self.assertEqual(self.state(method), "candidate")
        self.call("revoke", method, "--reason", "用户要求")
        self.assertEqual(self.state(method), "revoked")

    def test_correct_preference_and_restore_history(self):
        entry = self.record(self.item(body="最初要求"))
        self.assertEqual(self.record(self.item(body="修订要求")), entry)
        history = self.call("history", entry)["history"]
        self.assertEqual([e["body"] for e in history], ["最初要求", "修订要求"])
        self.call("rollback", entry, "--revision", "1")
        info = self.call("get", entry)["entry"]
        self.assertEqual(info["body"], "最初要求")
        self.assertEqual(info["revision"], 3)

    def test_rescope_removes_old_global_effect(self):
        entry = self.record(self.item())
        self.call("rescope", entry, "--input", "-", payload={"project": "A"})
        self.assertEqual(self.recall(), [])
        self.assertEqual(self.recall("--project", "A")[0]["id"], entry)
        second = self.record(self.item())
        self.call("rollback", entry, "--revision", "1", ok=False)
        self.call("rescope", second, "--input", "-", payload={"project": "A"}, ok=False)

    def test_disable_memory_stops_read_and_learning_but_allows_forget(self):
        entry = self.record(self.item())
        self.call("config", "--memory", "off", "--teaching", "off")
        self.assertEqual(self.recall(), [])
        self.call("record", "--input", "-", payload=self.item(), ok=False)
        self.call("rescope", entry, "--input", "-", payload={}, ok=False)
        self.assertEqual(self.call("list")["total"], 1)
        self.call("forget", entry)
        self.assertEqual(self.call("list")["total"], 0)

    def test_chinese_retrieval_budget_and_complete_summary(self):
        case = self.case()
        self.signal(case)
        result = self.call("context", "--query", "轮廓")
        self.assertEqual(result["entries"][0]["id"], case)
        tiny = self.call("context", "--query", "轮廓", "--budget", "1")
        self.assertEqual(tiny["entries"], [])
        self.assertEqual(tiny["omitted"], 1)
        self.assertLessEqual(tiny["summary_characters"], 1)

    def test_forget_removes_derived_history_events_and_preserves_other(self):
        marker = "PRIVATE-MARKER-DO-NOT-RETAIN"
        root = self.record(self.item(body=marker))
        self.record(self.item(body="新版 " + marker))
        child = self.item(key="derived", body=marker)
        child["related_ids"] = [root]
        child_id = self.record(child)
        case = self.case(related=[child_id])
        self.signal(case)
        unrelated = self.record(self.item(key="unrelated", body="public"))
        impact = self.call("impact", root)["entries_to_forget"]
        self.assertEqual({e["id"] for e in impact}, {root, child_id, case})
        self.call("forget", root)
        self.assertEqual(self.call("list")["total"], 1)
        self.assertEqual(self.recall()[0]["id"], unrelated)
        exported = self.root / "forgotten.json"
        self.call("export", "--output", str(exported))
        self.assertNotIn(marker, exported.read_text())
        with sqlite3.connect(str(self.data / "memory.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM links").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM history").fetchone()[0], 1)

    def test_round_trip_preserves_history_and_requires_method_revalidation(self):
        a, b = self.case("a"), self.case("b")
        self.signal(a)
        self.signal(b)
        method = self.method()
        self.validate(method, a, b)
        self.call("config", "--teaching", "off")
        output = self.root / "portable.json"
        self.call("export", "--output", str(output))
        imported = self.root / "restored"
        restored = self.call("import", "--input", str(output), directory=imported)
        self.assertEqual(restored["imported"], 3)
        self.assertEqual(restored["methods_requiring_validation"], [method])
        self.assertEqual(self.call("get", a, directory=imported)["entry"], self.call("get", a)["entry"])
        self.assertEqual(self.call("get", method, directory=imported)["entry"]["state"], "candidate")
        self.assertEqual(self.call("status", directory=imported)["settings"]["teaching"], "off")
        self.call("import", "--input", str(output), directory=imported, ok=False)
        self.assertEqual(self.call("list", directory=imported)["total"], 3)

    def test_export_never_overwrites_existing_file(self):
        output = self.root / "keep.json"
        output.write_text("original")
        self.call("export", "--output", str(output), ok=False)
        self.assertEqual(output.read_text(), "original")

    def test_invalid_import_is_atomic_and_schema_checked(self):
        self.record(self.item())
        output = self.root / "export.json"
        self.call("export", "--output", str(output))
        value = json.loads(output.read_text())
        bad = copy.deepcopy(value)
        bad["schema_version"] = 99
        empty = self.root / "empty"
        self.call("import", "--input", "-", payload=bad, directory=empty, ok=False)
        self.assertEqual(self.call("list", directory=empty)["total"], 0)
        bad = copy.deepcopy(value)
        bad["links"] = [[value["entries"][0]["id"], "missing"]]
        self.call("import", "--input", "-", payload=bad, directory=empty, ok=False)
        self.assertEqual(self.call("list", directory=empty)["total"], 0)
        bad = copy.deepcopy(value)
        bad["history"] = []
        self.call("import", "--input", "-", payload=bad, directory=empty, ok=False)
        self.assertEqual(self.call("list", directory=empty)["total"], 0)

    def test_concurrent_updates_keep_every_revision(self):
        entry = self.record(self.item())

        def update(index):
            return self.record(self.item(body="更新 " + str(index)))

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            ids = list(pool.map(update, range(12)))
        self.assertEqual(set(ids), {entry})
        history = self.call("history", entry)["history"]
        self.assertEqual([e["revision"] for e in history], list(range(1, 14)))
        self.assertEqual(len({e["body"] for e in history}), 13)

    def test_concurrent_first_use_keeps_settings(self):
        fresh = self.root / "concurrent-first-use"
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.call("init", directory=fresh), range(16)))
        self.assertTrue(all(r["initialized"] for r in results))
        self.call("config", "--memory", "off", directory=fresh)
        self.call("init", directory=fresh)
        self.assertEqual(self.call("status", directory=fresh)["settings"]["memory"], "off")

    def test_multi_session_lifecycle(self):
        """One continuous synthetic user's journey, each call is a fresh process."""
        p = self.record(self.item(key="cover.text", body="这个账号封面不放文字", scope={"project": "A"}))
        first = self.case("launch", {"project": "A"})
        self.signal(first, "prompt_accepted")
        self.assertEqual(self.state(first), "accepted")
        later = self.case("launch", {"project": "A"}, parent=first)
        self.signal(later)
        self.assertEqual(self.state(first), "accepted")
        self.assertEqual(self.state(later), "effective")
        self.assertEqual(self.recall("--query", "封面", "--project", "B"), [])
        self.assertIn(p, {e["id"] for e in self.recall("--query", "封面", "--project", "A")})
        self.call("config", "--teaching", "off")
        self.call("forget", first)
        self.call("get", later, ok=False)
        self.assertEqual(self.call("list")["total"], 1)
        self.assertEqual(self.call("status")["settings"], {"memory": "on", "teaching": "off"})


if __name__ == "__main__":
    unittest.main()
