---
description: "Prepare current work for shipping: validate, update docs, run /review-cycle, open a ready PR, and watch CI to green."
---

# /ship

Ship the current repository work end to end. Use `/review-cycle` for the repeating review/fix/retest loop before opening PRs.

The parent agent running this command is **Claude Code**. CI watching, PR creation, and the review-cycle subprocess invocations all happen through Bash tool calls — long-running steps (CI watch, review subprocesses) should run in the background with `run_in_background: true` and be polled with `BashOutput` rather than tying up a foreground call against the 10-minute Bash cap.

## Hard Rules

- Respect the global worktree isolation policy before making edits. If the current checkout is a primary checkout such as `/Users/will/Work/.../repos/...`, move the work to a dedicated worktree and branch before editing, preferably under `/Users/will/.claude/worktrees/` with a `claude/` branch prefix.
- Do not mix this session's edits with unrelated dirty files. Preserve user changes, and ask only when the current work cannot be separated safely.
- Do not use destructive cleanup commands such as `git reset --hard`, `git checkout --`, or `git clean` unless the user explicitly asks for that exact destructive action.
- Run `/review-cycle` before opening PRs. Inherit its review rules, including no `ultrareview`, at least 15-minute review timeouts (via background Bash + `BashOutput`), and up to the configured round cap.
- CI failures after PR creation count as new work and must be fixed, locally revalidated, and passed back through `/review-cycle` when the fix changes code, tests, docs, config, or behavior materially.
- If the current work spans multiple repositories, ship them as an ordered dependency graph. Validate and run `/review-cycle` on upstream repos first, then downstream consumers against the exact upstream commits or PR branches they depend on.

## Arguments

- `rounds=N`: maximum `/review-cycle` rounds. Default `3`.
- `base=<branch>`: override the comparison base branch.
- `repos=<path1,path2>`: explicit list of repositories in the shipping set.
- `draft`: explicitly create draft PRs. Without this argument, open PRs ready for review when validation and `/review-cycle` are clean.

## Preflight

1. Confirm this is a git repository. If `repos=` was provided, confirm every listed path is a git repository.
2. Discover the full shipping set before validating anything:
   - current repository
   - repositories explicitly named by the user or `repos=`
   - dirty related worktrees under `/Users/will/.claude/worktrees/` (also check `/Users/will/.codex/worktrees/` and `/Users/will/Work/_trees/` for cross-agent work in progress)
   - local path, workspace, git, or package dependencies referenced by changed files
   - git submodules or nested repositories touched by the diff
   - sibling repositories that are clearly referenced by changed docs, package manifests, lockfiles, workflow files, deployment manifests, or local integration config
3. Exclude unrelated dirty repositories. If multiple dirty repos are present but the dependency relationship is not clear, report them and ask before including them.
4. For each included repository, capture:
   - repo root
   - current branch
   - worktree path
   - remote URL
   - default/base branch
   - staged, unstaged, and untracked files
5. Confirm every included checkout is safe for edits under the worktree isolation policy. State the selected worktree path and branch for each repository before editing.
6. Check required tools before relying on them:
   - `gh`
   - `pr-review` (install: `git clone https://github.com/happyvertical/pr-review.git ~/pr-review && export PATH="$HOME/pr-review/bin:$PATH"`)
   - `codex`
   - `claude`
   - `gh copilot`
7. Confirm GitHub auth with `gh auth status`. Treat missing auth as a blocker for PR/CI work.
8. Read repository instructions and shipping context in every included repository:
   - nearest `CLAUDE.md`
   - nearest `AGENTS.md` if present
   - `README*`
   - package/build config files
   - `.github/pull_request_template*`
   - `.github/workflows/*`
9. Look for `## Shipping Notes` in repo-level `CLAUDE.md` (or `AGENTS.md`). If present, treat it as the source of repo-specific shipping commands, docs requirements, CI quirks, release notes, PR expectations, and known flaky checks.

## Multi-Repo Ordering

When more than one repository is involved, build a dependency graph before validation and `/review-cycle`.

