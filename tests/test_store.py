import tempfile
import unittest

from clanker_ops.store import Store


class StoreTest(unittest.TestCase):
    def test_rollback_and_reopen(self):
        with tempfile.TemporaryDirectory() as root:
            with Store(root) as store:
                store.db.execute("CREATE TABLE example (value TEXT)")
                with self.assertRaises(RuntimeError):
                    with store.transaction():
                        store.db.execute("INSERT INTO example VALUES ('partial')")
                        raise RuntimeError("interruption")
                with store.transaction():
                    store.db.execute("INSERT INTO example VALUES ('complete')")
            with Store(root) as store:
                self.assertEqual([r[0] for r in store.db.execute("SELECT value FROM example")],
                                 ["complete"])


if __name__ == "__main__":
    unittest.main()
