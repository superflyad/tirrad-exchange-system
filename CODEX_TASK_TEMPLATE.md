# Codex Task Template

Use this template for Level 1 single-task iteration. Level 1 is active now. Levels 2-4 are documented in `CODEX_WORKFLOW.md` and require human approval before use.

```markdown
Task:

Goal:

Workflow level:
- Level 1: single-task iteration

Mode:
- Investigation-only / Edit

Allowed files:
-

Do not edit:
- Product code unless explicitly listed in allowed files.
- Files outside the approved scope.

Requirements:
-

Contract safety:
- Keep Python-visible event shape exactly `{ "type": "...", "data": {...} }`.
- Do not leak raw C++ internals into Python-visible output.
- Do not weaken parsers or validators.
- Do not pass raw dictionaries beyond parser or serialization boundaries when strict models exist.

Validation:
- [ ] `./tes check`
- [ ] `./tes check python`
- [ ] `./tes check python-release`
- [ ] `cd web && npm run build`
- [ ] Other:

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
- Risks or unresolved questions.
- Next recommended task.
```

## Recommended First Level 1 Task

Add `./tes dev` as a repository workflow command after explicit human approval. This task should define the intended development startup behavior before implementation begins.
