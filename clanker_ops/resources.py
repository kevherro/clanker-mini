"""Admission reservations and reconciliation; this ledger is not a billing cap.

Cost is a cumulative allowance: every reservation permanently consumes its full
cost, including after cleanup; only capacity is reusable. There is no refund API.
An adapter's terminal launch assertion includes a complete resource inventory and
guarantees that the launch can never create more resources. Cleanup acceptance is
not terminal evidence. Every cooperating allocator must use the same local store.
"""

import json
import math
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import tempfile
import time


def initialize(store):
    with store.transaction():
        store.db.execute("""CREATE TABLE IF NOT EXISTS resource_policies (
            scope TEXT PRIMARY KEY, capacity INTEGER NOT NULL, cost INTEGER NOT NULL)""")
        store.db.execute("""CREATE TABLE IF NOT EXISTS resource_launches (
            launch_id TEXT PRIMARY KEY, retry_token TEXT UNIQUE NOT NULL,
            scope TEXT NOT NULL REFERENCES resource_policies(scope),
            capacity INTEGER NOT NULL, cost INTEGER NOT NULL, deadline REAL NOT NULL,
            launch_terminal INTEGER NOT NULL DEFAULT 0,
            cancelled INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'held',
            last_error TEXT, last_checked INTEGER NOT NULL DEFAULT 0)""")
        store.db.execute("""CREATE TABLE IF NOT EXISTS observed_resources (
            id TEXT PRIMARY KEY, launch_id TEXT NOT NULL REFERENCES resource_launches(launch_id),
            terminal INTEGER NOT NULL)""")


