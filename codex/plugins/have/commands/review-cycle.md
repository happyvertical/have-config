---
description: Run a repeatable review/fix/retest loop over current work, optionally across multiple repos, without opening PRs or shipping.
---

# /review-cycle

Run a bounded review cycle on the current work independent of shipping. Default to 3 rounds unless the user passes `rounds=N`.

## Hard Rules

- Respect the global worktree isolation policy before making edits. If the current checkout is a primary checkout such as `/Users/will/Work/.../repos/...`, move the work to a dedicated worktree and branch before editing, preferably under `/Users/will/.codex/worktrees/` with a `codex/` branch prefix.
- Do not mix this session's edits with unrelated dirty files. Preserve user changes, and ask only when the current work cannot be separated safely.
- Do not use destructive cleanup commands such as `git reset --hard`, `git checkout --`, or `git clean` unless the user explicitly asks for that exact destructive action.
- Do not use `claude ultrareview` or any `ultrareview` command. Use the normal Claude CLI in non-interactive print mode for review.
- Every external review command must be allowed at least 15 minutes. When using Codex command tools, set the command timeout to at least `900000` ms for review commands.
- Treat review output as evidence to verify, not as orders. Fix valid findings. For false positives, record the rationale in the final report.
- Keep going until the work is clean or the configured review-round cap is reached.
- If the work spans multiple repositories, review them as an ordered dependency graph. Review upstream repos first, then downstream consumers against the exact upstream commits or branches they depend on.
- This command does not open PRs, push branches, or watch CI unless the user explicitly asks for that during the review-cycle run.

## Arguments

- `rounds=N`: maximum review/fix rounds. Default `3`.
- `base=<branch>`: override the comparison base branch.
- `repos=<path1,path2>`: explicit list of repositories in the review set.
- `no-fix`: review only; do not edit files.
- `no-baseline`: skip baseline validation before the first review round.

## Preflight

1. Confirm this is a git repository. If `repos=` was provided, confirm every listed path is a git repository.
2. Discover the review set:
   - current repository
   - repositories explicitly named by the user or `repos=`
   - dirty related worktrees under `/Users/will/.codex/worktrees/`
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
   - `pr-review` (install: `git clone https://github.com/happyvertical/pr-review.git ~/pr-review && export PATH="$HOME/pr-review/bin:$PATH"`)
   - `codex`
   - `claude`
   - `gh copilot`
   - `gh` when Copilot is reached through `gh copilot`
7. Read repository instructions and review context in every included repository:
   - nearest `AGENTS.md`
   - nearest `CLAUDE.md` if present
   - `README*`
   - package/build config files
   - relevant test/lint/build docs
   - `.github/workflows/*` when CI risk is part of the change
8. Look for `## Shipping Notes` in repo-level `AGENTS.md`. If present, use it for repo-specific validation commands, docs expectations, review expectations, and known flaky checks.

## Multi-Repo Ordering

When more than one repository is involved, build a dependency graph before reviewing.

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

Review in topological order:

1. Validate and review each upstream repository first.
2. Fix upstream findings before relying on those changes downstream.
3. Record the exact upstream commit, branch, package version, image tag/digest, or artifact that downstream validation uses.
4. Update downstream repositories to reference the upstream result when that is part of the intended work.
5. Run downstream validation and review after upstream is clean.
6. If a downstream review finds a real upstream issue, go back to the upstream repo, fix it, rerun upstream validation/review, then rerun affected downstream validation/review. Count this as the same overall review round when practical.

## Baseline Validation

Unless `no-baseline` was passed, run baseline validation before the first review round for each repository in dependency order:

1. Inspect the current diff and classify the change:
   - behavior/API
   - UI/UX
   - data/schema/migrations
   - infrastructure/CI
   - docs-only
   - tests-only
2. Run the repo's normal formatting/linting path when configured. Prefer commands documented in `Shipping Notes`, `AGENTS.md`, package scripts, Makefiles, taskfiles, or README.
3. Run the smallest meaningful tests first, then broader suites appropriate to the blast radius.
4. Run typecheck/build commands when the stack has them.
5. Check documentation obligations:
   - user-facing docs for behavior, API, config, workflow, CLI, or UI changes
   - changelog/release notes when the repo uses them
   - examples or generated docs when they are part of the changed surface
