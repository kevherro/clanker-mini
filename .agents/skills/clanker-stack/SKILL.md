---
name: clanker-stack
description: Coordinate multi-step engineering and autonomous-system work in clanker-mini or systems operated with this pack. Use for clanker-stack or multi-step investigations, bug fixes, features, refactors, and unattended execution. Use a focused companion skill directly for a single operational question.
license: MIT
---

# clanker-stack

A compact adaptation of mestack for building and operating autonomous systems.
Own the requested outcome, choose a playbook, and finish with evidence. This
skill includes its engineering procedures and does not require mestack to be installed.

## Establish the task

Read applicable workspace instructions and inspect current work before editing.
Use the current session's documented tools and actual capabilities. Do not assume
a particular CLI, hosting provider, model, scheduler, or desktop integration.

For multi-step work, keep a short todo list in the available planning tool or
conversation. Establish:

- **Outcome:** the requested result and the observation that would prove it.
- **Target:** workspace, host, instance, revision, or run identity as relevant.
- **Scope:** allowed changes, existing authorization, constraints, and budgets.
- **Next unit:** one useful change or investigation with a check at its end.

Use evidence already present; do not turn these fields into a questionnaire.
Resolve missing facts through inspection when possible. Ask only when an unknown
changes the target or a consequential decision, and continue independent work.

## Choose the route

Read the relevant section of [the playbooks](references/playbooks.md). Use one
main route; change it when new evidence changes the task. Unattended work wraps
the applicable investigation, fix, build, or refactor route.

| Request | Main route | Companion when relevant |
| --- | --- | --- |
| Understand, explain, or assess without changes | Investigate | `clanker-system-map` for unfamiliar controls or state ownership |
| Correct a reported defect | Fix | `clanker-run-triage` when the symptom is a troubled live run |
| Add or change behavior | Build | `clanker-system-map` when the integration's real environment is unclear |
| Simplify structure while preserving behavior | Refactor | No operational skill required unless runtime evidence is needed |
| Recover a stalled or contradictory run | Operate | `clanker-run-triage` for diagnosis, effects, and bounded recovery |
| Audit an autonomous completion claim | Verify | `clanker-verify-outcome` for acceptance and actual destination evidence |
| Keep working while the user steps away | Unattended | The companion needed by the current unit, not every skill |

Resolve companions by name through the current skill catalog and read their
reported paths. Do not guess another machine's skill directories. If a companion
is unavailable, use the built-in route and name any missing capability or evidence;
do not install dependencies or abandon ordinary engineering work just to fill a
skill catalog. A single focused request can go straight to its companion.

## Engineering principles

Use a principle when it changes a decision, not as a ceremonial checklist.

- **Name the shape.** Before a behavior change, identify the data, ownership, and
  invariant. Use types, schemas, or explicit states to exclude invalid combinations.
- **Find the cause.** Tie a defect to evidence on the real path. Do not hide a
  failure with a fallback that makes incorrect results look successful.
- **Ship the smallest complete change.** Prefer deletion and direct code. Avoid
  speculative helpers and unrelated cleanup. Include affected callers and checks.
- **Keep one owner.** Point to authoritative facts rather than copying them.
  When replacing an internal interface, migrate callers and remove the obsolete path.
- **Validate boundaries.** Check external input at the edge, then trust the
  established internal shape. Do not silence type errors with invented guarantees.
- **Encode repeated rules.** Prefer a meaningful check or reusable tool when a
  constraint would otherwise need repeated instructions. Do not automate a one-off
  step unless doing so materially improves reliability.
- **Compare real alternatives.** For a consequential design with no precedent,
  compare two or three viable choices against the outcome before committing to one.
  Follow established patterns when they already solve the problem.
- **Preserve task identity.** Reconcile partial effects before replaying work.
  Keep logical operations distinct from attempts; retries must not duplicate effects.
- **Prove on the artifact.** Exercise the changed behavior or inspect its actual
  destination. Compilation, worker summaries, and activity alone do not prove success.

## Delegate without losing ownership

Only the top-level task spawns workers. If running as a delegated worker, stay
within the assigned scope and return findings; do not delegate again.

Parallelize independent investigations, checks, or isolated implementation slices
when useful. Give each worker its goal, relevant paths, allowed writes, check,
and expected report. Writers need separate worktrees or non-overlapping output
directories; otherwise keep edits serial in the parent. Preserve existing work.

Use available native delegation. Inherit the parent model unless the task provides
an applicable supported override. Report unavailable requested reviewers rather
than silently substituting. Without delegation, perform the work serially and
state the limitation only when it affects the claimed coverage.

The parent reads evidence and reviews diffs before integrating. Keep bulky logs
and artifacts at their source; bring back findings and pointers. A child's
completion message is not acceptance evidence.

## Carry authorization and scope forward

Proceed through reversible work already authorized by the task. Do not ask again
for actions the user has approved. A read-only request remains read-only even
when an obvious fix is found. Preserve unrelated changes and active workers.

Commit when requested. Publishing, pushing, merging, deployment, destructive
cleanup, and messages to others need authority for that action; a general request
to keep working does not grant all of them. When authority is missing, finish the
preparation first and present the concrete action and effect for approval.

## Finish with evidence

Report the outcome, what changed or was learned, the checks actually performed,
and material limits. Use verified paths, artifacts, or observations. Separate
restored progress from completed work and a correct final state from proven run
attribution. Name unfinished requirements and the next concrete step.

The adapted material retains its [MIT notice](LICENSE.txt).
