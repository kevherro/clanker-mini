# clanker-mini

A small skill pack for building and operating autonomous systems. A tailored
mestack dispatcher coordinates engineering work; three focused skills locate
authoritative state, diagnose troubled runs, and check whether work really
finished. The pack contains no assumed runtime commands or machine-specific paths.

| Skill | Use it for |
| --- | --- |
| [clanker-stack](.agents/skills/clanker-stack/SKILL.md) | Coordinating investigations, fixes, features, refactors, and unattended work with evidence at each step |
| [clanker-system-map](.agents/skills/clanker-system-map/SKILL.md) | Finding the control interface, effective configuration, state owner, and result destination |
| [clanker-run-triage](.agents/skills/clanker-run-triage/SKILL.md) | Distinguishing progress from retry loops and reconciling partial effects before recovery |
| [clanker-verify-outcome](.agents/skills/clanker-verify-outcome/SKILL.md) | Checking unattended completion claims against actual artifacts and downstream results |

Use `clanker-stack` for multi-step engineering work. It includes its own playbooks
and routes to the focused skills when relevant, with fallbacks if they are absent.
It does not depend on a global mestack installation. The focused skills can also
be used directly; there is no requirement to run the whole pack in sequence.
Supply the target workspace or host and, for run-specific work, the task identity
and original request.

## Use in Codex

The skills live in `.agents/skills` for repository discovery. Open Codex in this
checkout and invoke `$clanker-stack`, `$clanker-system-map`, `$clanker-run-triage`,
or `$clanker-verify-outcome`. Their descriptions also support automatic selection.

To make them available in other projects, link or copy the individual skill
directories into your user skill directory, normally `~/.agents/skills`. Check
for existing names before adding links. This repository does not install them
globally or modify Codex's bundled `.system` skills.

See the [official discovery documentation](https://learn.chatgpt.com/docs/build-skills#where-to-save-skills).

## Check changes

Validate each skill with Codex's skill-creator validator, then check discovery
from this checkout. Replay the [behavioral evaluation cases](EVALS.md) with a
fresh agent. Formatting checks alone do not establish useful decisions.

The skills provide operational judgment. The runtime remains responsible for
permissions, leases, concurrency, retry budgets, and durable state.
