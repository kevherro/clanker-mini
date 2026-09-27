---
name: clanker-system-map
description: Locate the authoritative controls, state, and evidence for an unfamiliar autonomous system. Use when entering a new environment or when documentation and a running instance disagree, before operating or diagnosing it.
---

# Map an autonomous system

Produce the smallest evidence-backed map needed for the requested operation.
This skill inspects a system; it does not start workers or change configuration.

## Establish the boundary

Identify the requested operation, workspace, execution host, and target instance.
Use the supplied environment and available tools to establish those identities.
A local checkout, a remote worker, and a desktop session may have different
configuration, credentials, skill roots, and working directories.

If the supplied workspace contains no runtime, report that evidence and the
missing location. An empty directory is not permission to invent a service,
search unrelated workspaces, or install an assumed runtime. Continue only with
independently useful facts from the supplied scope.

## Trace one operational path

Follow the requested operation through:

`entrypoint → effective configuration → task identity → state owner → effect destination`

Inspect repository instructions, launch definitions, configuration loaders,
documented command help, and existing status interfaces as needed. Read source
only far enough to settle a specific uncertainty. Do not run an unfamiliar
entrypoint merely to discover its behavior; even a presumed help command may
start work unless its interface is established.

Record these facts with file, command-output, or tool-result evidence:

| Fact | What must be distinguished |
| --- | --- |
| Control | A supported status/cancel/resume interface versus an internal file |
| Configuration | Declared defaults versus overrides actually loaded by this instance |
| Task identity | The logical task versus its individual attempts and worker processes |
| State owner | The authoritative queue, database, or checkpoint versus a cached display |
| Progress | A task-relevant change versus heartbeats, log traffic, or retry counts |
| Destination | Where the requested effect is persisted or consumed |

Resolve conflicting configuration using the loader's precedence and live
instance evidence. A recently edited file does not prove a running worker loaded
it. When effective configuration cannot be observed, label it inferred or unknown.
Report the names and origins of credential settings, never secret values.

## Finish when the next decision is possible

Stop once the operator can identify the appropriate control, authoritative state,
progress signal, and destination for this operation. Do not expand into a general
architecture audit. Missing observability is itself a useful finding.

Return a concise map with:

- The host, workspace, instance or run identity, and observation time.
- The operational path, with an evidence pointer for each established fact.
- Configuration conflicts, missing capabilities, and remaining unknowns.
- The next useful inspection or supported action, including any prerequisite.

Keep observations in the task's report or existing run record. Do not bake live
PIDs, paths from one machine, or current status into this reusable skill. Recheck
instance identity and effective configuration before using an old map to mutate state.
