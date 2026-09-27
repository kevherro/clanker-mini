---
name: clanker-continuation
description: Arrange and verify a durable wakeup for authorized work that must resume after this session, or recover a previously registered continuation. Use for scheduled follow-up, event-driven resumption, and interruption recovery; a saved plan alone is not background execution.
---

# Resume work through a real wakeup

Bind an actual scheduler or event subscription to a durable task record, then
resume from live evidence. Preserve the requested outcome and existing authority
across interruptions. This skill does not itself provide a scheduler or keep an
agent running after the session ends.

## Identify the continuation mechanism

Inspect the available scheduler, event source, job runner, or documented tool for
the requested target. Prefer the system's existing mechanism and task record.
Use its documented registration, inspection, delivery, and cancellation behavior;
do not substitute a session sleep or child agent for durable scheduling.

Resolve the wake condition, target task or executor, time zone when relevant,
deadline or expiry, and the observation that ends the work. Preserve the user's
notification intent. A request to keep checking does not imply a message on
every unchanged observation or authority to perform new external actions.

If no durable mechanism is available, finish work feasible in this session and
save a usable checkpoint when appropriate. Explain what must be connected before
resumption can happen. Do not report that follow-up is scheduled or that work
will continue merely because its instructions have been written down.

## Save the checkpoint before registering

Use the authoritative task store or supported durable location. Keep the record
small enough to inspect and sufficient to reconstruct the next safe action:

- Logical task identity, requested outcome, target, and actual output destination.
- Input snapshot and relevant environment or artifact identities.
- Existing authority and its scope, budgets, original deadline, and constraints.
- Last verified unit, evidence pointers, unresolved effects, and known attempts.
- Current owner or claim, supported claim semantics, and the next bounded unit.
- Wake condition, terminal condition, delivery identity, and registration state.

Point to authoritative evidence instead of copying changing state into prose.
Keep secrets in their supported store and reference them by identity. Persist
partial effects before relying on a later wake to finish or reconcile them.
Neither a checkpoint nor a scheduler prompt grants additional authority.

## Register and verify the wakeup

Inspect existing registrations for this logical task before creating another.
Use a stable registration identity or the scheduler's supported deduplication
mechanism. Reuse or update a matching registration within the requested scope.
If a create request times out, reconcile it before retrying with a new identity.

Register only the requested condition and lifetime. Where available, prefer a
bounded event or one-time wake to polling; use recurring checks when the task
needs them. Do not extend deadlines or recurrence indefinitely on each retry.

Read back the actual registration and verify its enabled state, target, condition,
expiry, and checkpoint reference. Inspect the next delivery or event binding
through the documented interface. Record its returned identity and verification
evidence in the task record. An accepted request without readable state may leave
registration unverified; say so rather than creating duplicate registrations.

## Resume from ownership and live state

Treat delivery as a hint to inspect the task, not an instruction to replay its
last command. Reload the checkpoint and check the real destination, current
authority, deadline, input identity, and whether the task already completed.

Acquire the supported exclusive claim or generation before advancing shared task
state. Duplicate deliveries should observe an existing owner or completed unit
and do no extra work. A local lock cannot establish ownership across independent
hosts. An expired claim alone does not prove an old worker can no longer act.
Use the runtime's fencing or reconcile continuing work before taking over.

For an uncertain external effect, preserve its logical operation identity and
inspect the destination or documented reconciliation interface. Replay only with
a verified idempotency contract, or evidence that the effect is absent and the
earlier attempt cannot still commit. Never erase uncertainty by resetting state.

Execute the next bounded unit, verify its actual result, and save the new
checkpoint. Check ownership before further mutation. If scope, inputs, or
authority changed, resolve that change before performing dependent work.

## Retire the continuation

When the terminal condition, cancellation, or expiry is reached, stop scheduling
new work and retire this task's registration using supported controls. Verify
its disabled or removed state. A queued delivery can still arrive; the durable
terminal state must make it a no-op before any new effects.

Keep incomplete cleanup or uncertain effects visible after the task stops. If
an already authorized independent cleanup controller must continue, retain its
identity and expiry separately from the finished work registration. Do not leave
the main task recurring as an undocumented substitute for cleanup ownership.

Report the verified registration or its absence, next condition or delivery,
checkpoint location, and remaining work. On completion, report both the outcome
evidence and whether the wakeup was successfully retired.
