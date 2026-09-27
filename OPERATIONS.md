# Local operations

This optional Python toolkit gives cooperating processes a durable local authority.
The skills remain usable with an existing runtime instead. It does not provision
cloud resources, supply a scheduler, enforce provider billing, or infer permission
to run or publish anything. Use Python 3.10 or later on macOS or Linux, with no
third-party packages.

## State and invariants

All workers and controllers sharing a policy must use the **same store on one
host's local disk**. SQLite transactions serialize conflicting admissions and
updates. A separate database on each worker is a separate authority; network
filesystems and multiple hosts are not supported. The store is trusted operational
state, not an authorization boundary against another process running as its owner.

| Record | Invariant |
| --- | --- |
| Task | Goal, target, input identity, and absolute deadline retain their original identity across retries. |
| Claim | Only the current unexpired owner and generation can checkpoint or promote an artifact. A new generation fences old writers in this store. |
| Checkpoint | Records verified evidence, the next step, and unresolved external effects; recovering ownership never proves an external effect absent. |
| Artifact | Content is complete and checksum-addressed before a manifest is committed. Promotion binds the current task/input/generation, acceptance evidence, and the expected previous destination. |
| Reservation | Admission atomically reserves capacity and integer cost units against one shared policy. Unknown launch or unconfirmed cleanup retains capacity; the full reserved cost permanently consumes the scope's cumulative allowance. |
| Launch | One durable identity and original deadline survive retries. A late resource is still owned and needs cleanup. |
| Resource | Cleanup requests do not establish termination. Capacity release requires authoritative terminal evidence for the launch and every resource. |

Fencing protects these records; it cannot stop an old worker from writing to an
external service. That service must enforce its own operation identity or fencing.
Before replaying an unresolved effect, establish that it cannot still commit or
use the destination's verified idempotency contract. A claim expiry alone is
insufficient.

Cost reservations limit **admission**, not actual bills. The real executor must
enforce resource shape, finite lifetime, data permissions, and the spending policy.
A separate controller or provider deadline must outlive the agent. A local
controller also depends on its host remaining available; a cloud VM must not rely
on the user's laptop waking up to enforce its lifetime.

## Interface

Run from this repository:

```sh
python3 -m clanker_ops --help
python3 -m unittest discover -s tests -v
```

Operations accept one JSON object from standard input, or a file supplied with
`--input`. They produce one JSON result; errors use standard error and a nonzero
exit code. Select a store outside a source checkout and keep it out of commits.
Do not put credentials in task metadata, evidence, checkpoints, or adapter output.

The task runner remains responsible for checking the actual result. Passing an
acceptance-evidence pointer records a claim; it does not make that claim true.

## Tasks and artifacts

Pass an operation name after `--store`, for example:

```sh
python3 -m clanker_ops --store /absolute/path/to/shared-store task-read <<'JSON'
{"task_id":"build-42"}
JSON
```

The following fields form the JSON interface. Timestamps are Unix seconds in UTC.
Choose a stable logical identity once, before submission; preserve it on retry.

| Operation | Required fields; optional fields in parentheses |
| --- | --- |
| `task-create` | `task_id`, `goal`, `target`, `input_id`, `deadline` |
| `task-read` | `task_id` |
| `task-claim` | `task_id`, `owner`, `claim_id`, `lease_seconds` |
| `task-renew` | `task_id`, `owner`, `generation`, `lease_seconds` |
| `task-checkpoint` | `task_id`, `owner`, `generation`, `checkpoint_id`, `next_step`, `unresolved_effects`, `evidence`; (`complete`, `reconciliation_evidence`) |
| `artifact-put` | `task_id`, `owner`, `generation`, `name`, `path`, `source` |
| `artifact-read` | `sha256`; (`destination`) |
| `artifact-promote` | `task_id`, `owner`, `generation`, `name`, `sha256`, `expected_sha256`, `expected_generation`, `acceptance_evidence` |

1. Create the task with the intended snapshot identity and original deadline.
   Put detailed authority, environment, destination, and wake records in the
   existing durable task system; use evidence pointers here. These records do not
   substitute for a scheduler or a permission system.
2. Claim it using a unique claim request identity and retain the returned generation.
   An active retry returns the same claim; an expired claim ID cannot silently
   renew itself. A new claim after expiry requires live reconciliation. Renew
   before expiry; renewal never extends the original task deadline.
3. Checkpoint before an external effect, recording its durable operation identity
   in `unresolved_effects`. Lists contain nonempty strings. Removing an unresolved
   effect or clearing a reclaimed task's uncertainty needs `reconciliation_evidence`.
   A checkpoint ID cannot be reused with a changed payload. Replaying it returns
   its historical result; use `task-read` for current state before further actions.
4. Submit a completed file with `artifact-put`. It returns the immutable manifest
   and SHA-256. Artifact names are simple names without path separators. Retrieve
   by digest with `artifact-read`; it checks the bytes and never overwrites a
   destination containing different bytes. Directly editing stored blobs causes
   checksum verification to fail.
5. Perform the actual acceptance check. Then promote using the current claim,
   manifest name/digest, and nonempty `acceptance_evidence`. Supply the previous
   promotion's digest **and generation** from `task-read`, or `null` for both if
   absent. A stale predecessor or an old worker cannot replace a newer promotion.
   Promotion updates the local record only; it does not deploy or publish files.
