# clanker-mini

A small skill pack for building and operating autonomous systems. A tailored
mestack dispatcher coordinates engineering work; eight focused skills handle
environment setup, capacity, recovery, continuation, releases, and verification.
An optional local operations toolkit supplies durable records and executable
checks without assuming a cloud provider or scheduler.

| Skill | Use it for |
| --- | --- |
| [clanker-stack](.agents/skills/clanker-stack/SKILL.md) | Coordinating investigations, fixes, features, refactors, and unattended work with evidence at each step |
| [clanker-system-map](.agents/skills/clanker-system-map/SKILL.md) | Finding the control interface, effective configuration, state owner, and result destination |
| [clanker-run-triage](.agents/skills/clanker-run-triage/SKILL.md) | Distinguishing progress from retry loops and reconciling partial effects before recovery |
| [clanker-verify-outcome](.agents/skills/clanker-verify-outcome/SKILL.md) | Checking unattended completion claims against actual artifacts and downstream results |
| [clanker-compute](.agents/skills/clanker-compute/SKILL.md) | Keeping heavy work within local capacity or running it on authorized remote compute with bounded cost and cleanup |
| [clanker-environment](.agents/skills/clanker-environment/SKILL.md) | Preparing isolated dependencies, services, and fixtures, then proving the environment can run the intended work |
| [clanker-continuation](.agents/skills/clanker-continuation/SKILL.md) | Registering a real wake, preserving a durable handoff, and safely resuming after interruption |
| [clanker-api-capacity](.agents/skills/clanker-api-capacity/SKILL.md) | Pacing shared API demand, diagnosing quotas, and bounding safe retries |
| [clanker-release](.agents/skills/clanker-release/SKILL.md) | Preparing and performing authorized releases of the exact tested artifact, with destination checks and a viable recovery path |

Use `clanker-stack` for multi-step engineering work. It includes its own playbooks
and routes to the focused skills when relevant, with fallbacks if they are absent.
It does not depend on a global mestack installation. The focused skills can also
be used directly; there is no requirement to run the whole pack in sequence.
Supply the target workspace or host and, for run-specific work, the task identity
and original request.

## Use in Codex

The skills live in `.agents/skills` for repository discovery. Open Codex in this
checkout and invoke any name in the table with `$`, such as `$clanker-stack` or
`$clanker-environment`. Their descriptions also support automatic selection.

To make them available in other projects, link or copy the individual skill
directories into your user skill directory, normally `~/.agents/skills`. Check
for existing names before adding links. This repository does not install them
globally or modify Codex's bundled `.system` skills.

See the [official discovery documentation](https://learn.chatgpt.com/docs/build-skills#where-to-save-skills).

## Remote compute

`clanker-stack` checks resource placement before heavy work and wider fan-out.
`clanker-compute` prefers a bounded local workload when sufficient, then considers
existing workers, managed jobs, or remote VMs. Supply standing authority for the
allowed account/regions, workload and data, sizes, cost/concurrency limits,
deadlines, and retention. Within that policy, the skill proceeds without repeated
approval requests.

The [remote execution contract](.agents/skills/clanker-compute/references/remote-execution.md)
defines the required controls and recovery behavior. It uses the connected
provider's documented tools or an established adapter; this pack does not ship a
provider-specific provisioner or enforce provider billing. Resource deadlines,
shared reservations, and cleanup must be enforced by the actual runner/controller,
including when the agent disconnects. Examples in evaluations grant no live cloud
spending authority.

## Supporting operations

The [local operations contract](OPERATIONS.md) documents a Python standard-library
CLI for task claims and checkpoints, immutable artifacts and conditional promotion,
and shared capacity/cost reservations with launch reconciliation and cleanup.
It also includes an expiry controller that can run independently under a real
supervisor. No controller is installed or started by adding these files.

Use an existing runtime when it already owns these records. The optional toolkit
requires all participating processes to share one store on one host's local disk.
It does not enforce provider bills or stop external side effects from stale
workers. Its cleanup adapter must be implemented against the chosen executor,
and its controller must be registered and verified on an appropriate host before
unattended resource cleanup can be claimed. Copying only the skill directories
does not copy or install the toolkit.

## Check changes

Validate each skill with Codex's skill-creator validator, then check discovery
from this checkout. Replay the [behavioral evaluation cases](EVALS.md) with a
fresh agent. Formatting checks alone do not establish useful decisions.

Run the portable operations checks from this checkout:

```sh
python3 -m unittest discover -s tests -v
python3 -m clanker_ops --help
```

The skills provide operational judgment. The connected runtime remains responsible
for enforcing permissions and external effects; local ledger evidence is not
proof that an external service performed an action.
