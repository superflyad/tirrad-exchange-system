# Project Operations

This file defines the TES Project Operations and Capacity Tracking framework. It is a workflow and project-management surface only. It does not authorize product code changes, automation, agents, schedulers, commits, pushes, or pull requests.

## Purpose

Project Operations lets Codex reason about engineering throughput, effort, objective progress, blockers, and recommendation value from observed project history.

At Level 3, Codex must use operations data to answer:

```text
What is the highest-value next task?
```

before recommending follow-up work.

## Operations Scope

Codex must track:

- Objectives
- Milestones
- Tasks
- Throughput
- Capacity
- Blockers
- Usage observations

Operations tracking should improve decisions without creating workflow churn. If an operations update does not clarify progress, capacity, blocker state, or next-task value, leave the record unchanged.

## Operations Records

Each completed or blocked task may record an operations entry. Do not invent usage values. If token or other usage data is unavailable, record exactly:

```text
Usage unavailable
```

Use this structure:

```markdown
### <YYYY-MM-DD> - <task name>

- Date:
- Task name:
- Objective:
- Milestone:
- Duration:
- Observed token usage:
- Outcome:
- Value assessment:
- Notes:
```

Field guidance:

- Date: local task completion date.
- Task name: the completed or blocked task.
- Objective: the objective the task advanced or attempted to unblock.
- Milestone: the milestone the task advanced or attempted to unblock.
- Duration: observed elapsed work time when available; otherwise `Duration unavailable`.
- Observed token usage: actual usage only when available; otherwise `Usage unavailable`.
- Outcome: completed, blocked, partial, or superseded.
- Value assessment: High, Medium, Low, or Unknown, with a short reason.
- Notes: evidence, constraints, or recommendation implications.

## Objective Progress Tracking

Each objective should track:

- Progress %
- Completed milestones
- Remaining milestones
- Current bottleneck
- Estimated next highest-value work

Progress must remain evidence-based. Planning work can improve clarity, but it should not inflate progress unless it removes a blocker, retires stale work, or changes a milestone's validation status.

Suggested objective operations block:

```markdown
#### Operations Tracking

- Progress %:
- Completed milestones:
- Remaining milestones:
- Current bottleneck:
- Estimated next highest-value work:
- Throughput notes:
- Capacity notes:
- Usage observations:
```

## Throughput and Capacity

Throughput is the observed rate at which scoped tasks produce validated progress.

Capacity is the practical ability to keep making progress given available context, validation time, local environment readiness, user approvals, and risk.

Codex should record throughput and capacity qualitatively unless measured data is available. Examples:

- Throughput: `One docs-only workflow task completed with repository hygiene validation.`
- Capacity: `Good for workflow docs; product validation still requires local startup evidence.`
- Usage observations: `Usage unavailable.`

Do not convert qualitative observations into numeric estimates unless the task produced actual measurements.

## Blocker Tracking

Blockers should identify:

- Blocked objective
- Blocked milestone
- Blocked success scenario step
- Evidence observed
- Scope reason Codex cannot resolve it immediately
- Highest-value unblocker task

Prefer unblocker work before new feature or documentation work.

## Prioritization Rules

When recommending work, prefer:

1. Unblockers
2. Shared infrastructure
3. User-visible functionality
4. Validation
5. Automation
6. Documentation

Avoid:

- Duplicate work
- Completed work
- Workflow churn
- Documentation-only loops

Documentation is high value when the active objective is workflow governance. Otherwise, it should usually follow proven functionality and validation evidence.

## Recommendation Rules

Before recommending work, Codex must answer:

```text
What is the highest-value next task?
```

The answer should consider:

- Which objective is most important now.
- Which milestone is blocked or closest to meaningful validation.
- Whether the work removes a blocker, creates shared infrastructure, proves user-visible value, adds validation, automates a proven path, or documents an already-proven outcome.
- Whether recent operations records show planning effort outweighing implementation progress.
- Whether task scope is small enough to complete and validate.

