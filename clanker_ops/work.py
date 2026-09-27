"""Durable, single-host task leases and immutable artifact operations."""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile


def initialize(store):
    store.db.executescript("""
        CREATE TABLE IF NOT EXISTS work_tasks (
            task_id TEXT PRIMARY KEY, goal TEXT NOT NULL, target TEXT NOT NULL,
            input_id TEXT NOT NULL, deadline REAL NOT NULL, status TEXT NOT NULL,
            owner TEXT, generation INTEGER NOT NULL DEFAULT 0, lease_until REAL,
            next_step TEXT NOT NULL DEFAULT '', unresolved_effects TEXT NOT NULL DEFAULT '[]',
            evidence TEXT NOT NULL DEFAULT '[]', reconciliation_required INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS work_claims (
            task_id TEXT NOT NULL, claim_id TEXT NOT NULL, owner TEXT NOT NULL,
            generation INTEGER NOT NULL, PRIMARY KEY (task_id, claim_id)
        );
        CREATE TABLE IF NOT EXISTS work_checkpoints (
            task_id TEXT NOT NULL, checkpoint_id TEXT NOT NULL,
            request TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY (task_id, checkpoint_id)
        );
        CREATE TABLE IF NOT EXISTS work_artifacts (
            task_id TEXT NOT NULL, generation INTEGER NOT NULL, name TEXT NOT NULL,
            input_id TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL,
            source TEXT NOT NULL, PRIMARY KEY (task_id, generation, name)
        );
        CREATE TABLE IF NOT EXISTS work_promotions (
            task_id TEXT NOT NULL, name TEXT NOT NULL, sha256 TEXT NOT NULL,
            generation INTEGER NOT NULL, evidence TEXT NOT NULL,
            PRIMARY KEY (task_id, name)
        );
    """)


def _text(args, key):
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a nonempty string")
    return value


def _number(args, key):
    value = args.get(key)
    try:
        valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{key} must be a finite number")
    return value


def _items(args, key):
    value = args.get(key, [])
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f"{key} must be a list of nonempty strings")
    return value


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _task(store, task_id):
    row = store.db.execute("SELECT * FROM work_tasks WHERE task_id = ?", (task_id,)).fetchone()
    if row is None:
        raise ValueError("unknown task_id")
    result = dict(row)
    for key in ("unresolved_effects", "evidence"):
        result[key] = json.loads(result[key])
    result["reconciliation_required"] = bool(result["reconciliation_required"])
    return result


def validate_claim(store, task_id, owner, generation):
    """Validate within the caller's transaction; this fences only this store."""
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        raise ValueError("generation must be a positive integer")
    task = _task(store, task_id)
    if task["status"] != "open" or task["owner"] != owner or task["generation"] != generation:
        raise ValueError("claim is stale or task is complete")
    if store.now() >= min(task["lease_until"], task["deadline"]):
        raise ValueError("claim or original task deadline has expired")
    return task


def task_create(store, args):
    identity = tuple(_text(args, key) for key in ("task_id", "goal", "target", "input_id"))
    deadline = _number(args, "deadline")
    with store.transaction():
        row = store.db.execute("SELECT * FROM work_tasks WHERE task_id = ?", identity[:1]).fetchone()
        if row:
            if tuple(row[key] for key in ("task_id", "goal", "target", "input_id", "deadline")) != (*identity, deadline):
                raise ValueError("task_id already belongs to a different immutable task identity")
        else:
            if deadline <= store.now():
                raise ValueError("deadline must be in the future")
            store.db.execute("INSERT INTO work_tasks(task_id, goal, target, input_id, deadline, status) VALUES (?, ?, ?, ?, ?, 'open')", (*identity, deadline))
        return _task(store, identity[0])


def task_read(store, args):
    with store.transaction():
        task = _task(store, _text(args, "task_id"))
        task["claim_active"] = task["status"] == "open" and task["lease_until"] is not None and store.now() < min(task["lease_until"], task["deadline"])
        task["promotions"] = [dict(row) for row in store.db.execute("SELECT * FROM work_promotions WHERE task_id=? ORDER BY name", (task["task_id"],))]
        for promotion in task["promotions"]:
            promotion["evidence"] = json.loads(promotion["evidence"])
        return task


def task_claim(store, args):
    task_id, owner, claim_id = (_text(args, key) for key in ("task_id", "owner", "claim_id"))
    duration = _number(args, "lease_seconds")
    if duration <= 0:
        raise ValueError("lease_seconds must be positive")
    with store.transaction():
        task = _task(store, task_id)
        prior = store.db.execute("SELECT * FROM work_claims WHERE task_id = ? AND claim_id = ?", (task_id, claim_id)).fetchone()
        if prior:
            if prior["owner"] != owner:
                raise ValueError("claim_id belongs to another owner")
            return validate_claim(store, task_id, owner, prior["generation"])
        now = store.now()
        if task["status"] != "open" or now >= task["deadline"]:
            raise ValueError("task is complete or its original deadline has expired")
        if task["lease_until"] is not None and now < task["lease_until"]:
            raise ValueError("task already has a live claim")
        generation = task["generation"] + 1
        store.db.execute("UPDATE work_tasks SET owner=?, generation=?, lease_until=?, reconciliation_required=? WHERE task_id=?", (owner, generation, min(now + duration, task["deadline"]), int(generation > 1), task_id))
        store.db.execute("INSERT INTO work_claims VALUES (?, ?, ?, ?)", (task_id, claim_id, owner, generation))
        return _task(store, task_id)