6. Mark the task complete through a checkpoint only after reconciliation, with
   no unresolved effects and actual evidence. Completion prevents new claims.

Interrupted or rejected uploads may leave unreferenced temporary files or blobs. They cannot
be promoted without a complete manifest. The toolkit does not garbage-collect
artifacts; choose an owned store and retention policy, and keep needed evidence
before retiring the store. Multi-file results should be packaged and verified as
one artifact using the project's established format.

## Capacity and launch reconciliation

| Operation | Required fields; optional fields in parentheses |
| --- | --- |
| `resource-policy` | `scope`, `capacity`, `cost` |
| `resource-reserve` | `scope`, `launch_id`, `retry_token`, `capacity`, `cost`, `deadline` |
| `resource-observe` | `launch_id`, `retry_token`, `launch_terminal`, `resources` |
| `resource-cancel` | `launch_id` |
| `resource-status` | None; (`launch_id`) |
| `resource-reap` | `adapter`; (`timeout`, `limit`) |

Define one scope for the actual shared allowance. Capacity and cost are integers;
use one consistent unit per scope, such as worker slots and cents. The policy is
immutable. The full reserved cost is conservatively charged against the scope
forever, including failed or cleaned-up launches. There is no automatic refund,
billing settlement, or budget reset. Creating another scope does not confer more
spending authority. Capacity becomes reusable only after confirmed cleanup.

Reserve before launching through the real executor. Persist its actual idempotency
token in `retry_token`; an invented token does not make a provider idempotent.
Retrying a reservation with identical inputs returns its current state, including
cancellation or release. **Only a valid held reservation within its original
deadline permits the runner to consider launch**; even then, reconcile any earlier
submission first. This tool never makes the launch call. Cancellation marks intent,
and does not mean a remote operation has stopped.

An observation's `resources` is a list of `{"id":"provider-scoped-identity",
"terminal":false}` records. Use globally unambiguous identities including provider,
account, and region as needed. Missing resources remain unresolved. `terminal:true`
means authoritative final state, not accepted deletion. `launch_terminal:true`
asserts that the launch can never create more resources **and** the supplied
inventory is exhaustive. It must include every previously known resource. A
transient empty list cannot establish this assertion. Terminal identities cannot
become active again or acquire new resources.

## Cleanup adapter and controller

Implement the adapter against the actual executor's documented controls, then
validate it with a task-owned resource before relying on it. The toolkit accepts
an explicitly supplied absolute executable path and invokes it without a shell:

- `adapter inspect`: JSON input includes `launch_id`, `retry_token`, `scope`,
  `deadline`, and all known `resource_ids`. Return exactly `launch_id`, `retry_token`,
  `launch_terminal` (boolean), and `resources` as above. Queries must reconcile
  lost launches by stable identity and discover late resources.
- `adapter cleanup`: the same input shape contains only the known nonterminal
  `resource_ids`. Idempotently cancel the original launch and clean precisely its
  owned resources. Return exactly `launch_id`, `retry_token`,
  `launch_cancel_accepted` (boolean), and `accepted_ids` (a subset of the requested
  IDs). An empty ID list still requires cancellation of a possibly pending launch.

Write one JSON object to stdout. Nonzero exit, malformed/contradictory output,
foreign identities, or timeout preserves uncertainty and records `last_error`.
Do not return credentials or payload secrets. Calls can be interrupted or repeated;
adapter cancellation and deletion must converge using the same identities.

Each reconciliation pass inspects held launches. For cancelled or expired launches,
it attempts cleanup and inspection with separate portions of the pass budget;
a hung query must not prevent cancellation from being attempted. Cleanup acceptance
never releases capacity. A persistent rotation prevents one unresolved launch
from monopolizing the queue. `timeout` bounds the entire pass (default 10 seconds, maximum 60);
`limit` bounds the launches considered (default 20, maximum 100). Adapter output is
checked against a one-MiB limit. Pass results report per-launch errors,
`pass_exhausted`, and the count deferred (`null` if it could not be determined).
The CLI returns nonzero on budget exhaustion or a processed launch's adapter error.
Deferred launches remain reserved for a subsequent pass. A successful pass means
reconciliation ran; inspect each resource's state before claiming cleanup finished.
If the database budget expires before the final update, the returned `last_error`
may be a report-only value. Keep the pass output for diagnostics and use the
durable ledger as the authority for reservations and observed resource states.

For a scheduler's one-shot invocation:

```sh
python3 -m clanker_ops.controller --store /absolute/path/to/shared-store \
  --adapter /absolute/path/to/verified-adapter --once
```

For an independently supervised process, omit `--once`. `--interval` controls the
pause between passes; `--timeout` bounds each pass. Register it with the actual
supervisor and verify restart behavior, store identity, effective permissions,
polling capacity, and last successful pass. The controller must remain available
through the resources' lifetime, including after the agent disconnects. Check
that queue length, provider latency, and pass cadence meet the authorized deadline;
the loop is not a hard real-time termination guarantee. Provider-enforced lifetime
limits are still needed when that guarantee is part of the task's policy.

No adapter, supervisor registration, live cleanup, or scheduler wake is created by
installing this repository. Tests use isolated executable fixtures to prove the
local protocol and controller behavior; real provider integration remains a
separate verification step.