6. If validation fails, fix the failure unless `no-fix` was passed, then rerun the relevant command.

## Review Commands

Create a temporary review directory outside the repo for review outputs. Do not commit raw review logs unless the repo explicitly asks for them.

For multi-repo work, create one review subdirectory per repository and include the dependency context in each review prompt. Upstream review prompts should ask whether downstream compatibility is preserved. Downstream review prompts should name the upstream commits, branches, versions, image tags, or artifacts being consumed.

### Generate the review prompt with `pr-review`

Use the `pr-review` tool (https://github.com/happyvertical/pr-review) to generate the review prompt rather than a generic one-line brief. `pr-review` bundles a calibrated 10-theme checklist (refactor regressions, tenant isolation, effect races, silent error swallowing, hardcoded paths, doc/code drift, infra duplication, dead config, concurrency, SQL correctness) plus any repository-specific patterns in `<repo>/.pr-review/extensions.md`. All three reviewers get the same calibrated prompt so their findings are directly comparable.

If `pr-review` is not on `$PATH`:

```bash
git clone https://github.com/happyvertical/pr-review.git ~/pr-review
export PATH="$HOME/pr-review/bin:$PATH"
```

If the repository being reviewed has no `.pr-review/extensions.md`, the shared core checklist still applies — the prompt just doesn't include repo-specific guidance. That's a signal to consider adding one after the review-cycle run.

### Run Codex review

`codex review` fetches its own diff, so pass `--no-diff` to `pr-review` to avoid sending the diff twice:

- If the branch has committed changes against the base branch:
  ```bash
  pr-review --base <base> --no-diff | codex review --base <base> -
  ```
- If there are staged, unstaged, or untracked changes, also run:
  ```bash
  pr-review --base <base> --no-diff | codex review --uncommitted -
  ```
- Do not use `claude ultrareview` or any `ultrareview` variant for any reviewer here.

### Run Claude review

Claude does not fetch its own diff — pipe `pr-review` output without `--no-diff`:

```bash
pr-review --base <base> | claude -p --permission-mode plan
```

- Use `claude -p` in non-interactive mode.
- Prefer read-only/plan permissions for the review run (`--permission-mode plan`).
- Disallow edit/write tools where supported.

### Run Copilot review

**This step is non-optional for the "catch before push" intent.** The
Copilot PR review *bot* only fires after a PR is opened — too late to
prevent the round-trip the review-cycle exists to compress. The Copilot
*CLI* runs locally pre-push and gives you Copilot's blind-spot
coverage before the bot has a chance to comment.

Copilot CLI expects the prompt to carry its own context:

```bash
gh copilot -- -p "$(pr-review --base <base> --pretty)" --allow-all-tools --effort xhigh
```

- Use `--pretty` so Copilot receives the prompt as readable markdown
  rather than the JSON-instruction format.
- Pass `--` after `gh copilot` to forward flags to the underlying
  `copilot` binary; otherwise `gh` may interpret them.
- `--effort xhigh` matches codex's reasoning depth; tune down if the
  diff is small and you want faster runs.
- If the `gh copilot` syntax has changed, run `gh copilot -- --help`
  and adapt to the installed CLI.
- Keep the Copilot run read-only — `--allow-all-tools` permits
  exploration but the prompt itself instructs not to modify files.

**Known blockers and fallbacks** (real failures we've seen):

- **`Access denied by policy settings`** — the org's Copilot policy
  is disabling CLI use. Fix at https://github.com/settings/copilot
  (personal) and/or your org's Copilot policies page (admin). Until
  enabled, Copilot CLI cannot run pre-push.
- **`Failed to authenticate. API Error: 401`** on `claude -p` — happens
  when this command is invoked from inside an active Claude Code
  session; OAuth credentials don't propagate to spawned children.
  Workaround: set `ANTHROPIC_API_KEY` env var on the child invocation,
  or run review-cycle from a terminal / CI / codex session instead.

**When a reviewer is unavailable**: proceed with the others *and*
record in the final report which reviewer was skipped and why. Do
not silently drop a reviewer — that's how operational drift hides.
If Copilot CLI is the unavailable one, consider opening the PR as a
**draft** so the Copilot bot reviews before merge candidates form;
fix any bot findings before marking ready for review.

### For all three

- Use a review command timeout of at least 15 minutes.
- Capture stdout and stderr to separate files in the temp review directory — malformed or empty findings almost always have the cause in stderr.
- Treat each tool's findings as evidence to verify against the code, not as orders to apply. Vague claims get dismissed; concrete file:line citations with named failure paths get acted on.
- After all three runs complete, merge findings into one checklist grouped by severity (see "Review/Fix Loop" below). Prefer findings flagged by ≥2 reviewers when severity is medium or low; high-severity findings from a single reviewer still warrant verification.

### Optional: capture for calibration

If the repository has a `.pr-review/extensions.md`, also append `| pr-review-capture` to one of the runs (typically Claude or Codex) so the findings are stored at `.pr-review/history/<sha>.json`. Later, `pr-review-tune --last 10` can compare stored findings against the review comments PRs actually received and propose refinements to the checklist. This closes the feedback loop so the checklist gets sharper over time.

```bash
pr-review --base <base> | claude -p --permission-mode plan | pr-review-capture | tee /dev/tty
```

## Review/Fix Loop

Run up to `rounds` review rounds. Default: 3 for code changes, higher
(5-10) for documentation / reviewer-checklist content where each round
catches progressively narrower factual edge cases.

**Hard rules for the loop** (these prevent the "stopped too early"
failure mode):

- **Each round runs all reviewers in parallel against the SAME commit**
  — not sequentially against each other's fixes. Sequential cascading
  makes findings depend on which reviewer ran first and obscures
  whether reviewers actually agree on the latest state.
- **A fix-round is never the final round.** Convergence requires
  at least one round where every reviewer returns 0 actionable
  findings against the latest commit. If you just pushed a fix, you
  MUST run another round before declaring clean.
- **Convergence is per-commit, not per-finding.** Reviewer A returning
  clean against commit X doesn't mean clean against commit Y (the
  fix commit). Re-run all reviewers against Y before stopping.

For each round, process repositories in dependency order:

1. Run validation before review if files changed since the previous validation pass.
2. Run Codex, Claude, and Copilot reviews for each repository in dependency order.
3. Merge findings into a single checklist:
   - `P0/P1`: correctness, data loss, security, broken build, failing tests
   - `P2`: likely bug, missing test, missing docs for changed behavior
   - `P3`: maintainability or polish with clear benefit
4. Verify each finding against the code. Do not blindly patch speculative review comments.
5. If `no-fix` was passed, stop after reporting findings.
6. Address all valid findings in priority order.
7. Add or adjust tests for bug fixes and behavior changes.
8. Rerun relevant validation after edits.
9. If upstream fixes change the contract consumed downstream, rerun affected downstream validation and review even if that downstream repo had already passed in the current round.
10. **If a fix was pushed in this round, the next round MUST run** to
    verify convergence. Do not stop on a fix-round.
11. Stop the loop as clean only when **a verify round (no edits) returns
    no actionable findings from any reviewer** in any included repo and
    validation is green across the graph.

If the loop hits the round cap:

- stop and summarize unresolved findings
- distinguish true blockers from false positives and accepted non-blockers
- if findings are still surfacing at the cap, that's a signal — either
  the spec is over-detailed (consider simplifying), the reviewer set
  is producing diminishing returns (acceptable to ship with a recorded
  follow-up), or there's a genuine gap (don't ship; raise the cap or
  reassess)
- do not push or open PRs from this command unless the user explicitly asks

## Final Report

Return a concise review-cycle report:

```text
## Review Cycle Result
- Status: clean | partial | blocked | findings-only
- Repos: <ordered repo list with upstream/downstream roles>
- Worktrees: <paths>
- Branches: <branches>
- Validation: <commands run>
- Reviews: <rounds and tools>
- Docs: <updated, not needed because..., or findings only>
- Dependency order: <upstream -> downstream edges or none>
- Remaining: <none or concrete findings/blockers>
```