def task_renew(store, args):
    task_id, owner = (_text(args, key) for key in ("task_id", "owner"))
    duration = _number(args, "lease_seconds")
    if duration <= 0:
        raise ValueError("lease_seconds must be positive")
    with store.transaction():
        task = validate_claim(store, task_id, owner, args.get("generation"))
        until = min(max(task["lease_until"], store.now() + duration), task["deadline"])
        store.db.execute("UPDATE work_tasks SET lease_until=? WHERE task_id=?", (until, task_id))
        return _task(store, task_id)


def task_checkpoint(store, args):
    task_id, owner, checkpoint_id = (_text(args, key) for key in ("task_id", "owner", "checkpoint_id"))
    next_step = _text(args, "next_step")
    effects, evidence, reconciliation = (_items(args, key) for key in ("unresolved_effects", "evidence", "reconciliation_evidence"))
    complete = args.get("complete", False)
    if not isinstance(complete, bool):
        raise ValueError("complete must be boolean")
    request = _json(args)
    with store.transaction():
        prior = store.db.execute("SELECT * FROM work_checkpoints WHERE task_id=? AND checkpoint_id=?", (task_id, checkpoint_id)).fetchone()
        if prior:
            if prior["request"] != request:
                raise ValueError("checkpoint_id already records different input")
            return json.loads(prior["result"])
        task = validate_claim(store, task_id, owner, args.get("generation"))
        if set(task["unresolved_effects"]) - set(effects) and not reconciliation:
            raise ValueError("removing unresolved effects requires reconciliation_evidence")
        pending = task["reconciliation_required"] and not reconciliation
        if complete and (pending or effects or not evidence):
            raise ValueError("completion requires evidence, reconciled claims, and no unresolved effects")
        store.db.execute("UPDATE work_tasks SET next_step=?, unresolved_effects=?, evidence=?, reconciliation_required=?, status=? WHERE task_id=?", (next_step, _json(effects), _json(evidence + reconciliation), int(pending), "complete" if complete else "open", task_id))
        result = _task(store, task_id)
        store.db.execute("INSERT INTO work_checkpoints VALUES (?, ?, ?, ?)", (task_id, checkpoint_id, request, _json(result)))
        return result


def _name(args):
    name = _text(args, "name")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", name):
        raise ValueError("name must be a simple artifact name without path separators")
    return name


def _digest(args, key="sha256"):
    value = _text(args, key)
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{key} must be a lowercase SHA-256 digest")
    return value


def _hash(path):
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def _blob(store, digest):
    return store.root / "artifacts" / "sha256" / digest


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _verify(store, digest):
    path = _blob(store, digest)
    if not path.is_file():
        raise ValueError("artifact blob is missing or incomplete")
    actual, size = _hash(path)
    if actual != digest:
        raise ValueError("artifact checksum mismatch")
    return path, size


def artifact_put(store, args):
    task_id, owner, source = (_text(args, key) for key in ("task_id", "owner", "source"))
    name, input_path = _name(args), Path(_text(args, "path"))
    if not input_path.is_file():
        raise ValueError("path must identify a complete regular file")
    with store.transaction():
        validate_claim(store, task_id, owner, args.get("generation"))
    directory = store.root / "artifacts" / "sha256"
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".upload-", dir=directory)
    temporary = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as output, input_path.open("rb") as incoming:
            shutil.copyfileobj(incoming, output)
            output.flush()
            os.fsync(output.fileno())
        digest, size = _hash(temporary)
        try:
            os.link(temporary, _blob(store, digest))
        except FileExistsError:
            _verify(store, digest)
        _sync_directory(directory)
        _sync_directory(directory.parent)
        _sync_directory(store.root)
        with store.transaction():
            task = validate_claim(store, task_id, owner, args.get("generation"))
            manifest = dict(task_id=task_id, generation=task["generation"], name=name, input_id=task["input_id"], sha256=digest, size=size, source=source)
            prior = store.db.execute("SELECT * FROM work_artifacts WHERE task_id=? AND generation=? AND name=?", (task_id, task["generation"], name)).fetchone()
            if prior and dict(prior) != manifest:
                raise ValueError("artifact name already identifies a different immutable manifest")
            store.db.execute("INSERT OR IGNORE INTO work_artifacts VALUES (?, ?, ?, ?, ?, ?, ?)", tuple(manifest.values()))
            return manifest
    finally:
        temporary.unlink(missing_ok=True)


