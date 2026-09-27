# Remote execution contract

Apply this contract to the actual connected provider or established runner.
It describes required observations and controls, not a fictional universal API.
Use documented capabilities; verify provider-specific semantics before mutation.

## Resolve standing policy

Read the task's existing authorization and applicable configuration. Record the
source of each limit. Honor the most recent scope changes. Missing values are
unknown, not unlimited; do not turn sample values into user authorization.

Apply billing requirements only where the operation can incur charges. An
already authorized executor with verified zero incremental cost needs no cloud
price lookup or invented monetary reservation. Verify that fact across compute,
transfer, and storage, and retain data permissions, capacity ownership, bounded
job execution, and task-owned cleanup. Record inapplicable policy fields with
their reason instead of inventing an account or region for a private executor.

| Policy fact | What must be established |
| --- | --- |
| Placement | Permitted provider/account/project, region, workload, resource types and maximum sizes |
| Data | Allowed inputs and destinations, credential scope, and any locality constraints |
| Allowance | Per-job cost bound and any shared spending period, remaining allowance, and reservation owner |
| Capacity | Maximum simultaneous jobs/resources, counting pending and ambiguous launches |
| Time | Absolute task deadline, maximum resource lifetime, queue/startup/retry bounds, and cleanup margin |
| Retention | Where results/logs persist, ownership, permitted duration and storage cost, and what must be deleted |

A task-specific approval can supply the policy; no particular policy file is
required. If permission is missing, prepare the placement, estimated exposure,
deadline, data movement, and cleanup plan for approval. Do not ask again when
standing authorization already covers them. A read-only request permits planning
and inspection only, even if older authorization allowed provisioning.

## Bound exposure before launch

Estimate cost using current documented rates and billing units for the selected
configuration. Include permitted startup and execution time, retries, disks,
accelerators, transfer, artifact retention, and other applicable charges. State
uncertainties and leave room for shutdown delay and billing granularity.
Reserve conservative exposure through the permitted lifetime and retention,
not just the expected execution cost. Distinguish the per-job ceiling, shared
remaining allowance, and any explicitly required hard billed-total cap. Do not
infer permission to exceed them. An estimate or delayed billing alert is not an
exact enforced dollar cap. If a required spending guarantee cannot be enforced,
do not spend under that requirement: establish the needed controls or obtain
authorization for a different bound. Disclosure alone does not grant that change.

Reserve capacity and, where charges apply, allowance against an authoritative
shared controller or ledger before provisioning or job submission. Count existing
commitments and unresolved launches;
two workers cannot each spend the same remaining allowance. Use the established
atomic reservation mechanism or a single authorized allocator covering that
policy's scope. A local note or lock shared by only one task cannot enforce an
account-wide limit. If shared capacity cannot be established, do not assume it is free.

Select controls that work independently of this agent/session: a bounded managed
job, provider-enforced expiry, or an independent controller that cancels work and
cleans up task-owned resources. Verify their coverage and permissions before
launch. A job timeout may leave its VM, disks, or queued descendants intact;
tags alone do not enforce expiry. Include late-created resources and retries
under the recorded effective deadline, initially the original absolute deadline.
Only the authorized extension procedure below may change it. Never reset the
allowance or lifetime just because an attempt is replaced.

For an existing shared executor, bound this job and its incremental resources;
do not acquire teardown ownership of the whole machine. Use its controller to
account for occupied capacity and other jobs. Required controls that cannot be
verified are a missing capability, not a reason to provision optimistically.

## Prepare exact inputs and record intent

Create a reproducible snapshot of the authorized inputs and environment: revision
plus relevant uncommitted/untracked changes, dependency versions, and required
runtime details. Include only task inputs permitted to leave the machine. Do not
copy an entire home directory, credential store, or ignored files indiscriminately.
Use scoped credentials through the provider's supported mechanism; do not embed
secrets in the snapshot, run record, images, or logs.

Use the existing task store or an authorized durable record that can be recovered
after disconnection. Before the launch request, record:

- Logical operation and attempt identity, input snapshot identity, target, and execution owner.
- Launch intent and original provider idempotency token when supported.
- Reservation identity, applicable cost/capacity bounds, original and effective deadlines, and control/cleanup ownership.
- Planned output destination and retention; all known job, VM, disk, and other resource IDs.
- Current phase and last observed state, including any unresolved request or effect.

Record new resource IDs as responses arrive. Preserve the intent record until
all possibly created resources are accounted for. During a move from local to
remote work, settle the old execution's ownership and partial effects before
allowing the remote attempt to repeat side effects. Separate attempts' outputs
so a late result cannot overwrite the accepted artifact or revive a closed task.

## Launch once, then reconcile uncertainty

After a lost response, treat the launch as possibly live and billable. Keep the
same logical operation, original token, reservation, capacity slot, and effective deadline.
Use request status, recorded IDs, or documented ownership queries to reconcile.
An empty listing, timeout, or expired client connection does not prove that the
original request failed or cannot still create a resource.

Reissue only when the documented idempotency contract covers this exact request
and token, or authoritative evidence proves the original request created nothing
and cannot still commit. Do not switch providers or create a new launch identity
to escape an unknown result. If it remains unresolved, stop further launches for
that unit, retain the reservation and cleanup responsibility, and report the
exposure. Reconcile any late resource under the effective deadline, including
after cancellation or the parent's session ends. After cancellation or expiry,
send a late resource directly to cleanup; it receives no new execution allowance.

Monitor task-relevant progress and resource use within the existing bounds.
Do not grow instance size or retry count indefinitely to hide a leak or repeated
failure. Apply changes only if the current policy and remaining allowance cover
them, after checking ownership and partial effects.

## Collect results and close resource ownership

Arrange durable output capture before execution when required by the deadline.
Retrieve logs and artifacts tied to the input snapshot and attempt, then verify
the requested outcome. Inspect late or superseded results before accepting them;
do not let their arrival overwrite the current task's result automatically.

Collection failure does not authorize extending paid compute indefinitely. Honor
the compute deadline and keep only outputs allowed by the retention policy. A
bounded extension requires authority specifically covering the extension and
remaining allowance. Before the old deadline expires, update the reservation
and verify the independent controller's new effective deadline within the policy's
hard limits. Retain the original deadline and extension history. If authorization
or the control update is missing, terminate as planned and report incomplete or
lost results honestly; a larger deadline written only in a local record is insufficient.

On success, failure, cancellation, or timeout, run the same ownership-aware cleanup.
Cancel only this task's jobs and remove only its owned temporary resources. Preserve
shared workers and unrelated data. Verify terminal/deleted state through the
provider or controller; stopping computation is not proof all charges stopped.
Check residual disks, addresses, snapshots, and temporary objects as applicable.

Close the lifecycle only when each created resource is confirmed released or
explicitly retained with an owner, expiry, and accounted cost. An accepted delete
request or unreachable provider leaves cleanup pending. Keep its reservation and
independent cleanup path active, with an explicit handoff if observation cannot
continue. Settle known charges and retained exposure through the authoritative
ledger; distinguish recorded costs from billing that has not yet arrived.
