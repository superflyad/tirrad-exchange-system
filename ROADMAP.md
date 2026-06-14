# Tirrad Roadmap

This roadmap is a lightweight planning surface for controlled Codex work. It does not replace issues, pull requests, or human approval.

## Active Workflow Level

Level 3: Objective-Driven Planning is active now.

Level 3 keeps outcome validation from Level 2, keeps project state maintenance from the operating loop, and adds objective-first planning through `OBJECTIVES.md`.

Planning flow:

```text
Objective -> Milestone -> Task -> Validation -> Progress
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

## Operating Principles

- Read `OBJECTIVES.md` before selecting tasks from `NEXT_TASK.md`.
- Keep tasks small, scoped, and validation-ready.
- Preserve strict command and event contracts.
- Do not modify matching behavior unless explicitly requested.
- Prefer repository workflow entry points through `./tes`.
- Keep human approval as the gate for commits, pushes, PRs, and merges.
