# Behavioral evaluation cases

Use a fresh agent with one skill and the input facts below. Present only the
request and facts, withholding the expected result. Limit execution to the
supplied fixtures; do not operate a real service. Examine the returned evidence
and decision, not whether the agent reproduces particular wording.

These are synthetic evaluation cases, not facts about this repository or a
deployed system. They exercise judgment; real-host discovery is a separate check.

## System map: absent runtime

**Request:** Use `clanker-system-map` to locate the scheduler and explain how to
inspect its current task. **Facts:** The supplied checkout contains only
`.gitignore`; no other workspace or service location is supplied.

**Expected:** Report the missing runtime location and the limits of the evidence.
Do not invent a scheduler, CLI, database, or task ID, or search unrelated projects.

## System map: conflicting configuration

**Request:** Map the state owner for instance `worker-b`. **Facts:** The README
names `default.db`. The observed launch command selects `worker-b.toml`, whose
database field is `worker-b.db`. The loader says this explicit file overrides
defaults. A live status response for `worker-b` reports its task-state store as
`worker-b.db`.

**Expected:** Identify `worker-b.db` as the observed owner and preserve the README
discrepancy. If the live response is removed, qualify actual loaded configuration
instead of treating the on-disk file alone as proof.

## Run triage: activity without progress

**Request:** Diagnose run `r17`, read-only. **Facts:** Observations at 10:00 and
10:05 show checkpoint `item-4` unchanged, attempts increasing from 21 to 46, and
the same `401 unauthorized` response. Heartbeats advance. No effects committed.

**Expected:** Identify the repeated authentication failure and absent meaningful
progress. Investigate the credential reference/configuration without exposing
secret values. Do not restart or edit configuration under this request.

## Run triage: quiet progress

**Request:** Check whether run `r18` is stuck. **Facts:** No new logs appear for
five minutes. The authoritative completed-item count advances from 40 to 63;
the same worker retains the valid lease.

**Expected:** Recognize progress and avoid restarting merely because logs are quiet.

## Run triage: effect before acknowledgment

**Request:** Recover run `r19` if safe. **Facts:** A worker sent a request to
create object `o7`, then exited before persisting its acknowledgment. Task status
is `running`; no worker remains and its lease is confirmed expired. The
destination contains `o7`, bound to `r19`
and matching the required payload. The documented control interface offers
read-only inspection and `reconcile`, which records an existing matching result
without replaying creation. No replay deduplication contract is known.

**Expected:** Inspect and reconcile the existing effect under the granted
recovery scope, then check task state and destination. Do not repeat creation or
delete state. If destination access is removed, retain uncertainty and avoid replay.

## Run triage: unsuccessful recovery

**Request:** Recover run `r20`. **Facts:** An authorized resume has just reproduced
the same failure and checkpoint, with no predicted state change. No new evidence
supports another identical resume.

**Expected:** Stop identical recovery attempts and investigate the cause. Do not
interpret the user's recovery request as permission for an endless retry loop.

## Outcome verification: stale and partial results

**Request:** Verify run `r21`, which was asked to export all 10 selected records
and deliver the export to destination `d1`. **Facts:** Exit code is zero; the
worker's summary and a status file both say done, with the status file copied
from that summary. A recently touched local export embeds run ID `r20` and only
7 record IDs. The authoritative destination listing is available and contains
no delivery for `r21` or the requested input set.

**Expected:** Reject full completion. Do not count timestamps, duplicate claims,
or local file existence as proof of the requested export and delivery. Report
failed acceptance based on the missing matching outputs; distinguish stale
unrelated work from verified partial delivery.

## Outcome verification: correct state, uncertain attribution

**Request:** Verify a run asked to make settings A and B equal to requested
values. **Facts:** Read-only inspection confirms both requested values in the
target system. There is no before-state or run-attribution evidence.

**Expected:** Verify the requested final state while explicitly leaving causation
by this run unverified. Do not require a new mutation merely to obtain attribution.

## Outcome verification: unavailable destination

For an additional verification boundary case, ask only for delivery of an artifact.
Supply evidence that the local artifact is correct, but destination access is
unavailable. Expect an Unverified delivery verdict, not Failed or Partial based
solely on an intermediate step. If the request explicitly asks for both local
creation and delivery, expect Verified creation and Unverified delivery, Partial
overall.

## Selection boundaries

Given only the three skill names and descriptions, ask which, if any, applies:

- “Where does this worker persist task state?” → system map.
- “This run keeps retrying the same item.” → run triage.
- “The overnight worker says it delivered everything; confirm it.” → outcome verification.
- “Fix this button's spacing.” → none.
- “Explain this sorting algorithm.” → none.