Use directed edges as `upstream -> downstream`, meaning the downstream repo depends on code, packages, APIs, manifests, images, generated artifacts, or documentation from the upstream repo.

Evidence for ordering includes:

- package manifests and lockfiles
- workspace files
- local `file:` or path dependencies
- Git submodules
- generated SDK/client references
- service API contracts
- deployment manifests and image references
- CI workflows that consume artifacts from another repo
- docs or release notes that explicitly describe dependency order
- `Shipping Notes`

If the graph is ambiguous:

- state the uncertainty
- choose the conservative order only when evidence is strong enough
- otherwise ask before proceeding

Ship in topological order:

1. Validate each upstream repository first.
2. Run `/review-cycle` on upstream repositories before relying on those changes downstream.
3. Record the exact upstream commit, branch, PR URL, package version, image tag/digest, or artifact that downstream validation uses.
4. Update downstream repositories to reference the upstream result when that is part of the intended change.
5. Run downstream validation and `/review-cycle` after upstream is clean.
6. If downstream work finds a real upstream issue, go back to the upstream repo, fix it, rerun upstream validation and `/review-cycle`, then rerun affected downstream validation and `/review-cycle`.

For PRs:

- Open upstream PRs before downstream PRs.
- Open PRs ready for review by default, including downstream PRs that depend on unmerged upstream PRs.
- Link downstream PRs to upstream PRs and call out the dependency explicitly.
- Use draft PRs only when the user passed `draft`, the repo explicitly requires draft stacked PRs, or unresolved blockers make the PR not ready for review.
- Watch CI in upstream-to-downstream order. If upstream CI fails, pause downstream promotion until the upstream failure is fixed or proven unrelated.

## Shipping Notes Policy

`## Shipping Notes` is a good repo-level pattern. Use it as a durable project checklist, not a run log.

When present:

- follow its commands and repo-specific gates before generic guesses
- update it only when this run discovers durable facts future shipping runs should know
- keep updates concise and actionable

When absent:

- do not add it just to say the command ran
- add it only if you learn durable repo-specific shipping knowledge, such as the canonical lint/test commands, required docs surfaces, release-note policy, CI watch quirks, or PR conventions
- if adding it, keep the section short and factual

Suggested shape:

```markdown
## Shipping Notes

- Validation:
- Documentation:
- Reviews:
- PR/CI:
- Known quirks:
```

## Clean And Validate

For multi-repo work, run this section for each repository in dependency order. After every upstream repo changes, rerun the relevant downstream checks that prove compatibility with the new upstream state.

1. Inspect the current diff and classify the change:
   - behavior/API
   - UI/UX
   - data/schema/migrations
   - infrastructure/CI
   - docs-only
   - tests-only
2. Run the repo's normal formatting/linting path when configured. Prefer the commands documented in `Shipping Notes`, `CLAUDE.md`, package scripts, Makefiles, taskfiles, or README.
3. Run the smallest meaningful tests first, then broader suites appropriate to the blast radius.
4. Run typecheck/build commands when the stack has them.
5. Check documentation obligations:
   - Update user-facing docs for behavior, API, config, workflow, CLI, or UI changes.
   - Update changelog/release notes when the repo uses them.
   - Update examples or generated docs when they are part of the changed surface.
   - If no docs are needed, note the reason.
6. If validation fails, fix the failure and rerun the relevant command. Broaden validation before review if the fix touches shared or user-facing behavior.

## Review Cycle Gate

After validation and documentation cleanup, run `/review-cycle` over the same repository set before opening PRs.

Use the same `rounds=`, `base=`, and `repos=` arguments passed to `/ship`. For multi-repo work, pass the dependency order and upstream/downstream context discovered during `/ship` preflight.

Treat `/review-cycle` as the blocker gate:

**Regardless of the gate's result**, always copy these fields from
`/review-cycle`'s final report into the PR body when creating or
updating the PR:
- `Accepted P2 (with rationale)` — accepted P2 happens on the `clean`
  branch under the current status contract (all P2 fixed-or-accepted
  → clean), so this propagation is not gated by `partial`
- `Accepted non-blockers (P3/nit)` — same reasoning
- `Skipped reviewers` (if any)

