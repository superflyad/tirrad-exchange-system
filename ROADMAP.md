# Tirrad Roadmap

This roadmap is a lightweight planning surface for controlled Codex work. It does not replace issues, pull requests, or human approval.

## Active Workflow Level

Level 3: Objective-Driven Planning with Project Operations and Capacity Tracking is active now.

Level 3 keeps outcome validation from Level 2, keeps project state maintenance from the operating loop, and adds objective-first planning through `OBJECTIVES.md` plus operations awareness through `OPERATIONS.md`.

Planning flow:

```text
Objective -> Milestone -> Task -> Validation -> Progress -> Operations
```

## Near-Term Objective

Recommended first objective: One-command local onboarding.

Success path:

```text
Fresh clone
-> ./tes dev --demo-run
-> Dashboard healthy
-> Replay visible
-> No manual fixes
```

Milestones:

1. Build verification
2. Python verification
3. Unified local startup
4. Outcome validation
5. Automated smoke validation

## Near-Term Task Direction

1. Outcome-validate the existing `./tes dev --demo-run` workflow from command startup through dashboard run/replay inspection.
2. Close any validation gaps found in the local development startup behavior for API, dashboard, persisted run creation, and replay surfaces.
3. Add automated smoke validation after the executable workflow has current outcome evidence.
4. Document contributor-facing Level 3 usage only after the executable workflow has current outcome evidence.
5. Keep objective, milestone, and state files current after each completed task.
6. Use operations records to answer `What is the highest-value next task?` before recommending work.

## Operating Principles

- Read `OBJECTIVES.md` before selecting tasks from `NEXT_TASK.md`.
- Read `OPERATIONS.md` before making capacity, usage, throughput, or recommendation-value claims.
- Keep tasks small, scoped, and validation-ready.
- Preserve strict command and event contracts.
- Do not modify matching behavior unless explicitly requested.
- Prefer repository workflow entry points through `./tes`.
- Keep human approval as the gate for commits, pushes, PRs, and merges.
- Prefer unblockers, shared infrastructure, user-visible functionality, validation, automation, then documentation.
- Avoid workflow churn and documentation-only loops.

## Future Readiness

Level 4: Parallel Execution Lanes is documented only. It may use operations history later to split work across independent lanes with disjoint file ownership and clear validation boundaries.

Level 5: Project Orchestration is documented only. It may use objective, milestone, operations, capacity, and blocker history later to coordinate larger plans with human approval.