def _shape(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError("Unexpected or missing fields")


def _text(value):
    if not isinstance(value, str) or not value or len(value) > 512 or value.strip() != value or any(ord(c) < 32 for c in value):
        raise ValueError("Identifiers must be nonempty strings of at most 512 characters")
    return value


def _integer(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 2**63 - 1:
        raise ValueError("Expected a bounded nonnegative integer")
    return value


def _number(value):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("Expected a finite number")
    return float(value)


def _boolean(value):
    if type(value) is not bool:
        raise ValueError("Expected a boolean")
    return value


def _launch(store, launch_id):
    row = store.db.execute("SELECT * FROM resource_launches WHERE launch_id = ?", (_text(launch_id),)).fetchone()
    if row is None:
        raise ValueError("Unknown launch identity")
    return row


def _refresh(store, row):
    remaining = store.db.execute("SELECT 1 FROM observed_resources WHERE launch_id = ? AND terminal = 0 LIMIT 1", (row["launch_id"],)).fetchone()
    state = "released" if row["launch_terminal"] and remaining is None else (
        "cleanup_pending" if row["cancelled"] or row["deadline"] <= store.now() else "held")
    store.db.execute("UPDATE resource_launches SET state = ? WHERE launch_id = ?", (state, row["launch_id"]))


def _result(store, launch_id):
    row = dict(_launch(store, launch_id))
    row["launch_terminal"] = bool(row["launch_terminal"])
    row["cancelled"] = bool(row["cancelled"])
    row["resources"] = [{"id": r["id"], "terminal": bool(r["terminal"])} for r in
                        store.db.execute("SELECT id, terminal FROM observed_resources WHERE launch_id = ? ORDER BY id", (launch_id,))]
    return row


def policy(store, args):
    _shape(args, ("scope", "capacity", "cost"))
    scope, capacity, cost = _text(args["scope"]), _integer(args["capacity"], 1), _integer(args["cost"])
    with store.transaction():
        old = store.db.execute("SELECT * FROM resource_policies WHERE scope = ?", (scope,)).fetchone()
        if old and (old["capacity"], old["cost"]) != (capacity, cost):
            raise ValueError("Existing policy is immutable; changing authority requires a reviewed migration")
        store.db.execute("INSERT OR IGNORE INTO resource_policies VALUES (?, ?, ?)", (scope, capacity, cost))
    return {"scope": scope, "capacity": capacity, "cost": cost, "guarantee": "admission_only"}


def reserve(store, args):
    _shape(args, ("scope", "launch_id", "retry_token", "capacity", "cost", "deadline"))
    scope, launch_id, token = (_text(args[k]) for k in ("scope", "launch_id", "retry_token"))
    capacity, cost, deadline = _integer(args["capacity"], 1), _integer(args["cost"]), _number(args["deadline"])
    with store.transaction():
        old = store.db.execute("SELECT * FROM resource_launches WHERE launch_id = ?", (launch_id,)).fetchone()
        if old:
            if (old["scope"], old["retry_token"], old["capacity"], old["cost"], old["deadline"]) != (scope, token, capacity, cost, deadline):
                raise ValueError("A launch identity cannot change its reservation or original deadline")
            _refresh(store, old)
            return _result(store, launch_id)
        if deadline <= store.now():
            raise ValueError("A new launch requires a future absolute deadline")
        if store.db.execute("SELECT 1 FROM resource_launches WHERE retry_token = ?", (token,)).fetchone():
            raise ValueError("Retry token already belongs to another launch")
        grant = store.db.execute("SELECT * FROM resource_policies WHERE scope = ?", (scope,)).fetchone()
        if grant is None:
            raise ValueError("Unknown policy scope")
        prior = store.db.execute("SELECT capacity, cost, state FROM resource_launches WHERE scope = ?", (scope,)).fetchall()
        if capacity + sum(r["capacity"] for r in prior if r["state"] != "released") > grant["capacity"] or cost + sum(r["cost"] for r in prior) > grant["cost"]:
            raise ValueError("Policy capacity or reserved cost is exhausted")
        store.db.execute("INSERT INTO resource_launches (launch_id, retry_token, scope, capacity, cost, deadline) VALUES (?, ?, ?, ?, ?, ?)",
                         (launch_id, token, scope, capacity, cost, deadline))
        return _result(store, launch_id)


def _observation(value):
    _shape(value, ("launch_id", "retry_token", "launch_terminal", "resources"))
    _text(value["launch_id"])
    _text(value["retry_token"])
    _boolean(value["launch_terminal"])
    if not isinstance(value["resources"], list) or len(value["resources"]) > 1000:
        raise ValueError("Expected at most 1000 resource observations")
    seen = set()
    for resource in value["resources"]:
        _shape(resource, ("id", "terminal"))
        rid = _text(resource["id"])
        _boolean(resource["terminal"])
        if rid in seen:
            raise ValueError("Duplicate resource identity")
        seen.add(rid)


def observe(store, args):
    _observation(args)
    with store.transaction():
        row = _launch(store, args["launch_id"])
        if row["retry_token"] != args["retry_token"]:
            raise ValueError("Observation has a foreign retry token")
        if row["launch_terminal"] and not args["launch_terminal"]:
            raise ValueError("Terminal launch cannot become nonterminal")
        known = {r["id"]: r for r in store.db.execute("SELECT * FROM observed_resources WHERE launch_id = ?", (row["launch_id"],))}
        if args["launch_terminal"] and not set(known) <= {r["id"] for r in args["resources"]}:
            raise ValueError("Terminal launch requires every known resource in its inventory")
        if len(set(known) | {r["id"] for r in args["resources"]}) > 1000:
            raise ValueError("Launch exceeds the resource inventory limit")
        for resource in args["resources"]:
            rid, terminal = resource["id"], resource["terminal"]
            owner = store.db.execute("SELECT * FROM observed_resources WHERE id = ?", (rid,)).fetchone()
            if owner and owner["launch_id"] != row["launch_id"]:
                raise ValueError("Resource identity belongs to a different launch")
            if row["launch_terminal"] and rid not in known:
                raise ValueError("Terminal launch observation contradicted its complete inventory")
            if owner and owner["terminal"] and not terminal:
                raise ValueError("Terminal resource cannot become nonterminal")
            store.db.execute("INSERT INTO observed_resources VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET terminal = excluded.terminal",
                             (rid, row["launch_id"], int(terminal)))
        store.db.execute("UPDATE resource_launches SET launch_terminal = ? WHERE launch_id = ?", (int(args["launch_terminal"]), row["launch_id"]))
        _refresh(store, _launch(store, row["launch_id"]))
        return _result(store, row["launch_id"])


def cancel(store, args):
    _shape(args, ("launch_id",))
    with store.transaction():
        row = _launch(store, args["launch_id"])
        store.db.execute("UPDATE resource_launches SET cancelled = 1 WHERE launch_id = ?", (row["launch_id"],))
        _refresh(store, _launch(store, row["launch_id"]))
        return _result(store, row["launch_id"])


def status(store, args):
    _shape(args, (), ("launch_id",))
    with store.transaction():
        rows = [_launch(store, args["launch_id"])] if "launch_id" in args else store.db.execute("SELECT * FROM resource_launches ORDER BY deadline, launch_id").fetchall()
        for row in rows:
            _refresh(store, row)
        return {"reservations": [_result(store, row["launch_id"]) for row in rows]}


def _invoke(adapter, operation, payload, deadline):
    """Limit an adapter phase by wall clock and one MiB of child output."""
    if time.monotonic() >= deadline:
        raise ValueError("Adapter phase deadline exhausted")
    with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        source.write(json.dumps(payload).encode())
        source.seek(0)
        try:
            process = subprocess.Popen([str(adapter), operation], stdin=source, stdout=output, stderr=errors, start_new_session=True)
        except OSError:
            raise ValueError("Adapter could not execute") from None
        try:
            while True:
                if os.fstat(output.fileno()).st_size + os.fstat(errors.fileno()).st_size > 1024 * 1024:
                    raise ValueError("Adapter output limit exceeded")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError("Adapter phase deadline exhausted")
                try:
                    process.wait(timeout=min(remaining, 0.05))
                    break
                except subprocess.TimeoutExpired:
                    pass
            if process.returncode != 0:
                raise ValueError("Adapter exited unsuccessfully")
            if os.fstat(output.fileno()).st_size + os.fstat(errors.fileno()).st_size > 1024 * 1024:
                raise ValueError("Adapter output limit exceeded")
            output.seek(0)
            try:
                return json.loads(output.read(), object_pairs_hook=_unique_keys)
            except (ValueError, UnicodeError):
                raise ValueError("Adapter returned invalid JSON") from None
        finally:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                process.kill()
            if process.poll() is None:
                process.wait()


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _identity(value, row):
    if not isinstance(value, dict) or value.get("launch_id") != row["launch_id"] or value.get("retry_token") != row["retry_token"]:
        raise ValueError("Adapter response has a foreign launch identity")


class _PassExhausted(Exception):
    pass


def reap(store, args):
    _shape(args, ("adapter",), ("timeout", "limit"))
    adapter = Path(_text(args["adapter"]))
    if not adapter.is_absolute() or not adapter.is_file() or not os.access(adapter, os.X_OK):
        raise ValueError("Adapter must be an absolute executable file")
    timeout, limit = _number(args.get("timeout", 10)), _integer(args.get("limit", 20), 1)
    if not 0 < timeout <= 60 or limit > 100:
        raise ValueError("Pass timeout must be at most 60 seconds and limit at most 100")
    end, results, pass_errors = time.monotonic() + timeout, [], []
    total, skipped, exhausted = None, 0, False
    original_wait = store.db.execute("PRAGMA busy_timeout").fetchone()[0]

    def remaining():
        value = end - time.monotonic()
        if value <= 0:
            raise _PassExhausted()
        return value

    def database(action):
        store.db.execute("PRAGMA busy_timeout = %d" % int(remaining() * 1000))
        try:
            return action()
        except sqlite3.OperationalError as error:
            if str(error) in ("database is locked", "database table is locked", "interrupted"):
                raise _PassExhausted() from None
            raise

    def snapshot():
        with store.transaction():
            count = store.db.execute("SELECT COUNT(*) FROM resource_launches WHERE state != 'released'").fetchone()[0]
            rows = store.db.execute("SELECT * FROM resource_launches WHERE state != 'released' ORDER BY last_checked, deadline, launch_id LIMIT ?", (limit,)).fetchall()
            return count, rows

    def begin(candidate):
        with store.transaction():
            current = _launch(store, candidate["launch_id"])
            if current["state"] == "released":
                return None
            _refresh(store, current)
            sequence = store.db.execute("SELECT COALESCE(MAX(last_checked), 0) + 1 FROM resource_launches").fetchone()[0]
            store.db.execute("UPDATE resource_launches SET last_checked = ? WHERE launch_id = ?", (sequence, candidate["launch_id"]))
            return _result(store, candidate["launch_id"])

    store.db.set_progress_handler(lambda: time.monotonic() >= end, 1000)
    try:
        total, candidates = database(snapshot)
        for candidate in candidates:
            row = database(lambda: begin(candidate))
            if row is None:
                skipped += 1
                continue
            errors, attempted_ids = [], set()
            identity = {k: candidate[k] for k in ("launch_id", "retry_token", "scope", "deadline")}

            def inspect(divisor):
                current = database(lambda: status(store, {"launch_id": candidate["launch_id"]}))["reservations"][0]
                response = _invoke(adapter, "inspect", {**identity, "resource_ids": [r["id"] for r in current["resources"]]}, time.monotonic() + remaining() / divisor)
                _identity(response, candidate)
                return database(lambda: observe(store, response))

            def cleanup(divisor):
                ids = [r["id"] for r in row["resources"] if not r["terminal"]]
                attempted_ids.update(ids)
                try:
                    response = _invoke(adapter, "cleanup", {**identity, "resource_ids": ids}, time.monotonic() + remaining() / divisor)
                    _identity(response, candidate)
                    _shape(response, ("launch_id", "retry_token", "launch_cancel_accepted", "accepted_ids"))
                    _boolean(response["launch_cancel_accepted"])
                    accepted = response["accepted_ids"]
                    if not isinstance(accepted, list) or any(not isinstance(r, str) for r in accepted) or len(accepted) != len(set(accepted)) or not set(accepted) <= set(ids):
                        raise ValueError("Cleanup acknowledgment contains foreign or duplicate resources")
                except ValueError as error:
                    errors.append(str(error))

            def checked_inspect(divisor):
                try:
                    return inspect(divisor)
                except ValueError as error:
                    errors.append(str(error))
                    return database(lambda: status(store, {"launch_id": candidate["launch_id"]}))["reservations"][0]

            def finish():
                with store.transaction():
                    store.db.execute("UPDATE resource_launches SET last_error = ? WHERE launch_id = ?", ("; ".join(errors) or None, candidate["launch_id"]))
                    return _result(store, candidate["launch_id"])

            started_pending = row["state"] == "cleanup_pending"
            try:
                if started_pending:
                    cleanup(3)
                row = checked_inspect(2)
                new_ids = {r["id"] for r in row["resources"] if not r["terminal"]} - attempted_ids
                if row["state"] == "cleanup_pending" and (not started_pending or new_ids):
                    cleanup(2)
                    row = checked_inspect(1)
                row = database(finish)
            except _PassExhausted:
                row["last_error"] = "; ".join(errors + ["Reconciliation pass exhausted; persisted holds remain authoritative"])
                results.append(row)
                raise
            results.append(row)
    except _PassExhausted:
        exhausted = True
        pass_errors.append("Reconciliation pass deadline or SQLite wait budget exhausted")
    finally:
        store.db.set_progress_handler(None, 0)
        store.db.execute("PRAGMA busy_timeout = %d" % original_wait)
    return {"reservations": results, "processed": len(results), "guarantee": "admission_only",
            "pass_exhausted": exhausted or time.monotonic() >= end,
            "deferred": None if total is None else max(0, total - len(results) - skipped), "errors": pass_errors}


OPS = {
    "resource-policy": policy,
    "resource-reserve": reserve,
    "resource-observe": observe,
    "resource-cancel": cancel,
    "resource-status": status,
    "resource-reap": reap,
}
