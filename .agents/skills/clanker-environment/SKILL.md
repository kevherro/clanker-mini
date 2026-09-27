---
name: clanker-environment
description: Prepare and verify an isolated, reproducible execution environment from a project's real manifests and runtime requirements. Use when setting up a worker, reproducing a build, or resolving missing dependencies or services; compute placement and cloud provisioning are separate concerns.
---

# Prepare the execution environment

Make the chosen executor capable of running the requested task on the intended
inputs. Bind the environment to those inputs and prove it with a representative
check before committing the full workload. This skill supplies a procedure, not
a package manager, container runtime, or remote executor.

## Establish the environment contract

Read the project's setup instructions, manifests, lockfiles, existing CI or
container configuration, and relevant runner configuration. Resolve conflicts
against the path the task will actually use. Do not invent a dependency list from
imports when an authoritative manifest exists.

Record the smallest useful environment identity:

- The intended source snapshot, including authorized uncommitted inputs.
- OS, architecture, runtime and toolchain versions, and required accelerators.
- Dependency manifests and lockfile identities; installation mode and registry.
- Required services, schema or fixture versions, and permitted network access.
- Runtime configuration and secret references, without recording secret values.
- Working directory, output destination, and the command that exercises readiness.

Distinguish an exact reproducible environment from a best-effort reconstruction.
An absent lockfile or unpinned image may be usable for exploration, but does not
justify claiming another worker can reproduce the same dependency resolution.

## Choose an isolation boundary

Reuse a suitable project or runner environment when its ownership and identity
are known. Otherwise choose the smallest supported isolation that fits the task:
a dedicated work directory, language environment, container, or disposable worker.
Inspect available capabilities before selecting an interface or command.

Keep this task's mutable files, service instances, ports, caches that require
exclusive access, and output paths separate from other active work. A shared
read-only dependency cache can be reused when its integrity and key are adequate.
Do not reset the user's checkout, replace global toolchains, or stop unrelated
services to make setup succeed. Preserve existing modifications.

Check aggregate setup and workload resource demand before large downloads,
image builds, service startup, or test fan-out. Compute placement belongs to the
actual runner or, when available, `clanker-compute`; environment isolation alone
does not add capacity or make a workload portable across operating systems.

## Prepare from declared inputs

Use the project's documented locked or frozen installation mode when available.
An installation that wants to rewrite the lockfile is a changed input, not a
routine reproduction step. Diagnose the mismatch before allowing the rewrite;
make dependency changes only when they fall within the requested work.

Run setup hooks only within the task's existing execution and data authority.
For remote workers, transfer only intended inputs and necessary data. Inject
secrets through the supported runtime mechanism; keep them out of images, source
snapshots, logs, and reusable artifacts. Do not copy an entire home directory.

Start task-owned dependencies through supported controls and verify readiness
at their actual endpoints. Use isolated fixtures or the authorized dataset.
Never seed, migrate, or clear a live shared database merely because a local
setup recipe mentions those actions. Treat data preparation as a separate effect
with its own destination and existing authority.

Record concrete versions and resolved identities after setup. A cache hit or
successful package installation proves only that phase, not application readiness.
If a prerequisite cannot be satisfied, preserve completed preparation and identify
the missing capability rather than repeatedly reinstalling the same environment.

## Prove readiness in the same environment

Run a small representative path using the same executor, user, working directory,
runtime configuration, services, and inputs as the intended workload. Check the
output itself and a relevant dependency interaction; a version command alone does
not establish readiness for a build or integration task.

Use the real required platform when platform behavior matters. A successful
Linux build cannot establish macOS UI or attached-device behavior. If only a
separable part can run here, state that boundary and verify that part.

Keep the resulting environment identity with the run or artifact record. Reuse
it only while the relevant source requirements, toolchain, dependencies, service
state, and runtime configuration remain compatible. Recheck the affected path
when one of those inputs changes; do not discard unrelated valid setup.

## Retain or retire intentionally

Collect required outputs before removing disposable state. Clean up only resources
owned by this task, through their supported controls, or record an intentional
retention owner and expiry. A terminated worker does not prove attached storage
or external services were removed.

Report the prepared environment, source and dependency identity, readiness check,
output location, and any unmet platform or reproducibility requirement. Distinguish
environment readiness from completion of the user's full workload.
