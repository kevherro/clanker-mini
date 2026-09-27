---
name: clanker-run-triage
description: Diagnose an autonomous run that stalls, retries repeatedly, duplicates work, or reports contradictory status. Reconcile partial effects before a bounded recovery; use for a specific troubled run, not routine monitoring or general code review.
---

# Diagnose and recover a run

Determine what happened to one logical task, including its attempts, worker
ownership, and externally visible effects. Diagnosis alone does not authorize
recovery; use any recovery authority already granted by the current request.

## Capture evidence before changing state

Establish the target host, instance, task ID, attempt IDs, original requested
outcome, and supported control interface from supplied evidence or inspection.
If these cannot be resolved, report the missing identity before choosing an action.

Inspect authoritative task state, the last meaningful checkpoint, the relevant
error, worker ownership, and the effect destination. Distinguish event time from
observation time. Retain the evidence that a restart or retry could erase.

When progress is unclear, compare two observations at an interval justified by
the operation's expected duration or documented lease/retry timing. Respect the
available execution time; a short observation window may leave the answer unknown.
Checkpoints or completed work items can prove progress. Heartbeats, CPU usage,
log volume, and increasing retry counts establish activity only.

## Choose the diagnosis that the evidence supports

| Observation | Interpretation and next move |
| --- | --- |
| Meaningful checkpoint advances | Progressing; do not restart because logs are quiet |
| Explicit dependency wait or future retry time | Waiting; inspect the prerequisite and its expected release condition |
| Same item and failure repeat, with no meaningful advance | Retry loop; investigate the repeated cause before another attempt |
| Reported owner differs from live ownership | Ownership conflict; inspect documented lease/claim semantics before intervening |
| Destination contains the requested effect, status remains unfinished | Possible lost acknowledgment; reconcile identity and completeness before retrying |
| Explicit terminal failure with no continuing owner | Failed attempt; inspect its cause and any partial effects |
| Signals are absent, stale, or inconsistent | Unknown; name the observation needed to distinguish the remaining explanations |

Neither process existence nor one expired timestamp settles ownership on its own.
A dead worker can leave a valid lease; a quiet worker can still be doing useful work.

## Reconcile effects before recovery

For each side-effecting step, establish whether its result is confirmed present,
confirmed absent, partial, or unknown. Match the logical task and destination
object, not just a filename or a worker's success message.

If an effect may have committed before its acknowledgment was recorded, inspect
the destination or use the documented reconciliation interface. Replay only when
the system provides a verified idempotency/deduplication contract, or evidence
establishes the effect was absent. Do not invent a new idempotency key on retry:
that can turn one logical operation into two. Unknown effects are a reason to
gather evidence, not to reset state until the dashboard looks clean.

## Make a bounded recovery when authorized

Choose the smallest supported action that addresses the observed cause. State
its target, precondition, expected state change, and check before executing it.
Recheck current ownership immediately before mutation. Use the supported control
interface; do not edit internal state or remove locks to bypass its lifecycle.

An existing instruction to recover is sufficient within its scope. A read-only
request permits diagnosis and a proposed action only. If authority is missing,
present the concrete action and its effect for approval, while continuing useful
inspection. Do not expand recovery into deployment, deletion, or new external work.

After the action, inspect both task progress and the destination. If the same
failure recurs or the predicted change does not occur, stop identical retries
and revise the diagnosis. Follow explicit runtime retry limits when they exist;
do not manufacture an endless recovery loop.

Report the diagnosis, evidence and uncertainty, partial effects, action taken
or proposed, and observed result. Separate restored progress from a completed task.
