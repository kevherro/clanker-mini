import hashlib
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from clanker_ops.store import Store
from clanker_ops import work
from clanker_ops import resources


class WorkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root)
        self.clock = 1000.0
        self.store.now = lambda: self.clock
        work.initialize(self.store)
        self.call("task-create", task_id="t", goal="produce report", target="report.csv", input_id="snapshot-1", deadline=1100)
        self.claim = self.call("task-claim", task_id="t", owner="a", claim_id="attempt-a", lease_seconds=10)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def call(self, operation, **args):
        return work.OPS[operation](self.store, args)

    def checkpoint(self, **updates):
        args = dict(task_id="t", owner="a", generation=1, checkpoint_id="cp1", next_step="verify report", unresolved_effects=[], evidence=[])
        args.update(updates)
        return self.call("task-checkpoint", **args)

    def put(self, content=b"complete report", **updates):
        path = self.root / "input.txt"
        path.write_bytes(content)
        args = dict(task_id="t", owner="a", generation=1, name="report", source="snapshot-1:input.txt", path=str(path))
        args.update(updates)
        return self.call("artifact-put", **args)

    def promote(self, artifact, **updates):
        args = dict(task_id="t", owner="a", generation=1, name="report", sha256=artifact["sha256"], expected_sha256=None, expected_generation=None, acceptance_evidence=["verified report rows against snapshot-1"])
        args.update(updates)
        return self.call("artifact-promote", **args)

    def test_immutable_identity_and_claim_retry(self):
        task = self.call("task-create", task_id="t", goal="produce report", target="report.csv", input_id="snapshot-1", deadline=1100)
        self.assertEqual(task["generation"], 1)
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.call("task-create", task_id="t", goal="different", target="report.csv", input_id="snapshot-1", deadline=1100)
        self.clock += 3
        retry = self.call("task-claim", task_id="t", owner="a", claim_id="attempt-a", lease_seconds=90)
        self.assertEqual(retry["lease_until"], self.claim["lease_until"])
        with self.assertRaisesRegex(ValueError, "live claim"):
            self.call("task-claim", task_id="t", owner="b", claim_id="attempt-b", lease_seconds=10)

    def test_expiry_fences_writes_and_requires_reconciliation(self):
        self.checkpoint(unresolved_effects=["provider launch lost its response"])
        self.clock = 1011
        with self.assertRaisesRegex(ValueError, "expired"):
            self.checkpoint(checkpoint_id="late")
        with self.assertRaisesRegex(ValueError, "expired"):
            self.call("task-claim", task_id="t", owner="a", claim_id="attempt-a", lease_seconds=10)
        resumed = self.call("task-claim", task_id="t", owner="b", claim_id="attempt-b", lease_seconds=20)
        self.assertEqual(resumed["generation"], 2)
        self.assertEqual(resumed["deadline"], 1100)
        self.assertTrue(resumed["reconciliation_required"])
        self.assertEqual(resumed["unresolved_effects"], ["provider launch lost its response"])
        with self.assertRaisesRegex(ValueError, "stale"):
            self.checkpoint(checkpoint_id="stale")
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            self.checkpoint(owner="b", generation=2, checkpoint_id="clear")
        done = self.checkpoint(owner="b", generation=2, checkpoint_id="done", complete=True, evidence=["artifact verified"], reconciliation_evidence=["provider confirms launch failed terminally"])
        self.assertEqual(done["status"], "complete")
        self.assertFalse(done["reconciliation_required"])
        self.assertEqual(done, self.checkpoint(owner="b", generation=2, checkpoint_id="done", complete=True, evidence=["artifact verified"], reconciliation_evidence=["provider confirms launch failed terminally"]))
        with self.assertRaisesRegex(ValueError, "complete"):
            self.call("task-claim", task_id="t", owner="c", claim_id="attempt-c", lease_seconds=10)

    def test_deadline_and_checkpoint_identity(self):
        renewed = self.call("task-renew", task_id="t", owner="a", generation=1, lease_seconds=1000)
        self.assertEqual(renewed["lease_until"], 1100)
        saved = self.checkpoint()
        self.assertEqual(saved, self.checkpoint())
        with self.assertRaisesRegex(ValueError, "different input"):
            self.checkpoint(next_step="erase state")
        self.clock = 1100
        with self.assertRaisesRegex(ValueError, "expired"):
            self.call("task-renew", task_id="t", owner="a", generation=1, lease_seconds=1000)

    def test_artifact_round_trip_is_immutable_and_provenance_bound(self):
        artifact = self.put()
        self.assertEqual(artifact, self.put())
        self.assertEqual(artifact["input_id"], "snapshot-1")
        destination = self.root / "retrieved.txt"
        result = self.call("artifact-read", sha256=artifact["sha256"], destination=str(destination))
        self.assertEqual(destination.read_bytes(), b"complete report")
        self.assertEqual(result["manifests"], [artifact])
        promotion = self.promote(artifact)
        self.assertEqual(promotion, self.promote(artifact))
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.put(b"different report")
        destination.write_text("user changes")
        with self.assertRaisesRegex(ValueError, "different contents"):
            self.call("artifact-read", sha256=artifact["sha256"], destination=str(destination))

    def test_corrupt_incomplete_and_unproven_artifacts_cannot_promote(self):
        artifact = self.put()
        with self.assertRaisesRegex(ValueError, "acceptance_evidence"):
            self.promote(artifact, acceptance_evidence=[])
        (self.root / "artifacts" / "sha256" / artifact["sha256"]).write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.promote(artifact)
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.call("artifact-read", sha256=artifact["sha256"])
        orphan = b"crash after blob write before manifest commit"
        digest = hashlib.sha256(orphan).hexdigest()
        (self.root / "artifacts" / "sha256" / digest).write_bytes(orphan)
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.promote({"sha256": digest})
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.call("artifact-read", sha256=digest)

    def test_stale_output_and_compare_and_swap(self):
        old = self.put()
        self.promote(old)
        self.clock = 1011
        self.call("task-claim", task_id="t", owner="b", claim_id="attempt-b", lease_seconds=20)
        new = self.put(b"new report", owner="b", generation=2)
        with self.assertRaisesRegex(ValueError, "reconcile"):
            self.promote(new, owner="b", generation=2, expected_sha256=old["sha256"], expected_generation=1)
        self.checkpoint(owner="b", generation=2, checkpoint_id="reconciled", reconciliation_evidence=["previous worker exited; output inspected"])
        with self.assertRaisesRegex(ValueError, "compare-and-swap"):
            self.promote(new, owner="b", generation=2)
        self.promote(new, owner="b", generation=2, expected_sha256=old["sha256"], expected_generation=1)
        with self.assertRaisesRegex(ValueError, "stale"):
            self.promote(old, expected_sha256=new["sha256"], expected_generation=2)
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.promote(old, owner="b", generation=2, expected_sha256=new["sha256"], expected_generation=2)

    def test_claim_expiring_during_checksum_cannot_promote(self):
        artifact = self.put()
        original_hash = work._hash

        def slow_hash(path):
            result = original_hash(path)
            self.clock = 1011
            return result

        with patch.object(work, "_hash", side_effect=slow_hash):
            with self.assertRaisesRegex(ValueError, "expired"):
                self.promote(artifact)
        self.assertEqual(self.call("task-read", task_id="t")["promotions"], [])

    def test_interrupted_upload_leaves_no_usable_artifact(self):
        def interrupted(incoming, output):
            output.write(b"partial")
            raise OSError("simulated interrupted upload")

        with patch.object(work.shutil, "copyfileobj", side_effect=interrupted):
            with self.assertRaisesRegex(OSError, "interrupted"):
                self.put()
        count = self.store.db.execute("SELECT COUNT(*) FROM work_artifacts").fetchone()[0]
        self.assertEqual(count, 0)
        self.assertEqual(list((self.root / "artifacts" / "sha256").iterdir()), [])
        artifact = self.put()
        self.promote(artifact)

    def test_unknown_and_missing_fields_rejected_before_mutation(self):
        args = dict(task_id="t", owner="a", generation=1, checkpoint_id="cp", next_step="continue", evidence=[])
        with self.assertRaisesRegex(ValueError, "missing fields"):
            self.call("task-checkpoint", **args)
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            self.call("task-checkpoint", **args, unresolved_effects=[], unresovled_effects=["lost response"])
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            self.call("task-read", task_id="t", extra=True)
        self.assertEqual(self.call("task-read", task_id="t")["next_step"], "")

    def test_out_of_range_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            self.call("task-create", task_id="huge", goal="g", target="t", input_id="i", deadline=10**400)

    def test_artifact_hashing_does_not_block_resource_coordination(self):
        artifact = self.put()
        resources.initialize(self.store)
        second = Store(self.root)
        self.addCleanup(second.close)
        second.db.execute("PRAGMA busy_timeout = 0")
        original = work._verify
        calls = []

        def verify_without_lock(store, digest):
            result = original(store, digest)
            calls.append(resources.policy(second, dict(scope="during-hash", capacity=1, cost=0)))
            return result

        with patch.object(work, "_verify", side_effect=verify_without_lock):
            self.put()
            self.promote(artifact)
        self.assertEqual(len(calls), 2)

    def test_generation_compare_and_swap_rejects_identical_digest_aba(self):
        original = self.put()
        self.promote(original)
        self.clock = 1011
        self.call("task-claim", task_id="t", owner="b", claim_id="b", lease_seconds=10)
        same_bytes = self.put(owner="b", generation=2)
        self.checkpoint(owner="b", generation=2, checkpoint_id="b", reconciliation_evidence=["worker a stopped"])
        self.promote(same_bytes, owner="b", generation=2, expected_sha256=original["sha256"], expected_generation=1)
        self.clock = 1022
        self.call("task-claim", task_id="t", owner="c", claim_id="c", lease_seconds=10)
        different = self.put(b"third report", owner="c", generation=3)
        self.checkpoint(owner="c", generation=3, checkpoint_id="c", reconciliation_evidence=["worker b stopped"])
        with self.assertRaisesRegex(ValueError, "compare-and-swap"):
            self.promote(different, owner="c", generation=3, expected_sha256=original["sha256"], expected_generation=1)
        self.promote(different, owner="c", generation=3, expected_sha256=original["sha256"], expected_generation=2)

    def test_names_and_digests_cannot_traverse_paths(self):
        for name in ("../escape", "a/b", "/tmp/file", "..", "a\\b"):
            with self.assertRaises(ValueError):
                self.put(name=name)
        with self.assertRaises(ValueError):
            self.call("artifact-read", sha256="../escape")

    def test_parallel_claims_have_one_winner(self):
        self.clock = 1011
        barrier = threading.Barrier(2)
        results = []

        def claim(owner):
            store = Store(self.root)
            store.now = lambda: 1011.0
            try:
                barrier.wait(timeout=5)
                results.append(work.task_claim(store, dict(task_id="t", owner=owner, claim_id=owner, lease_seconds=10)))
            except ValueError as error:
                results.append(error)
            finally:
                store.db.close()

        threads = [threading.Thread(target=claim, args=(owner,)) for owner in ("b", "c")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertEqual(sum(isinstance(result, ValueError) for result in results), 1)
        self.assertEqual(self.call("task-read", task_id="t")["generation"], 2)

    def test_persistence_survives_reopen(self):
        self.checkpoint(unresolved_effects=["upload response unknown"])
        self.store.db.close()
        self.store = Store(self.root)
        self.store.now = lambda: 1011.0
        resumed = self.call("task-claim", task_id="t", owner="b", claim_id="new", lease_seconds=10)
        self.assertEqual(resumed["unresolved_effects"], ["upload response unknown"])
        self.assertEqual(resumed["next_step"], "verify report")
        self.assertTrue(resumed["reconciliation_required"])


if __name__ == "__main__":
    unittest.main()
