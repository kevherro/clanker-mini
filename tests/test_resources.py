import concurrent.futures
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

from clanker_ops import resources
from clanker_ops.store import Store


ADAPTER = r'''
import json, os, pathlib, sys, time
path = pathlib.Path(__file__).with_name("remote.json")
state = json.loads(path.read_text())
payload = json.load(sys.stdin)
operation = sys.argv[1]
state.setdefault("calls", []).append({"operation": operation, **payload})
path.write_text(json.dumps(state))
identity = {k: payload[k] for k in ("launch_id", "retry_token")}
mode = state.get(operation + "_mode", "normal")
if mode == "timeout":
    time.sleep(2)
if mode == "crash":
    print("secret provider diagnostic", file=sys.stderr)
    sys.exit(7)
if mode == "malformed":
    print("secret malformed provider response")
    sys.exit(0)
if mode == "duplicate_keys":
    print('{"launch_id":"wrong","launch_id":"launch-1","retry_token":"token-launch-1","launch_terminal":true,"resources":[]}')
    sys.exit(0)
if mode == "foreign":
    identity["launch_id"] = "another-launch"
if operation == "inspect":
    response = {**identity, "launch_terminal": state.get("launch_terminal", False),
                "resources": state.get("resources", [])}
else:
    if mode == "complete":
        state["launch_terminal"] = True
        state["resources"] = [{"id": r["id"], "terminal": True} for r in state.get("resources", [])]
        path.write_text(json.dumps(state))
    response = {**identity, "launch_cancel_accepted": True,
                "accepted_ids": ["foreign/resource"] if mode == "foreign_resource" else payload["resource_ids"]}
print(json.dumps(response))
'''


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clock = [100.0]
        self.store = Store(self.root / "store", clock=lambda: self.clock[0])
        self.addCleanup(self.store.close)
        resources.initialize(self.store)
        resources.policy(self.store, {"scope": "approved", "capacity": 2, "cost": 100})
        self.adapter = self.root / "adapter"
        self.adapter.write_text("#!" + sys.executable + "\n" + ADAPTER)
        self.adapter.chmod(0o700)
        self.remote_path = self.root / "remote.json"
        self.remote_path.write_text("{}")

    def launch(self, launch_id="launch-1", **overrides):
        args = {"scope": "approved", "launch_id": launch_id, "retry_token": "token-" + launch_id,
                "capacity": 2, "cost": 100, "deadline": 200.0}
        args.update(overrides)
        return resources.reserve(self.store, args)

    def observation(self, terminal=False, items=(), launch_id="launch-1"):
        return resources.observe(self.store, {"launch_id": launch_id, "retry_token": "token-" + launch_id,
                                              "launch_terminal": terminal, "resources": list(items)})

    def remote(self, **updates):
        state = json.loads(self.remote_path.read_text())
        state.update(updates)
        self.remote_path.write_text(json.dumps(state))
        return state

    def reap(self, **args):
        return resources.reap(self.store, {"adapter": str(self.adapter), **args})

    def current(self):
        return resources.status(self.store, {"launch_id": "launch-1"})["reservations"][0]

    def test_atomic_reservations_between_independent_connections(self):
        gate = threading.Barrier(2)

        def contender(name):
            with Store(self.root / "store", clock=lambda: 100.0) as store:
                gate.wait()
                try:
                    resources.reserve(store, {"scope": "approved", "launch_id": name, "retry_token": name,
                                              "capacity": 2, "cost": 100, "deadline": 200.0})
                    return "reserved"
                except ValueError:
                    return "denied"

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as workers:
            answers = list(workers.map(contender, ("a", "b")))
        self.assertEqual(sorted(answers), ["denied", "reserved"])

    def test_policy_and_launch_identity_cannot_change_on_retry(self):
        self.launch()
        self.assertEqual(self.launch()["state"], "held")
        for change in ({"deadline": 300}, {"retry_token": "fresh"}, {"cost": 50}):
            with self.assertRaises(ValueError):
                self.launch(**change)
        with self.assertRaises(ValueError):
            resources.policy(self.store, {"scope": "approved", "capacity": 9, "cost": 999})
        with self.assertRaises(ValueError):
            self.launch("another", retry_token="token-launch-1")

    def test_expiry_and_empty_lookup_keep_ambiguous_launch_reserved(self):
        self.launch()
        self.clock[0] = 201.0
        row = self.reap()["reservations"][0]
        self.assertEqual(row["state"], "cleanup_pending")
        self.assertFalse(row["launch_terminal"])
        self.assertEqual(self.launch()["deadline"], 200.0)
        with self.assertRaises(ValueError):
            self.launch("replacement", deadline=300)
        calls = self.remote()["calls"]
        self.assertEqual([call["operation"] for call in calls], ["cleanup", "inspect"])
        self.assertEqual(calls[0]["resource_ids"], [])

    def test_late_resource_is_cleaned_and_released_only_after_terminal_inspection(self):
        self.launch()
        self.clock[0] = 201.0
        self.reap()
        self.remote(resources=[{"id": "provider/account/vm-1", "terminal": False}])
        row = self.reap()["reservations"][0]
        self.assertEqual(row["state"], "cleanup_pending")
        self.assertEqual(self.remote()["calls"][-2]["resource_ids"], ["provider/account/vm-1"])
        self.remote(cleanup_mode="complete")
        row = self.reap()["reservations"][0]
        self.assertEqual(row["state"], "released")
        self.assertTrue(row["resources"][0]["terminal"])
        self.assertEqual(self.launch("next", deadline=300, cost=0)["state"], "held")

    def test_cleanup_reuses_capacity_but_never_refunds_cost_allowance(self):
        self.launch()
        self.observation(True)
        with self.assertRaises(ValueError):
            self.launch("second", cost=1)
        self.assertEqual(self.launch("zero-cost", cost=0)["state"], "held")

    def test_reaper_rotates_past_stuck_launch_when_limit_is_one(self):
        self.launch(capacity=1, cost=50)
        self.launch("second", capacity=1, cost=50)
        self.clock[0] = 201.0
        first = self.reap(limit=1)["reservations"][0]
        self.assertEqual(first["launch_id"], "launch-1")
        self.assertEqual(first["state"], "cleanup_pending")
        self.remote(cleanup_mode="complete")
        second = self.reap(limit=1)["reservations"][0]
        self.assertEqual(second["launch_id"], "second")
        self.assertEqual(second["state"], "released")

    def test_cleanup_acknowledgment_and_launch_terminal_do_not_release_live_resource(self):
        self.launch()
        self.observation(True, [{"id": "vm-1", "terminal": False}])
        resources.cancel(self.store, {"launch_id": "launch-1"})
        self.remote(launch_terminal=True, resources=[{"id": "vm-1", "terminal": False}])
        self.assertEqual(self.reap()["reservations"][0]["state"], "cleanup_pending")
        self.remote(cleanup_mode="complete")
        self.assertEqual(self.reap()["reservations"][0]["state"], "released")

    def test_resource_disappearance_is_never_terminal_evidence(self):
        self.launch()
        self.observation(False, [{"id": "vm-1", "terminal": False}])
        self.assertEqual(len(self.observation(False)["resources"]), 1)
        with self.assertRaises(ValueError):
            self.observation(True)
        self.assertFalse(self.current()["launch_terminal"])

    def test_monotonic_terminal_evidence_and_foreign_resource_are_checked_atomically(self):
        self.launch(capacity=1, cost=50)
        self.observation(False, [{"id": "vm-1", "terminal": True}])
        with self.assertRaises(ValueError):
            self.observation(False, [{"id": "vm-1", "terminal": False}])
        self.launch("second", capacity=1, cost=50)
        with self.assertRaises(ValueError):
            self.observation(False, [{"id": "new", "terminal": False}, {"id": "vm-1", "terminal": True}], launch_id="second")
        second = resources.status(self.store, {"launch_id": "second"})["reservations"][0]
        self.assertEqual(second["resources"], [])
        self.observation(True, [{"id": "vm-1", "terminal": True}])
        for terminal, items in ((False, []), (True, [{"id": "late", "terminal": False}])):
            with self.assertRaises(ValueError):
                self.observation(terminal, items)

    def test_adapter_failures_do_not_drop_holds_or_echo_provider_secrets(self):
        self.launch()
        resources.cancel(self.store, {"launch_id": "launch-1"})
        for mode in ("foreign", "malformed", "duplicate_keys", "crash"):
            self.remote(inspect_mode=mode)
            row = self.reap()["reservations"][0]
            self.assertEqual(row["state"], "cleanup_pending")
            self.assertIsNotNone(row["last_error"])
            self.assertNotIn("secret", row["last_error"])
        self.remote(inspect_mode="normal", cleanup_mode="foreign_resource")
        row = self.reap()["reservations"][0]
        self.assertIn("foreign", row["last_error"])
        self.assertEqual(row["state"], "cleanup_pending")

    def test_timeout_preserves_holds_and_retry_uses_same_identity(self):
        self.launch()
        resources.cancel(self.store, {"launch_id": "launch-1"})
        self.remote(inspect_mode="timeout")
        self.assertEqual(self.reap(timeout=0.1)["reservations"][0]["state"], "cleanup_pending")
        self.remote(inspect_mode="normal", cleanup_mode="crash")
        self.reap()
        with Store(self.root / "store", clock=lambda: 300.0) as restarted:
            resources.initialize(restarted)
            row = resources.reap(restarted, {"adapter": str(self.adapter)})["reservations"][0]
            self.assertEqual(row["state"], "cleanup_pending")
        calls = self.remote()["calls"]
        self.assertEqual({call["retry_token"] for call in calls}, {"token-launch-1"})
        self.assertEqual({call["deadline"] for call in calls}, {200.0})

    def test_hung_inspection_cannot_starve_cleanup_of_known_resources(self):
        self.launch()
        self.observation(False, [{"id": "vm-1", "terminal": False}])
        resources.cancel(self.store, {"launch_id": "launch-1"})
        self.remote(inspect_mode="timeout", cleanup_mode="complete",
                    resources=[{"id": "vm-1", "terminal": False}])
        result = self.reap(timeout=0.5)
        self.assertEqual(result["reservations"][0]["state"], "cleanup_pending")
        self.assertIn("phase deadline", result["reservations"][0]["last_error"])
        remote = self.remote()
        self.assertEqual(remote["calls"][0]["operation"], "cleanup")
        self.assertEqual(remote["calls"][0]["resource_ids"], ["vm-1"])
        self.assertTrue(remote["resources"][0]["terminal"])
        self.remote(inspect_mode="normal")
        self.assertEqual(self.reap()["reservations"][0]["state"], "released")

    def test_hung_cleanup_cannot_starve_authoritative_inspection(self):
        self.launch()
        resources.cancel(self.store, {"launch_id": "launch-1"})
        self.remote(cleanup_mode="timeout", launch_terminal=True)
        row = self.reap(timeout=0.5)["reservations"][0]
        self.assertEqual(row["state"], "released")
        calls = self.remote()["calls"]
        self.assertEqual([call["operation"] for call in calls], ["cleanup", "inspect"])

    def test_database_lock_exhaustion_is_bounded_and_explicit(self):
        self.launch()
        locked = threading.Event()

        def hold_lock():
            with Store(self.root / "store") as writer:
                with writer.transaction():
                    locked.set()
                    time.sleep(0.3)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as workers:
            future = workers.submit(hold_lock)
            self.assertTrue(locked.wait(2))
            before = time.monotonic()
            result = self.reap(timeout=0.05)
            elapsed = time.monotonic() - before
            self.assertLess(elapsed, 0.2)
            self.assertEqual(result["processed"], 0)
            self.assertTrue(result["pass_exhausted"])
            self.assertIsNone(result["deferred"])
            self.assertTrue(result["errors"])
            future.result()
        self.assertEqual(self.current()["state"], "held")
        self.assertEqual(self.store.db.execute("PRAGMA busy_timeout").fetchone()[0], 10000)

    def test_reaper_reports_candidates_deferred_by_limit(self):
        self.launch(capacity=1, cost=50)
        self.launch("second", capacity=1, cost=50)
        result = self.reap(limit=1)
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["deferred"], 1)
        self.assertFalse(result["pass_exhausted"])

    def test_boundary_rejections_leave_no_partial_reservation(self):
        for args in ({"capacity": True}, {"cost": -1}, {"deadline": float("nan")},
                     {"deadline": float("inf")}, {"deadline": 10**400}, {"deadline": 100}):
            with self.assertRaises(ValueError):
                self.launch(**args)
        self.assertEqual(resources.status(self.store, {})["reservations"], [])
        self.launch()
        with self.assertRaises(ValueError):
            self.observation(False, [{"id": "duplicate", "terminal": False}] * 2)
        self.assertEqual(self.current()["resources"], [])
        with self.assertRaises(ValueError):
            self.reap(adapter="relative/adapter")


if __name__ == "__main__":
    unittest.main()
