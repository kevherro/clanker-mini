# Playbooks

Read only the route relevant to the task. The workspace's existing commands,
tests, and operating interfaces supply the concrete mechanics.

## Investigate

1. State the question and the evidence that would settle it.
2. Trace the relevant entrypoint, data, and state owner. Use system mapping for
   an unfamiliar operational environment; ordinary code questions can stay in source.
3. For historical questions, inspect reachable history or documentation and
   distinguish recorded intent from inference.
4. Return the supported answer and remaining unknowns. Stay read-only; describe
   an obvious fix without applying it unless the request also authorizes changes.

## Fix

1. Reproduce the reported behavior on the real interface or a representative
   local regression case. Record expected and observed results. If reproduction
   is unavailable, investigate with existing evidence and state that limit rather
   than inventing a cause or claiming the fix is proven.
2. Trace the failure to its cause. Name the invariant if it was missing. Use run
   triage before touching a troubled live worker or replaying side effects.
3. Make the smallest complete correction. Preserve unrelated work and avoid
   bundling a structural cleanup unless it is necessary for the fix.
4. Rerun the original case and one nearby case that could expose a wrong fix.
   Use a regression test when it protects meaningful behavior. Report verification
   as incomplete if the affected interface cannot be exercised.

## Build

1. Trace the existing path the behavior will join. If none exists, identify the
   new entrypoint and boundary without inventing an existing implementation.
2. State the data shape, ownership, invariant, and observable acceptance case.
3. Implement the smallest complete unit, including the affected integration and
   callers. Prefer existing project conventions over a parallel framework.
4. Exercise the requested behavior and a meaningful failure or boundary case
   using the real interface or established harness. For skills, check discovery
   and realistic decisions; parsing their Markdown alone is insufficient.
5. Continue through required units until the requested result is verified or a
   concrete blocker remains. Commit only within existing user authorization.

## Refactor

1. Name the behavior that must remain unchanged and the boundary being moved.
2. Establish a check on the existing behavior before restructuring. Preserve a
   single owner for moved facts; avoid introducing wrappers with no useful role.
3. Make the structural change. Separate intended behavior changes into their own
   verifiable unit so they cannot hide inside the refactor.
4. Exercise the same behavior afterward and inspect affected callers. A clean
   build alone does not establish preserved behavior.

## Operate

Use `clanker-run-triage` when available; it owns the detailed procedure. If it is
unavailable, identify the run, authoritative state, current ownership, progress
evidence, and effect destination. Missing signals leave uncertainty; activity is
not progress. Reconcile any effect that may already exist before considering replay.
Replay only when the original effect is confirmed absent and cannot still commit,
or a verified idempotency contract makes replay safe. Unknown effects require
further inspection.

Choose a supported action within the granted scope, with an observable expected
change and a retry bound. Do not bypass internal locks or invent an idempotency
contract. Recheck ownership before mutation and destination state afterward. If
the predicted change does not occur, revise the diagnosis instead of repeating
the same action. A diagnosis-only request stops before recovery.

## Verify

Use `clanker-verify-outcome` when available; it owns the detailed acceptance audit.
Otherwise derive acceptance from the original request, inspect actual results for
the intended target and inputs, and distinguish execution reports from independent
evidence. Check the requested destination and completeness; stale or unrelated
artifacts do not count. Report verified, partial, failed, or unverified acceptance
with the supporting observations. Do not repair during an audit unless authorized.

## Compute

Use `clanker-compute` when available; it owns placement and remote resource
lifecycle. Assess aggregate demand before heavy execution, including overlapping
workers and scratch/output storage. Prefer bounded local work when it fits.

If the companion is absent, reduce concurrency or workload size within available
capacity, or use an established remote runner whose authorization, cost bounds,
input identity, and independent cleanup are already verified. Otherwise prepare
a remote plan and report the missing controls. Do not invent paid provisioning
commands or equate a connected account with unlimited spending authority.

## Unattended

1. Establish the finish condition, existing authority, resource/time bounds, and
   stop rule. Use supplied limits; otherwise choose a bounded plan proportionate
   to the task. Do not interpret silence as permission to expand scope.
2. Use a suitable free checkout or isolated output location. Account for existing
   changes and active work before selecting it; never reset a dirty tree to start.
3. Work in verifiable units using the applicable route above. Keep a compact
   checkpoint in the task's existing record: target identity, last verified result,
   evidence pointers, unresolved effects, and next action. Recheck live state on resume.
4. On a repeated failure without new evidence, change the investigation or stop
   that path. Continue independent work when useful. Honor the task's budgets and
   stop when the finish condition holds or the stated stop rule fires.
5. Use a documented wake or continuation mechanism only when available and within
   the user's request. Without one, work in the active session and report what
   remains; never promise work will continue after execution ends.
6. At exit, leave a clear result or handoff with completed requirements, evidence,
   remaining work, and the reason for stopping. Do not mark uncertain work complete.