These fields are how human reviewers see the deliberate choices the
ensemble made. Dropping them defeats the audit trail.

Then branch on the gate result:

- If `/review-cycle` returns `clean`, continue to commit and PR.
- If it returns `partial`, branch on the reason recorded in
  `Skipped reviewers` (the only documented cause of `partial` —
  Accepted P2 ends in `clean`, not `partial`, per the Status
  contract):
  - **Partial because copilot-cli was skipped** (org policy block,
    network failure, missing auth, etc.): open the PR as a **draft**
    so the Copilot bot can review post-push.

    **Prerequisite check**: GitHub's automatic Copilot code review
    of drafts is opt-in per-repo. By default the bot only reviews
    when a PR opens *non-draft* (or transitions Draft→Open) and
    does NOT auto-re-review subsequent pushes. Before relying on
    this fallback, verify in the repo's Copilot settings ([docs](https://docs.github.com/en/copilot/concepts/agents/code-review#about-automatic-pull-request-reviews))
    that BOTH "Automatically review pull requests" includes
    "Review draft pull requests" AND "Review new pushes" is
    enabled. If either is off, the fallback will silently wait
    forever for a review that never comes — you must instead
    request the bot review manually with `gh pr edit <PR>
    --add-reviewer @copilot` ([docs](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)).

    **gh CLI version requirement**: `--add-reviewer @copilot`
    requires gh CLI v2.88.0 or newer ([release notes](https://github.com/cli/cli/releases/tag/v2.88.0)).
    On older gh, the command fails with `Could not request
    reviewer: '@copilot' not found` and the bot is NOT requested
    — silently regressing into the same "draft sits forever
    without review" mode. Check with `gh --version` first. If
    your gh is older, upgrade (`brew upgrade gh`) or use the PR
    page's Reviewers menu manually.

    For re-reviews after subsequent pushes, use the Reviewers menu
    (re-request button) on the PR page; `gh pr edit` is for the
    initial add only.

    Address bot findings, then rerun `/review-cycle`. The rerun
    will *still* return `partial` (the CLI block is the same), so
    it can't be the clearance signal. Instead: when the Copilot
    bot has reviewed the **current** commit with no unaddressed
    findings AND a human explicitly accepts the bot-for-CLI
    substitution (typically by running `gh pr ready`), that's the
    clearance path. "Current commit" matters: if you pushed
    fixes after the bot reviewed, request a re-review on the new
    SHA before clearing. Document the substitution in the PR body
    so the audit trail is clear.
  - **Partial because a different required reviewer slot was unfilled**
    (codex-cli unavailable, OR claude slot couldn't be filled via
    EITHER `claude -p` subprocess OR the sub-agent fallback, OR the
    orchestrator slot was unfilled because no explicit `{findings:
    []}` checklist pass was produced this round): open as draft and
    call out the skip in the PR body so a human can decide whether
    the remaining reviewer coverage is sufficient. Don't mark ready
    until the skipped slot can be filled or a human explicitly
    accepts the gap with rationale in the PR body.

    Note: if `claude -p` failed but the sub-agent fallback succeeded,
    the claude slot IS filled (not skipped). `/review-cycle` should
    have returned `clean`, not `partial`, in that case — if it
    returned `partial` anyway, that's a bug in how the orchestrator
    classified the substitution and should be fixed there, not
    worked around here.
- If it returns `blocked`, stop before opening ready PRs. Open draft PRs only when the user passed `draft` or a draft would help expose the blocker.
  - **Special sub-case: blocked because of `verify-round-blocked-by-cap`** (a P0/P1/P2 fix landed in the final permitted `/review-cycle` round). The fix may be correct but no verify round confirmed it. Don't ship — re-run `/review-cycle rounds=N+1` (or higher) to let the verify round complete, then re-attempt `/ship`. Calling this out explicitly because the failure mode looks like "clean" to a literal reader (the tree post-fix surfaces no findings) but actually means "findings were never sought".
- If `/review-cycle` changed files, rerun the relevant validation and documentation checks before committing.

## Commit And PR

When the Review Cycle Gate above has been satisfied (either `clean`,
or `partial` with an explicit fallback path documented above),
commit and open PRs in dependency order. Draft vs ready follows the
gate's branch — draft on partial, ready on clean (unless the user
passed `draft`):

1. Recheck `git status --porcelain` in each included repository.
2. Ensure every branch name is suitable. If needed, create a `claude/ship-<short-topic>` branch per repository.
3. Commit uncommitted shipping changes with concise messages. Do not rewrite or squash existing user commits unless asked.
4. Push upstream branches first, then downstream branches.
5. Create or update PRs with `gh pr create` or `gh pr edit`, upstream first.
6. Use each repo's PR template when present.
7. If an existing PR is draft AND `/review-cycle` returned status `clean` (not `partial`, not `blocked`) AND validation is green AND the user didn't pass `draft`, mark it ready for review with `gh pr ready`. "Now clean" is the Review Cycle Gate output specifically — not a subjective re-read of the working tree. On `partial`, the human runs `gh pr ready` after the partial-branch clearance path documented above (e.g. after Copilot bot has reviewed the current commit and the operator explicitly accepts the bot-for-CLI substitution). Don't auto-ready a draft that came from a partial gate.
8. Include in every PR:
   - summary of changes
   - validation commands and results
   - review rounds run and outcome
   - documentation updates or why none were needed
   - unresolved accepted non-blockers, if any
   - cross-repo dependencies, including upstream PR URLs or exact commits when applicable

If the user passed `draft`, create draft PRs. Otherwise, create PRs ready for review when the work is clean. Do not make a downstream PR draft solely because it depends on an unmerged upstream PR; link the dependency clearly instead. Use draft only for explicit user preference, documented repo policy, or unresolved blockers.

## CI Watch And Fix

After PRs exist, watch CI in dependency order. CI watching is long-running — invoke `gh pr checks --watch` via Bash with `run_in_background: true` and poll with `BashOutput`, or use the `Monitor` tool with `gh pr checks --json state -q '.[].state' | grep -v -E 'success|skipped|neutral'` until it returns empty.

1. Run `gh pr checks --watch --interval 10` for the current upstream PR before advancing to downstream PRs.
2. If checks pass, record the PR URL and green status.
3. If checks fail:
   - list failing check names with `gh pr checks --json name,workflow,state,bucket,link`
   - inspect failing logs with `gh run view --log-failed` or the check-specific URL
   - identify the smallest valid fix
   - apply the fix in the isolated worktree
   - rerun local validation relevant to the failing check
   - rerun reviews when the fix changes code, tests, docs, config, or behavior materially
   - commit and push
   - resume watching CI
4. If an upstream CI fix changes downstream behavior or artifacts, rerun affected downstream validation, review, and CI.
5. Continue until CI is green across all included PRs or a real blocker remains, such as missing secrets, external service outage, unavailable required credentials, or a failing check that cannot be inspected locally.

## Final Report

Return a concise shipping report:

```text
## Ship Result
- Status: clean | partial | blocked
- Repos: <ordered repo list with upstream/downstream roles>
- Worktrees: <paths>
- Branches: <branches>
- PRs: <urls or none>
- Validation: <commands run>
- Reviews: <copy the Reviews field from /review-cycle's report verbatim — enumerate all four ensemble slots (codex-cli, claude slot, copilot-cli, orchestrator) with substitutions/skips called out. Don't summarize "3 rounds: codex + copilot + me" — silence reads as "ran" and confuses readers who only see /ship's report>
- Accepted P2 (with rationale): <copy from /review-cycle's report verbatim — none, or list with rationale. Same field already gets copied into the PR body; mirror it here so /ship's own report is self-contained>
- Accepted non-blockers (P3/nit): <copy from /review-cycle's report verbatim>
- Skipped reviewers: <copy from /review-cycle's report verbatim — never silently drop>
- Docs: <updated or not needed because...>
- CI: green | failing | blocked | not configured
- Dependency order: <upstream -> downstream edges or none>
- Remaining: <none or concrete blockers>
```
