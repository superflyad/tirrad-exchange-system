# Codex Task Template

Use this template for Codex tasks. Level 2 outcome validation is active for future work: tasks are complete only when the requested user workflow succeeds or a documented blocker prevents completion.

```markdown
Task:

Objective:

Workflow level:
- Level 2: outcome validation

Mode:
- Investigation-only / Edit

Allowed files:
-

Do not edit:
- Product code unless explicitly listed in allowed files.
- Files outside the approved scope.

Constraints:
-

Requirements:
-

Contract safety:
- Keep Python-visible event shape exactly `{ "type": "...", "data": {...} }`.
- Do not leak raw C++ internals into Python-visible output.
- Do not weaken parsers or validators.
- Do not pass raw dictionaries beyond parser or serialization boundaries when strict models exist.

Validation Commands:
- [ ] `./tes check`
- [ ] `./tes check python`
- [ ] `./tes check python-release`
- [ ] `cd web && npm run build`
- [ ] Other:

Success Scenario:
1.
2.
3.

Acceptance:
-

Permissions:
- Do not commit.
- Do not push.
- Stop after completion report.

Completion report must include:
- Summary.
- Files changed.
- Validation commands actually run and results.
- SUCCESS SCENARIO.
- Risks or unresolved questions.
- Next recommended task.

Completion Report:

## Summary
-

## Files Changed
-

## Validation
- `git status`: passed / failed / not run
- `git diff --stat`: passed / failed / not run
- Other commands actually run:

## SUCCESS SCENARIO
Steps executed:

Observed result:

Evidence:

Remaining issues:

Blockers:

Recommended next task:

## Risks
-
```

## Example Level 2 Success Scenario

Task:
`./tes dev --demo-run`

Success Scenario:
1. Start stack.
2. Open dashboard.
3. Verify health page.
4. Generate run.
5. Verify run appears.
6. Verify replay data loads.
7. Shut down cleanly.

The task is incomplete until all steps succeed or a blocker is documented.

## Recommended First Level 2 Implementation Task

Implement `./tes dev --demo-run` as the first outcome-validated workflow after explicit human approval. The task should define the command behavior, success scenario, validation commands, and completion report before implementation begins.
