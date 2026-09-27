---
name: clanker-compute
description: Plan and run resource-heavy work within local capacity or on authorized remote compute. Use before large builds, test batches, data jobs, GPU work, or parallel fan-out could exhaust RAM, CPU, disk, or accelerators, and when offloading to cloud workers or VMs. Not a remedy for model API quotas.
---

# Place and bound compute work

Keep the user's machine usable while completing the same requested task. Choose
where a workload runs, retain its identity, and verify both its result and resource
cleanup. This skill uses documented tools in the connected environment; it does
not supply a cloud account, spending policy, or provider adapter.

## Assess the next workload

Identify the task, inputs, required environment, expected outputs, and deadline.
Inspect current host capacity and competing work before a heavy phase or wider
fan-out. Estimate demand from prior measurements or a small representative run
when that run itself fits safely. Preserve the user's requested local reserve;
otherwise choose and explain conservative headroom using observed pressure.

Account for peak RAM, CPU concurrency, scratch/output disk, GPU memory, and all
workers that will overlap. Include setup and artifact collection, not only steady
execution. Do not start an oversized trial to discover its peak. If demand cannot
be bounded, reduce the trial size or concurrency first.

High CPU usage alone does not justify remote provisioning. Distinguish legitimate
work from a leak, repeated failure, or a process making no progress. Diagnose the
cause instead of repeatedly renting larger machines. Do not terminate unrelated
work to free capacity. A VM or container on the same host adds no physical capacity.

## Choose placement

Compare only options that meet the required environment and deadline. Consider
setup, data movement, and total bounded cost as well as execution time.

| Placement | Choose it when |
| --- | --- |
| Local execution | Aggregate demand fits while preserving interactive use and disk reserve |
| Fewer local workers or smaller chunks | Reduced concurrency fits and still meets the task's deadline |
| Existing remote executor | It has permitted spare capacity and can isolate this job from other work |
| Managed finite job | The task is portable and its execution, effects, and resource lifetime can be bounded |
| New remote VM | The required environment, accelerator, or state cannot be served suitably by the simpler options |

Check OS/architecture, accelerators, dependencies, required local services, data
location, and transfer permissions. Do not substitute remote Linux evidence for
a behavior that requires the user's macOS environment, UI, or attached hardware.
Move a separable computation when the whole task is not portable. Remote execution
does not broaden authority to publish, deploy, or repeat external effects.

If local execution is sufficient, use the bounded concurrency and verify the
result; no cloud setup is needed. Recheck pressure as the workload changes. Only
throttle or cancel work owned by this task, through its supported controls.

## Execute remotely under an explicit contract

Before remote execution, read [the remote execution contract](references/remote-execution.md).
It owns policy resolution, cost/concurrency reservations, launch reconciliation,
deadlines, and cleanup. Use existing standing authorization without requesting it
again. A connected account alone does not establish permission to spend or upload data.

Resolve the executor's documented capabilities. Where execution can incur charges,
check current prices for the selected region and resource shape. Prefer an
established job runner or adapter that implements the contract. Check its actual behavior rather than
assuming that a timeout, tag, budget alert, or accepted delete request enforces it.
Do not invent provider commands or guarantees.

Before launching or submitting the workload, establish:

- The permitted execution target, workload, resource limits, and data scope;
  account/region and cost allowance where applicable.
- An attributable input snapshot, including the intended uncommitted work.
- One execution owner, durable launch identity, reserved capacity, and a cost reservation where charges apply.
- A deadline and cleanup path that continue to work if the agent disconnects.
- An output destination and bounded retention plan compatible with that deadline.

Within the granted policy, proceed autonomously through preparation, execution,
collection, and task-owned cleanup. Creating the required controls is part of
preparation when authorized and included in the allowance. If a prerequisite
cannot be established, continue feasible local work or prepare a concrete remote
plan with the exact missing permission or capability. Do not substitute unlimited
spending, an assumed provider connection, or a promise to clean up later.

## Verify and report

Match outputs to the intended input snapshot, task, and attempt; execute the
acceptance check on the actual artifact or destination. Do not accept a stale
remote checkout or successful process exit as proof. The focused outcome skill
can assist when available, but it is not required to use this skill.

Report placement and its reason, checks performed, artifact locations, observed
resource state, estimated versus known cost, and any remaining uncertainty.
Separate workload success from cleanup success. Name retained or unresolved
resources, their owner and expiry, and any continuing cost exposure. Never mark
resources cleaned up solely because a termination request was accepted.
