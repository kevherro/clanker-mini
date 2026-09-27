---
name: clanker-verify-outcome
description: Audit an autonomous run's completion claim against the original request and actual persisted or downstream results. Use when deciding whether unattended work is done, especially with stale artifacts, partial outputs, or a worker's self-reported success.
---

# Verify an autonomous outcome

Decide whether the requested outcome happened for the intended task and target.
A successful command or a worker's summary is evidence about execution, not by
itself evidence that the user's requested result exists.

## Define acceptance independently

Read the original request and subsequent scope changes before using the worker's
completion summary to guide inspection. If the request is unavailable, obtain it
or mark acceptance unverified; do not let the worker define its own success.

For each material requirement, identify the expected observable result, its
destination, and the evidence needed to distinguish success from a plausible
failure. Reuse an existing application verification interface when it exercises
the requested behavior. Do not add requirements the user did not ask for.

## Bind evidence to the correct work

Establish task/run identity, target environment, and relevant input or revision.
Inspect the actual artifact or destination before accepting a completion claim.

- A matching filename and recent timestamp do not establish identity. Check
  content, embedded provenance, object identity, or another relevant binding.
- Establish attribution through a run ID, input identity, before/after evidence,
  or an equivalent link. A correct current state can verify the desired outcome
  without proving that this particular run caused it; keep those claims separate.
- Check completeness across the requested set. A manifest is not enough unless
  it is reconciled with actual objects. Sampling supports only the sampled scope.
- Follow the requested effect to its endpoint. Creating a local export does not
  establish delivery, import, publication, or downstream consumption.
- Two reports copied from one unchecked status flag are one source of evidence.
  Prefer independent observation of persisted state or consumer-visible behavior.

Choose the cheapest meaningful disconfirmation check: open an artifact and
inspect its contents, compare expected and actual object identities, exercise a
user path, or inspect the downstream record. Prefer read-only inspection. If a
check would create another external effect, use an established isolated test
surface within the current authorization or report the missing evidence.

Allow for documented consistency delays when checking a remote destination.
Poll only within a justified bound. An unavailable destination is unverified;
authoritative evidence that the expected object is absent can establish failure.

## Give an evidence-based verdict

Use a compact acceptance table: requirement, observation, evidence pointer, and
verdict. Keep contradictions visible, including a worker reporting success while
the destination contains only some of the requested outputs.

| Verdict | Meaning |
| --- | --- |
| Verified | All material requirements have current evidence for the intended target |
| Partial | Some required outcomes are verified; others are missing, failed, or unverified |
| Failed | Evidence establishes that the required outcome was not achieved, with no verified subset of the requested outcomes |
| Unverified | Available evidence cannot establish the required outcome |

A verified intermediate step counts toward Partial only when it is itself a
requested outcome. For a delivery-only request, a correct local file and an
inaccessible destination leave delivery Unverified.

A missing material check prevents a fully verified verdict. When several
requirements differ, retain their individual verdicts and explain the aggregate.
State any limit on attribution, coverage, freshness, or access beside the claim
it qualifies. Include the specific remaining action or observation needed.

Verification does not repair, retry, publish, or change the system's task status
unless the current request or existing authorization covers that operation.
Report the result without rewriting the evidence to agree with the worker.