def artifact_read(store, args):
    digest = _digest(args)
    with store.transaction():
        manifests = [dict(row) for row in store.db.execute("SELECT * FROM work_artifacts WHERE sha256=?", (digest,))]
        if not manifests:
            raise ValueError("no complete manifest exists for this artifact")
    path, size = _verify(store, digest)
    if "destination" in args:
        destination = Path(_text(args, "destination"))
        if destination.exists():
            if not destination.is_file() or _hash(destination)[0] != digest:
                raise ValueError("destination exists with different contents")
        else:
            descriptor, temporary = tempfile.mkstemp(prefix=".retrieve-", dir=destination.parent)
            try:
                with os.fdopen(descriptor, "wb") as output, path.open("rb") as incoming:
                    shutil.copyfileobj(incoming, output)
                    output.flush()
                    os.fsync(output.fileno())
                if _hash(Path(temporary))[0] != digest:
                    raise ValueError("artifact changed during retrieval")
                try:
                    os.link(temporary, destination)
                    _sync_directory(destination.parent)
                except FileExistsError:
                    if _hash(destination)[0] != digest:
                        raise ValueError("destination was concurrently created with different contents")
            finally:
                Path(temporary).unlink(missing_ok=True)
        path = destination
    return {"sha256": digest, "size": size, "path": str(path.resolve()), "manifests": manifests}


def artifact_promote(store, args):
    task_id, owner = (_text(args, key) for key in ("task_id", "owner"))
    name, digest, evidence = _name(args), _digest(args), _items(args, "acceptance_evidence")
    if "expected_sha256" not in args or "expected_generation" not in args or not evidence:
        raise ValueError("promotion requires expected_sha256, expected_generation (both null for absent), and acceptance_evidence")
    expected = args["expected_sha256"]
    expected_generation = args["expected_generation"]
    if expected is not None:
        _digest(args, "expected_sha256")
        if isinstance(expected_generation, bool) or not isinstance(expected_generation, int) or expected_generation < 1:
            raise ValueError("expected_generation must be a positive integer when expected_sha256 is set")
    elif expected_generation is not None:
        raise ValueError("expected_generation must be null when expected_sha256 is null")
    with store.transaction():
        task = validate_claim(store, task_id, owner, args.get("generation"))
        if task["reconciliation_required"] or task["unresolved_effects"]:
            raise ValueError("reconcile the claim and unresolved effects before promotion")
        manifest = store.db.execute("SELECT * FROM work_artifacts WHERE task_id=? AND generation=? AND name=? AND sha256=? AND input_id=?", (task_id, task["generation"], name, digest, task["input_id"])).fetchone()
        if manifest is None:
            raise ValueError("no complete artifact manifest matches this task, input, and claim generation")
    _verify(store, digest)
    with store.transaction():
        task = validate_claim(store, task_id, owner, args.get("generation"))
        if task["reconciliation_required"] or task["unresolved_effects"]:
            raise ValueError("reconcile the claim and unresolved effects before promotion")
        prior = store.db.execute("SELECT * FROM work_promotions WHERE task_id=? AND name=?", (task_id, name)).fetchone()
        result = dict(task_id=task_id, name=name, sha256=digest, generation=task["generation"], evidence=evidence)
        if prior and prior["sha256"] == digest and prior["generation"] == task["generation"] and json.loads(prior["evidence"]) == evidence:
            return result
        if ((prior["sha256"], prior["generation"]) if prior else (None, None)) != (expected, expected_generation):
            raise ValueError("promotion compare-and-swap failed: expected_sha256 or expected_generation is stale")
        store.db.execute("INSERT INTO work_promotions VALUES (?, ?, ?, ?, ?) ON CONFLICT(task_id, name) DO UPDATE SET sha256=excluded.sha256, generation=excluded.generation, evidence=excluded.evidence", (task_id, name, digest, task["generation"], _json(evidence)))
        return result


def _operation(function, required, optional=()):
    required, allowed = set(required.split()), set(required.split()) | set(optional)

    def checked(store, args):
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
        missing, unknown = required - args.keys(), args.keys() - allowed
        if missing or unknown:
            raise ValueError(f"missing fields: {sorted(missing)}; unknown fields: {sorted(unknown)}")
        return function(store, args)

    return checked


OPS = {
    "task-create": _operation(task_create, "task_id goal target input_id deadline"),
    "task-read": _operation(task_read, "task_id"),
    "task-claim": _operation(task_claim, "task_id owner claim_id lease_seconds"),
    "task-renew": _operation(task_renew, "task_id owner generation lease_seconds"),
    "task-checkpoint": _operation(task_checkpoint, "task_id owner generation checkpoint_id next_step unresolved_effects evidence", ("complete", "reconciliation_evidence")),
    "artifact-put": _operation(artifact_put, "task_id owner generation name path source"),
    "artifact-read": _operation(artifact_read, "sha256", ("destination",)),
    "artifact-promote": _operation(artifact_promote, "task_id owner generation name sha256 expected_sha256 expected_generation acceptance_evidence"),
}
