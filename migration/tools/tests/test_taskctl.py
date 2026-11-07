"""Exercise ledger transitions and evidence failures using isolated temporary roots."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOL = Path(__file__).resolve().parents[1] / "taskctl.py"
SPEC = importlib.util.spec_from_file_location("taskctl_under_test", TOOL)
taskctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(taskctl)


class TaskLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = 1000.0
        self.plan = {"schema_version": 1, "tasks": [
            {"id": "A", "title": "First slice", "depends_on": [], "owned_paths": ["src/**"]},
            {"id": "B", "title": "Dependent slice", "depends_on": ["A"], "owned_paths": ["src/**"]}]}
        self.write("migration/plans/tasks.json", self.plan)
        self.write("migration/state/task-state.json", {"schema_version": 1,
                   "tasks": {key: {"status": "pending", "attempts": 0} for key in ("A", "B")}, "events": []})

    def write(self, path, value):
        output = self.root / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(value) if not isinstance(value, str) else value)
        return output

    def state(self):
        return json.loads((self.root / "migration/state/task-state.json").read_text())

    def invoke(self, *args, ok=True):
        output = io.StringIO()
        with patch.object(taskctl.time, "time", return_value=self.now), contextlib.redirect_stdout(output):
            code = taskctl.main(["--root", str(self.root), *args])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 0 if ok else 2, result)
        self.assertEqual(result["ok"], ok)
        return result

    def claim(self, worker="author", lease=60):
        return self.invoke("claim", "--task", "A", "--worker", worker, "--lease-seconds", str(lease))

    def evidence(self, worker="author", review=False):
        prefix = "review" if review else "author"
        log = self.write(f"runs/{prefix}.log", "Executed 3 cases: all passed.\n")
        artifact = self.write(f"runs/{prefix}-result.json", {"executed": 3, "failed": 0})
        result_commit = hashlib.sha1(b"result commit").hexdigest()
        result = {"task_id": "A", "result_commit": result_commit,
                  "commands": [{"argv": ["python3", "-m", "unittest"], "exit_code": 0,
                                "log": str(log.relative_to(self.root)),
                                "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()}],
                  "artifacts": [{"path": str(artifact.relative_to(self.root)),
                                 "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}],
                  "case_counts": {"executed": 3, "failed": 0, "skipped": 0}}
        if review:
            result.update(reviewer=worker, decision="approve")
        else:
            result.update(worker=worker, base_commit=hashlib.sha1(b"base commit").hexdigest(),
                          limitations=[], source_refs=["https://example.org/pinned-source"], changed_paths=["src/a.rs"])
        return result

    def submit(self, data=None):
        self.write("runs/evidence.json", data if data is not None else self.evidence())
        return self.invoke("submit", "--task", "A", "--worker", "author", "--evidence", "runs/evidence.json")

    def approve(self, data=None, ok=True):
        self.write("runs/review.json", data if data is not None else self.evidence("reviewer", review=True))
        return self.invoke("approve", "--task", "A", "--review-file", "runs/review.json", ok=ok)

    def test_dependency_and_full_lifecycle(self):
        self.assertEqual(self.invoke("next")["task"]["id"], "A")
        self.invoke("claim", "--task", "B", "--worker", "author", ok=False)
        self.claim()
        self.assertIsNone(self.invoke("next")["task"])
        self.submit()
        self.approve()
        self.assertEqual(self.invoke("next")["task"]["id"], "B")
        self.assertEqual(self.state()["tasks"]["A"]["status"], "done")
        self.assertEqual(len(self.state()["events"]), 3)
        self.invoke("claim", "--task", "A", "--worker", "author", ok=False)

    def test_wrong_owner_cannot_mutate(self):
        self.claim()
        self.write("runs/evidence.json", self.evidence("intruder"))
        for command, extra in [("heartbeat", []), ("block", ["--reason", "blocked"]),
                               ("submit", ["--evidence", "runs/evidence.json"])]:
            with self.subTest(command=command):
                before = self.state()
                self.invoke(command, "--task", "A", "--worker", "intruder", *extra, ok=False)
                self.assertEqual(self.state(), before)

    def test_lease_expiration_requires_explicit_reclaim(self):
        self.claim()
        self.invoke("reclaim", "--task", "A", "--worker", "replacement", "--reason", "checked", ok=False)
        self.now = 1060
        self.invoke("heartbeat", "--task", "A", "--worker", "author", ok=False)
        self.invoke("claim", "--task", "A", "--worker", "replacement", ok=False)
        self.invoke("reclaim", "--task", "A", "--worker", "replacement", "--reason", "No live owner")
        record = self.state()["tasks"]["A"]
        self.assertEqual(record["worker"], "replacement")
        self.assertEqual(record["attempts"], 2)

    def test_heartbeat_renews_without_new_attempt(self):
        self.claim()
        self.now = 1059
        self.invoke("heartbeat", "--task", "A", "--worker", "author", "--lease-seconds", "80")
        self.assertEqual(self.state()["tasks"]["A"]["lease_expires_at"], 1139)
        self.assertEqual(self.state()["tasks"]["A"]["attempts"], 1)

    def test_stop_blocks_every_mutation_but_allows_inspection(self):
        self.claim()
        before = self.state()
        self.write("migration/state/STOP", "operator requested stop")
        commands = [("claim", ["--worker", "author"]), ("heartbeat", ["--worker", "author"]),
                    ("block", ["--worker", "author", "--reason", "blocked"]),
                    ("unblock", ["--worker", "author", "--reason", "resolved"]),
                    ("submit", ["--worker", "author", "--evidence", "missing.json"]),
                    ("approve", ["--review-file", "missing.json"]),
                    ("reclaim", ["--worker", "author", "--reason", "checked"])]
        for command, extra in commands:
            with self.subTest(command=command):
                self.assertIn("STOP", self.invoke(command, "--task", "A", *extra, ok=False)["error"])
        self.assertEqual(self.state(), before)
        self.assertTrue(self.invoke("list")["stopped"])
        self.assertIsNone(self.invoke("next")["task"])

    def test_invalid_evidence_cannot_change_state(self):
        self.claim()
        good = self.evidence()
        invalid = [{}, {**good, "commands": []}, {**good, "artifacts": []}, {**good, "limitations": None},
                   {**good, "base_commit": "0" * 40}, {**good, "result_commit": "REPLACE_ME"},
                   {**good, "worker": "another"}, {**good, "task_id": "B"},
                   {**good, "changed_paths": ["unowned/file.rs"]},
                   {**good, "changed_paths": ["../escape"]}]
        for counts in ({"executed": 0, "failed": 0, "skipped": 0},
                       {"executed": 3, "failed": 1, "skipped": 0},
                       {"executed": True, "failed": 0, "skipped": 0},
                       {"executed": 3, "failed": 0, "skipped": 1}):
            invalid.append({**good, "case_counts": counts})
        for argv in ([], "python test", [3]):
            invalid.append({**good, "commands": [{**good["commands"][0], "argv": argv}]})
        for exit_code in (False, 1, "0"):
            invalid.append({**good, "commands": [{**good["commands"][0], "exit_code": exit_code}]})
        for data in invalid:
            with self.subTest(data=data):
                before = self.state()
                self.write("runs/bad.json", data)
                self.invoke("submit", "--task", "A", "--worker", "author", "--evidence", "runs/bad.json", ok=False)
                self.assertEqual(self.state(), before)

    def test_justified_skips_are_recorded_without_becoming_release_approval(self):
        self.claim()
        data = self.evidence()
        data["case_counts"]["skipped"] = 1
        data["skip_justifications"] = ["Optional GPU lane unavailable; milestone remains blocked"]
        self.submit(data)
        self.assertEqual(self.state()["tasks"]["A"]["status"], "submitted")

    def test_missing_outside_or_tampered_files_are_rejected(self):
        self.claim()
        good = self.evidence()
        for path in ("missing.log", "../outside.log", "/etc/passwd"):
            data = copy.deepcopy(good)
            data["commands"][0]["log"] = path
            self.write("runs/bad.json", data)
            self.invoke("submit", "--task", "A", "--worker", "author", "--evidence", "runs/bad.json", ok=False)
        data = copy.deepcopy(good)
        data["artifacts"][0]["sha256"] = hashlib.sha256(b"wrong").hexdigest()
        self.write("runs/bad.json", data)
        self.invoke("submit", "--task", "A", "--worker", "author", "--evidence", "runs/bad.json", ok=False)

    def test_submission_is_immutable_and_approval_rechecks_all_files(self):
        self.claim()
        self.submit()
        self.invoke("submit", "--task", "A", "--worker", "author", "--evidence", "runs/evidence.json", ok=False)
        for filename in ("runs/evidence.json", "runs/author.log", "runs/author-result.json"):
            with self.subTest(filename=filename):
                path = self.root / filename
                original = path.read_bytes()
                path.write_bytes(original + b"\nchanged")
                before = self.state()
                self.approve(ok=False)
                self.assertEqual(self.state(), before)
                path.write_bytes(original)
        self.approve()

    def test_reviewer_identity_commit_decision_and_evidence(self):
        self.claim()
        self.submit()
        review = self.evidence("reviewer", review=True)
        for changed in ({"reviewer": "author"}, {"result_commit": hashlib.sha1(b"other").hexdigest()},
                        {"decision": "reject"}, {"task_id": "B"}, {"commands": []}, {"artifacts": []}):
            with self.subTest(changed=changed):
                self.approve({**review, **changed}, ok=False)
        self.approve(review)

    def test_block_unblock_and_submitted_reclaim_preserve_history(self):
        self.claim()
        self.submit()
        self.invoke("block", "--task", "A", "--worker", "author", "--reason", "Reviewer requested a fix")
        self.assertIsNotNone(self.state()["events"][-1]["previous_submission"])
        self.invoke("claim", "--task", "A", "--worker", "author", ok=False)
        self.invoke("unblock", "--task", "A", "--worker", "other", "--reason", "resolved", ok=False)
        self.invoke("unblock", "--task", "A", "--worker", "author", "--reason", "Fix planned")
        self.claim()
        self.submit()
        self.now += 60
        self.invoke("reclaim", "--task", "A", "--worker", "replacement", "--reason", "Inspected stale work")
        self.assertEqual(self.state()["tasks"]["A"]["status"], "running")
        self.assertNotIn("submission", self.state()["tasks"]["A"])
        self.assertIsNotNone(self.state()["events"][-1]["previous_submission"])

    def test_unknown_task_invalid_lease_and_pending_submission(self):
        self.invoke("claim", "--task", "unknown", "--worker", "author", ok=False)
        for lease in ("0", "-1", "86401"):
            self.invoke("claim", "--task", "A", "--worker", "author", "--lease-seconds", lease, ok=False)
        self.invoke("submit", "--task", "A", "--worker", "author", "--evidence", "missing", ok=False)

    def test_bad_plan_state_json_and_cycle_fail_closed(self):
        for change in ("cycle", "unknown", "duplicate", "empty"):
            plan = copy.deepcopy(self.plan)
            if change == "cycle":
                plan["tasks"][0]["depends_on"] = ["B"]
            elif change == "unknown":
                plan["tasks"][0]["depends_on"] = ["missing"]
            elif change == "duplicate":
                plan["tasks"][1]["id"] = "A"
            else:
                plan["tasks"] = []
            self.write("migration/plans/tasks.json", plan)
            self.invoke("next", ok=False)
        self.write("migration/plans/tasks.json", self.plan)
        for raw in ('{"schema_version":1,"schema_version":1}', 'not-json', '{"tasks":NaN}'):
            self.write("migration/state/task-state.json", raw)
            self.invoke("next", ok=False)

    def test_two_processes_cannot_both_claim(self):
        argv = [sys.executable, str(TOOL), "--root", str(self.root), "claim", "--task", "A", "--worker"]
        processes = [subprocess.Popen([*argv, name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for name in ("one", "two")]
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertFalse(stderr)
            results.append(json.loads(stdout)["ok"])
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.state()["tasks"]["A"]["attempts"], 1)
        self.assertEqual(len(self.state()["events"]), 1)

    def test_failed_atomic_replace_preserves_ledger_and_cleans_temporary(self):
        original = (self.root / "migration/state/task-state.json").read_bytes()
        with patch.object(taskctl.os, "replace", side_effect=OSError("Injected replacement failure")):
            self.invoke("claim", "--task", "A", "--worker", "author", ok=False)
        self.assertEqual((self.root / "migration/state/task-state.json").read_bytes(), original)
        self.assertEqual(list((self.root / "migration/state").glob(".task-state-*.tmp")), [])
        self.claim()


if __name__ == "__main__":
    unittest.main()
