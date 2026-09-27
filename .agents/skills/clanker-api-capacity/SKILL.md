---
name: clanker-api-capacity
description: Bound and recover API workloads through the actual request client or queue. Use for throttling, request or token capacity, concurrency saturation, quota failures, and repeated remote-call retries; adding compute alone does not increase provider API limits.
---

# Control API demand at the request boundary

Make the authorized workload fit the service's real limits while preserving
request identity and result quality. Use the actual provider/client/queue controls.
This skill supplies no proxy, account entitlement, or automatic model migration.

## Find the limit and its owner

Inspect the failing request's service, endpoint or model, account or project,
status, provider error code, relevant response headers, and request identity.
Redact credentials and sensitive payloads. Check current documented behavior
before relying on provider-specific retry or quota semantics.

Inspect the client retry configuration and any queue, SDK, worker, or gateway
that can also retry or fan out. Identify where requests are actually admitted.
Multiplying retries at several layers can turn one task into a large workload.
Keep one coordinated retry policy or account explicitly for each layer's bound.

| Evidence | Next decision |
| --- | --- |
| Transient throttling with a documented retry window | Pace admission and retry within the task's attempt and time limits |
| Exhausted quota, billing restriction, or account entitlement failure | Resolve the prerequisite or wait for a verified reset; avoid rapid retries |
| Authentication, permission, invalid input, or unsupported feature | Correct the specific cause within scope; retrying unchanged cannot fix it |
| Timeout, disconnect, or uncertain acceptance | Reconcile the original operation before repeating effects |
| Local queue saturation while the provider is healthy | Bound local concurrency and queue growth; inspect consumers and useful progress |

HTTP status alone may not distinguish quota exhaustion from a short rate window.
Do not infer a reset time or retryability from a generic error string when a
documented code or account observation can settle it.

## Bound aggregate admission

Resolve the applicable request, token, byte, concurrency, queue-size, and cost
allowances from the service and existing task policy. Account for all workers
sharing that policy scope, including retries, batches, and background consumers.
Reserve conservative output capacity where output size is not known in advance.

Use the authoritative shared limiter or queue when available. Per-worker counters
cannot enforce an account-wide allowance. If competing demand is unobservable,
state that uncertainty, lower this task's demand, and avoid claiming a guaranteed
global limit. Keep task-owned controls separate from unrelated consumers.

Choose the smallest effective change: fewer concurrent calls, smaller batches,
bounded queueing, reduced duplicate requests, or pacing through the existing
limiter. Preserve the requested content and quality. Batching is useful only when
the real endpoint supports it and partial results can retain individual identities.

Do not switch accounts, models, regions, or providers to evade a limit. A fallback
must be authorized, supported, and satisfy the same task requirements, including
data handling and output quality. A new VM adds workers, not service entitlement.

## Retry one logical operation safely

Set bounded attempts and elapsed time consistent with the task's deadline and
allowance. Respect the provider's documented retry timing; add suitable backoff
and jitter through the real client or queue. A wait that exceeds the remaining
deadline should become a deferred or failed item, not an unbounded blocked worker.

Keep logical operation identity separate from transport attempts. Use the real
idempotency contract when supported, preserving its key and payload rules across
retries. Do not assume an arbitrary header deduplicates a request or invent a new
key for each retry. Treat the provider's deduplication retention window as a limit.

After an unknown acknowledgment, inspect the destination or operation status.
Retry a side-effecting call only with a verified idempotency guarantee, or proof
that the original effect is absent and its attempt cannot still commit. A read
request may still consume quota or money when its response is lost; account for
that uncertainty before resubmitting it.

Record per-item results in batch work. Retry eligible failed items while preserving
confirmed successes; do not rerun the whole batch to simplify bookkeeping. Stop
identical retries when the error is permanent or the bound is reached. Preserve
the failed item and reason so a later authorized attempt can resume deliberately.

## Verify the changed request path

Exercise a small representative workload through the same client, queue, and
identity scope as the real work. Observe successful outputs, admission rate,
in-flight calls, retry count, queue movement, and relevant provider usage evidence.
A quieter error log does not establish progress if requests are merely stuck.

Verify the intended failure behavior as well: a bounded throttle can recover;
a permanent quota error stops; an uncertain effect is reconciled; and duplicate
delivery cannot repeat a confirmed result. Use isolated fixtures or documented
test facilities when real calls would spend money or change external state.

If the request path cannot be controlled from the available environment, identify
the exact limiter, configuration, or access that is missing. Continue feasible
preparation without claiming pacing or retries were changed.

Report the observed limit, controls actually applied, completed and deferred work,
remaining retry or cost allowance, and output evidence. Distinguish provider usage
observations from estimates and acknowledge uncertain charges after lost responses.