Recommended next tasks must include:

- Objective
- Milestone
- Impact
- Risk
- Dependencies
- Lane
- Validation target
- Operations rationale

## Efficiency Guidance

Codex should classify observed effort as:

- Planning work
- Implementation work
- Validation work
- Documentation work

Planning is useful when it reduces ambiguity, prevents duplicate work, or selects a higher-value task. Planning effort is beginning to outweigh implementation progress when repeated tasks mostly update workflow text, state files, or recommendations without moving a product, validation, or objective milestone forward.

When that happens, Codex should say so plainly and recommend the smallest implementation or validation task that can produce new evidence.

## Objective Cost Awareness

Codex should treat effort, validation cost, local environment risk, and file ownership risk as part of task selection.

Use this lightweight assessment:

```markdown
- Expected value:
- Expected effort:
- Validation cost:
- Risk:
- Opportunity cost:
- Highest-value next task:
```

Do not invent duration, usage, or throughput metrics. Use observed evidence, qualitative estimates, or `unavailable` values.

## Operations Reporting

Every Level 3 completion report must include:

```markdown
## OPERATIONS SUMMARY

Objective:
Current milestone:
Progress:
Completed work:
Remaining work:
Blockers:
Observed duration:
Observed usage:
Recommended next tasks:
```

Rules:

- `Observed duration` may be qualitative or `Duration unavailable`.
- `Observed usage` must be actual observed usage or `Usage unavailable`.
- `Recommended next tasks` must follow the prioritization rules in this file.
- Do not report invented numeric usage values.

## Tirrad-Specific Example

Objective: One-command local onboarding

Goal:

```text
Fresh clone
-> ./tes dev --demo-run
-> Dashboard healthy
-> Replay visible
-> No manual fixes
```

Example objective operations tracking:

```markdown
#### Operations Tracking

- Progress %: 35
- Completed milestones:
  - Root `./tes` workflow entry point exists.
  - API demo-run helper exists.
  - Dashboard run, live monitor, and replay surfaces are present.
- Remaining milestones:
  - Python verification
  - Unified local startup outcome evidence
  - Dashboard run and replay visibility evidence
  - Automated smoke validation
- Current bottleneck: Current local outcome evidence for `./tes dev --demo-run` is unavailable.
- Estimated next highest-value work: Outcome-validate `./tes dev --demo-run` and record dashboard health, generated `run_id`, run detail, replay visibility, and clean shutdown.
- Throughput notes: Workflow planning is in place; next value should come from validation evidence.
- Capacity notes: Local validation capacity depends on API/dashboard startup and port availability.
- Usage observations: Usage unavailable.
```

Example operations entry:

```markdown
### 2026-06-14 - Upgrade workflow to include Project Operations and Capacity Tracking

- Date: 2026-06-14
- Task name: Upgrade workflow to include Project Operations and Capacity Tracking
- Objective: Workflow governance / One-command local onboarding support
- Milestone: Project operations framework
- Duration: Duration unavailable
- Observed token usage: Usage unavailable
- Outcome: Completed
- Value assessment: High. Adds throughput, capacity, blocker, usage, and objective cost awareness to future Level 3 recommendations.
- Notes: Docs-only workflow task. No product code, automation, agents, schedulers, commits, or pushes.
```

## Future Readiness

These levels are documented only. Do not implement them without explicit human approval.

### Level 4: Parallel Execution Lanes

Future Level 4 may use operations records to split work across independent lanes when file ownership is disjoint, validation boundaries are clear, and one integration owner is identified.

Level 4 must not allow parallel edits to shared contract files unless a single task owns integration.

### Level 5: Project Orchestration

Future Level 5 may use objectives, milestones, operations history, capacity observations, and blocker data to coordinate larger project plans.

Level 5 must remain deterministic, contract-safe, and human-approved. It should orchestrate already-defined work, not invent hidden automation or autonomous schedulers.
