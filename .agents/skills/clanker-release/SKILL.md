---
name: clanker-release
description: Prepare and execute an authorized deployment, package publication, or release of an exact tested artifact, then verify the actual destination. Use for release preparation, rollout, publication reconciliation, and supported rollback; ordinary local code changes do not imply release authority.
---

# Release the artifact that was verified

Carry a tested artifact into the requested destination with a traceable identity
and an explicit recovery path. Use the project's documented release controls.
This skill does not provide a hosting account, publisher, or deployment adapter.

## Resolve the release contract

Inspect the existing release instructions, build and packaging configuration,
target environment, current deployed or published version, and supported interface.
Use the user's requested target and existing authorization. Resolve ambiguity
that changes the destination or effect before publication.

Keep a concise release record containing:

- Logical release identity, destination, and existing action authority.
- Intended source snapshot, including the disposition of uncommitted changes.
- Built artifact digest or immutable identity and relevant build environment.
- Acceptance evidence for that artifact and required target compatibility.
- Configuration and migration identities, excluding secrets.
- Current destination state, rollout boundary, and expected health observations.
- Recovery method, its prerequisites, and effects that cannot be reversed.

Treat code, configuration, schema, and data compatibility as parts of the release.
Passing local tests does not establish that the target configuration or migration
is compatible. Inspect the real release path instead of inventing one.

## Complete preparation before publication

Build or package the intended inputs using the project's supported reproducible
path. Preserve user work; do not reset the checkout to make the tree appear clean.
Inspect package contents for accidental credentials, unrelated files, and missing
runtime assets. Use documented preview or dry-run facilities when they provide
meaningful evidence without publishing.

Run the relevant acceptance checks on the artifact that will be released. Keep
its immutable identity with the evidence. If promotion rebuilds the artifact,
verify the rebuilt identity and relevant behavior before calling it equivalent.
An unchanged version label alone does not prove identical contents.

Prepare the exact target, artifact, command or supported action, expected effects,
health check, and recovery path. If publication authority is missing, present
that concrete release for approval while completing independent preparation.
Do not request approval again when the user or standing policy already authorized
this release within the stated scope.

## Confirm that recovery is real

Inspect the supported rollback, roll-forward, traffic shift, or package correction
mechanism before rollout. Confirm that the previous artifact and required
configuration are available. Identify data changes the old code cannot safely
read and whether a tested recovery can restore compatibility.

A snapshot name alone does not prove recoverability; rely on relevant restore
evidence where recovery depends on it. Do not promise instant rollback when
irreversible migrations, external messages, or cached client versions prevent it.
Choose a compatible rollout boundary or prepare a forward repair when rollback
cannot meet the task's requirements. Missing consequential prerequisites should
be resolved before exposing the release, not discovered after failure.

## Publish once, then reconcile

Recheck destination state immediately before the authorized mutation. A newer
release or another active owner can invalidate preparation; use the platform's
concurrency or conditional-update controls where supported.

Publish or promote the recorded artifact through the supported interface. Keep
the logical operation identity and returned deployment, package, or release ID.
An accepted request proves submission only. If acknowledgment is lost, inspect
the destination or documented operation status before submitting another release.
Replay only with verified idempotency, or evidence that publication is absent and
the prior attempt cannot still commit. Do not convert uncertainty into a new
version or duplicate publication.

Use any requested staged rollout and observe its actual boundary before expanding.
Do not add unrelated migrations, permission changes, notifications, or releases
to complete the selected publication path.

## Verify the destination and close the release

Check that the actual destination serves or exposes the intended artifact identity.
Exercise the relevant user path with the target's real configuration and inspect
health over the period needed by the release contract. A successful uploader,
deployment command, or generic health endpoint alone may not prove the feature.

If rollout fails, use an already authorized recovery only when its prerequisites
still hold. Recheck data compatibility before rollback; do not automatically
restore old code over an incompatible migration. Stop further expansion and
preserve evidence while preparing the concrete safe recovery if authority or
feasibility is missing. Verify the destination again after any recovery.

Record the observed release identity, destination, health evidence, and final
rollout or recovery state. Retain artifacts and recovery resources according to
their existing policy; remove only task-owned temporary resources.

Report preparation, publication, and destination verification separately. Name
any remaining health uncertainty, incomplete rollout, or irreversible effect.
Do not claim the release succeeded while its actual destination is unverified.
