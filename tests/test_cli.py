import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CLITest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = self.root / "store"

    def call(self, operation, request, expected=0):
        run = subprocess.run([sys.executable, "-m", "clanker_ops", "--store", str(self.store), operation],
                             input=json.dumps(request), text=True, capture_output=True, cwd=ROOT, timeout=10)
        self.assertEqual(run.returncode, expected, run.stderr + run.stdout)
        return json.loads(run.stdout if run.stdout else run.stderr)

    def test_task_and_artifact_roundtrip_across_processes(self):
        self.call("task-create", dict(task_id="report", goal="verified report", target="local", input_id="snapshot-dirty", deadline=time.time() + 3600))
        claim = self.call("task-claim", dict(task_id="report", owner="worker", claim_id="claim-1", lease_seconds=300))
        owner = dict(task_id="report", owner="worker", generation=claim["generation"])
        source = self.root / "source.txt"
        source.write_text("the intended result\n")
        artifact = self.call("artifact-put", dict(owner, name="report.txt", path=str(source), source="local smoke test"))
        promote = dict(owner, name="report.txt", sha256=artifact["sha256"], expected_sha256=None,
                       expected_generation=None, acceptance_evidence=["source inspected by local smoke test"])
        self.call("artifact-promote", promote)
        destination = self.root / "retrieved.txt"
        self.call("artifact-read", dict(sha256=artifact["sha256"], destination=str(destination)))
        self.assertEqual(destination.read_bytes(), source.read_bytes())
        checkpoint = dict(owner, checkpoint_id="complete-1", next_step="none", unresolved_effects=[],
                          evidence=["verified report bytes"], complete=True)
        self.assertEqual(self.call("task-checkpoint", checkpoint)["status"], "complete")
        self.assertEqual(self.call("task-checkpoint", checkpoint)["status"], "complete")
        self.assertEqual(self.call("task-read", {"task_id": "report"})["status"], "complete")
        self.call("task-claim", dict(task_id="report", owner="duplicate", claim_id="claim-2", lease_seconds=300), expected=2)

    def test_invalid_json_does_not_create_store(self):
        for raw in ('{"scope":"a","scope":"b","capacity":1,"cost":0}',
                    '{"scope":"a","capacity":1,"cost":NaN}', '[]'):
            run = subprocess.run([sys.executable, "-m", "clanker_ops", "--store", str(self.store), "resource-policy"],
                                 input=raw, text=True, capture_output=True, cwd=ROOT, timeout=10)
            self.assertEqual(run.returncode, 2)
            self.assertIn("error", json.loads(run.stderr))
            self.assertFalse(self.store.exists())

    def adapter(self, content):
        path = self.root / "adapter.py"
        path.write_text("#!" + sys.executable + "\n" + content)
        path.chmod(0o700)
        return path

    def reserve(self):
        self.call("resource-policy", dict(scope="local-fixture", capacity=1, cost=0))
        self.call("resource-reserve", dict(scope="local-fixture", launch_id="launch-1", retry_token="stable-token", capacity=1, cost=0, deadline=time.time() + 3600))

    @unittest.skipUnless(os.name == "posix", "executable adapter fixture uses a POSIX shebang")
    def test_separate_controller_cleans_after_reserving_process_exits(self):
        self.reserve()
        self.call("resource-cancel", {"launch_id": "launch-1"})
        adapter = self.adapter('''import json, pathlib, sys
request = json.load(sys.stdin)
state = pathlib.Path(__file__).with_suffix(".done")
reply = {key: request[key] for key in ("launch_id", "retry_token")}
if sys.argv[1] == "cleanup":
    state.write_text("cleanup was performed by adapter")
    reply.update(launch_cancel_accepted=True, accepted_ids=request["resource_ids"])
else:
    reply.update(launch_terminal=state.exists(), resources=[{"id":"fixture-resource", "terminal":state.exists()}])
print(json.dumps(reply))
''')
        run = subprocess.run([sys.executable, "-m", "clanker_ops.controller", "--store", str(self.store),
                              "--adapter", str(adapter), "--once"], cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["reservations"][0]["state"], "released")
        self.assertTrue(adapter.with_suffix(".done").is_file())
        self.assertEqual(self.call("resource-status", {})["reservations"][0]["state"], "released")

    @unittest.skipUnless(os.name == "posix", "executable adapter fixture uses a POSIX shebang")
    def test_controller_and_cli_report_adapter_failure_and_retain_reservation(self):
        self.reserve()
        adapter = self.adapter('print("not valid JSON")\n')
        run = subprocess.run([sys.executable, "-m", "clanker_ops.controller", "--store", str(self.store),
                              "--adapter", str(adapter), "--once"], cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 2, run.stderr)
        row = json.loads(run.stdout)["reservations"][0]
        self.assertEqual(row["state"], "held")
        self.assertTrue(row["last_error"])
        self.call("resource-reap", dict(adapter=str(adapter)), expected=2)
        self.call("resource-reserve", dict(scope="local-fixture", launch_id="duplicate", retry_token="other-token",
                                          capacity=1, cost=0, deadline=time.time() + 3600), expected=2)

    @unittest.skipUnless(os.name == "posix", "executable adapter fixture uses a POSIX shebang")
    def test_exhausted_pass_is_not_reported_as_success(self):
        self.reserve()
        adapter = self.adapter('raise RuntimeError("no adapter call fits this budget")\n')
        result = self.call("resource-reap", dict(adapter=str(adapter), timeout=1e-9), expected=2)
        self.assertTrue(result["pass_exhausted"])
        run = subprocess.run([sys.executable, "-m", "clanker_ops.controller", "--store", str(self.store),
                              "--adapter", str(adapter), "--timeout", "0.000000001", "--once"],
                             cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertTrue(json.loads(run.stdout)["pass_exhausted"])
        self.assertEqual(self.call("resource-status", {})["reservations"][0]["state"], "held")


if __name__ == "__main__":
    unittest.main()
