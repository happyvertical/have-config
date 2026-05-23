---
description: Run a repeatable review/fix/retest loop over current work, optionally across multiple repos, without opening PRs or shipping.
---

# /review-cycle

Run a bounded review cycle on the current work independent of shipping. Default to 3 rounds unless the user passes `rounds=N`.

## Hard Rules

- Respect the global worktree isolation policy before making edits. If the current checkout is a primary checkout such as `/Users/will/Work/.../repos/...`, move the work to a dedicated worktree and branch before editing, preferably under `/Users/will/.codex/worktrees/` with a `codex/` branch prefix.
- Do not mix this session's edits with unrelated dirty files. Preserve user changes, and ask only when the current work cannot be separated safely.
- Do not use destructive cleanup commands such as `git reset --hard`, `git checkout --`, or `git clean` unless the user explicitly asks for that exact destructive action.
- Do not use `claude ultrareview` or any `ultrareview` command. Use the normal claude-cli in non-interactive print mode for review.
- Every external review command must be allowed at least 15 minutes. When using codex-cli's command tools, set the command timeout to at least `900000` ms for review commands.
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
   - `gh` when copilot-cli is reached through `gh copilot`
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

### Run codex-cli review

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

### Run claude-cli review

claude-cli does not fetch its own diff — pipe `pr-review` output without `--no-diff`:

```bash
pr-review --base <base> | claude -p --permission-mode plan
```

- Use `claude -p` in non-interactive mode.
- Prefer read-only/plan permissions for the review run (`--permission-mode plan`).
- Disallow edit/write tools where supported.

### Run copilot-cli review

**This step is non-optional for the "catch before push" intent.** The
Copilot PR review *bot* only fires after a PR is opened — too late to
prevent the round-trip the review-cycle exists to compress. The copilot-cli runs locally pre-push and gives you copilot-cli's blind-spot
coverage before the bot has a chance to comment.

copilot-cli expects the prompt to carry its own context. **The
invocation must enforce read-only at the permission layer — prompt
instructions are advisory, tool permissions are enforcement.** If
copilot-cli can use write/edit-capable tools, a "review" pass can mutate
the working tree mid-round, breaking the same-commit guarantee the
loop relies on.

`--allow-all-tools` is *not* read-only — it grants write/edit
capability and would let the model mutate the working tree mid-review.
Don't use it. But `--available-tools shell,read` alone *also doesn't
work* in non-interactive mode — it only filters which tools the model
can *see*, not which it can run without approval. In `-p` mode there's
no place to ask for permission, so tool calls get denied with
`Permission denied and could not request permission from user`. The
review then runs with no repository context.

The correct shape is **explicit per-command `--allow-tool` flags** for
the specific read-only commands a review needs. Verify against
`gh copilot -- --help` and `gh copilot -- help permissions` for the
syntax your CLI version supports; example for current copilot-cli:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
gh copilot -- -p "$(pr-review --base <base> --pretty)" \
  -C "$REPO_ROOT" \
  --add-dir "$REPO_ROOT" \
  --disallow-temp-dir \
  --allow-tool 'shell(git diff)' \
  --allow-tool 'shell(git log)' \
  --allow-tool 'shell(git show)' \
  --allow-tool 'shell(git status)' \
  --allow-tool 'shell(git rev-parse)' \
  --allow-tool 'shell(rg)' \
  --allow-tool 'shell(cat)' \
  --allow-tool 'shell(head)' \
  --effort xhigh
```

The `-C` / `--add-dir` / `--disallow-temp-dir` trio is **scope
hygiene**, not a security boundary: they keep the reviewer focused
on the repo and prevent it from wandering into unrelated files in
your `/tmp` or wherever else the shell was invoked from. That
reduces noise in findings — not a vulnerability fix. The reviewer
is running locally with your credentials and can already see
anything you can see; that's how local CLI tools work.

**When stricter sandboxing actually matters** (and the above flags
are insufficient — you need a sanitized temp checkout):
- Reviewing PRs from untrusted contributors (OSS maintainership)
  where the diff could contain prompt-injection asking the model to
  read your `.env` and quote it into findings the contributor sees
- CI environments where the reviewer runs unattended and findings
  get auto-posted to public PR comments
- Workspaces with secrets in untracked files that you don't want
  surfaced even in your own review output

For the normal HappyVertical case — engineer reviewing their own
org's PR pre-push, findings going to their own terminal — none of
that applies. The flags above are enough.

Add `--deny-tool` for any specific commands you want hard-blocked.
The per-command `--allow-tool` allowlist is **mostly** read-only —
but it is NOT a hard write-prevention boundary, because copilot-cli
matches at first-level subcommand granularity. `--allow-tool
'shell(git diff)'` approves any `git diff …` invocation including
write-capable forms like `git diff --output=path` which can dirty
the working tree. Similarly, `shell(rg)` permits redirection-style
flags depending on shell escaping. The prompt's "don't modify
files" instruction is defense-in-depth, but the structural
guarantee for "the reviewer ran against the same commit" is the
**post-review tree-clean check**: after every reviewer
invocation, run `git status --porcelain` (and `git diff` if you
want detail). If the working tree changed, the round is invalid —
the reviewer didn't stay read-only, the commit being reviewed
moved, and the same-commit guarantee Step 11 depends on is broken.
Either fail the round and restart from a clean checkout, or move
copilot-cli into a disposable worktree if this becomes a recurring
issue in your workflow.

- Use `--pretty` so copilot-cli receives the prompt as readable markdown
  rather than the JSON-instruction format.
- Pass `--` after `gh copilot` to forward flags to the underlying
  `copilot` binary; otherwise `gh` may interpret them.
- `--effort xhigh` matches codex-cli's reasoning depth; tune down if the
  diff is small and you want faster runs.
- The prompt itself also instructs not to modify files. That's
  defense-in-depth, not the primary enforcement — the permission
  flags do the actual blocking.

**Known blockers and fallbacks** (real failures we've seen):

- **`Access denied by policy settings`** — the org's Copilot policy
  is disabling CLI use. Fix at https://github.com/settings/copilot
  (personal) and/or your org's Copilot policies page (admin). Until
  enabled, copilot-cli cannot run pre-push.
- **`Failed to authenticate. API Error: 401`** on `claude -p` — happens
  when this command is invoked from inside an active Claude Code
  session; OAuth credentials don't propagate to spawned children.
  Workaround: set `ANTHROPIC_API_KEY` env var on the child invocation,
  or run review-cycle from a terminal / CI / codex-cli session instead.

**When a reviewer is unavailable**: proceed with the others *and*
record in the final report which reviewer was skipped and why.
**Status MUST drop to `partial` when any required reviewer is
skipped** (codex-cli, copilot-cli, and claude-cli subprocess are all
required by default). Never silently drop. Never report `clean`
with a skipped required reviewer — `/ship` gates on `Status: clean`,
and a soft skip would let unreviewed code merge.

If copilot-cli is the unavailable one specifically, record this in
the final report's `Skipped reviewers` field with reason. Downstream
(`/ship`, or the human invoking review-cycle directly) reads the
report and decides whether to open the PR as a **draft** so the
Copilot bot can review before merge candidacy. `/review-cycle`
itself never opens or pushes PRs — that's `/ship`'s job — so this
fallback is something the report enables, not something review-cycle
executes.

### For all three

- Use a review command timeout of at least 15 minutes.
- Capture stdout and stderr to separate files in the temp review directory — malformed or empty findings almost always have the cause in stderr.
- Treat each tool's findings as evidence to verify against the code, not as orders to apply. Vague claims get dismissed; concrete file:line citations with named failure paths get acted on.
- After all three runs complete, merge findings into one checklist grouped by severity (see "Review/Fix Loop" below). Prefer findings flagged by ≥2 reviewers when severity is medium or low; high-severity findings from a single reviewer still warrant verification.

### Optional: capture for calibration

If the repository has a `.pr-review/extensions.md`, also append `| pr-review-capture` to one of the runs (typically claude-cli or codex-cli) so the findings are stored at `.pr-review/history/<sha>.json`. Later, `pr-review-tune --last 10` can compare stored findings against the review comments PRs actually received and propose refinements to the checklist. This closes the feedback loop so the checklist gets sharper over time.

```bash
pr-review --base <base> | claude -p --permission-mode plan | pr-review-capture | tee /dev/tty
```

## Review/Fix Loop

Run up to `rounds` review rounds. The argument default is `3`
regardless of change type (set at the `rounds=N` arg above). For
documentation / reviewer-checklist content, consider passing
`rounds=5..10` because each round catches progressively narrower
factual edge cases — there's no auto-detection that bumps the cap
for doc work.

**Hard rules for the loop** (these prevent the "stopped too early"
*and* "looped too long on trivia" failure modes):

- **Each round runs all reviewers in parallel against the SAME commit**
  — not sequentially against each other's fixes. Sequential cascading
  makes findings depend on which reviewer ran first and obscures
  whether reviewers actually agree on the latest state.
- **A fix-round on substantive (P0-P2) findings is never the final
  round.** If you just pushed a fix for a real bug, you MUST run
  another round to confirm it didn't introduce a new one.
- **The loop exits when no P0/P1/P2 findings remain — not when
  every reviewer returns zero findings.** P3 / nit-level findings
  (polish, narrow factual edges, cosmetic placement) get triaged
  three ways (fix inline if cheap, record in the final report if
  worth tracking, file as follow-up if bigger) but never extend the
  loop. Running another full ensemble round just to verify a
  one-line wording tweak is technical perfectionism that burns
  reviewer cycles without changing what ships.
- **Convergence is per-commit for behaviour-changing fixes** (P0/P1/P2
  and any non-fix code changes). Reviewer A returning clean against
  commit X doesn't mean clean against commit Y when Y changes
  behaviour — re-run all reviewers. **P3-only commits do not reset
  convergence**: if the only change since the last clean verify
  round is a P3 wording tweak, you don't need another full ensemble
  pass.
- **One reviewer returning clean is NOT convergence — the whole
  ensemble must return clean.** A reviewer that didn't run can't
  have caught the bug another reviewer would have. Two failure
  modes to guard against:
  - *Silent solo*: only running one reviewer per round (e.g.
    "codex-cli is fast and reliable, I'll skip the others") and
    declaring convergence when it returns 0. The whole point of
    the ensemble is non-overlapping blind spots. A real example:
    if you solo a single reviewer for ~12 rounds and then add a
    second reviewer for round 13, expect that second reviewer to
    immediately surface findings the first kept missing.
  - *Unavailable ≠ clean*: if a reviewer errored (auth, policy,
    network, env), that's a missing signal — not a clean signal.
    Record the unavailability explicitly in the final report.
    Either resolve the blocker and retry, or accept the
    reduced-coverage tradeoff with rationale, but do not count
    the absence as agreement.

For each round, process repositories in dependency order:

1. Run validation before review if files changed since the previous validation pass.
2. Run codex-cli, claude-cli, and copilot-cli reviews for each repository in dependency order.
3. Merge findings into a single checklist by severity:
   - `P0/P1`: correctness, data loss, security, broken build, failing tests. **Always block. Always loop.**
   - `P2`: likely bug, missing test, missing docs for changed behavior. **Block by default; loop unless explicitly accepted with rationale in the final report (which `/ship` then copies into the PR body when creating the PR).**
   - `P3`: maintainability or polish with clear benefit; narrow factual edges affecting tiny version windows or rare paths. **Never block. Never extend the loop just to verify a P3 fix.** For each P3 finding, pick one based on cost vs. value:
     - **Cheap to fix → fix inline in the same commit/PR.** No verify round needed; group with other fixes if any. (Most P3 wording/clarity tweaks fall here.)
     - **Worth tracking but not blocking → record in the final report** as accepted non-blocker with brief rationale. If a PR already exists, also copy into the PR body; otherwise `/ship` propagates the report into the PR body at PR creation time.
     - **Bigger than this PR's scope → file as follow-up issue**, link from the final report (and PR body, when one exists).
4. Verify each finding against the code. Do not blindly patch speculative review comments.
5. If `no-fix` was passed, stop after reporting findings.
6. Address all valid P0/P1 findings (mandatory) and all valid P2 findings (mandatory unless explicitly accepted in the final report with a one-line rationale) in priority order.
7. Add or adjust tests for bug fixes and behavior changes.
8. Rerun relevant validation after edits.
9. If upstream fixes change the contract consumed downstream, rerun affected downstream validation and review even if that downstream repo had already passed in the current round.
10. **If a P0/P1/P2 fix was pushed in this round, the next round MUST run** to verify the fix didn't break something. Do not stop on a P0/P1/P2 fix-round.
11. Stop the loop as `clean` only when **ALL THREE** conditions
    hold across the graph:
    - a verify round returns no *unaccepted* P0/P1/P2 findings
      from any reviewer in any included repo,
    - validation is green across the graph, AND
    - every required reviewer actually ran in the verify round
      (any skipped/unavailable reviewer → status is `partial`,
      not `clean`, per the Status contract below).

    Don't conflate "no findings surfaced" with "clean" — a
    reviewer that didn't run produced no findings because it
    didn't run, not because none exist.

    Reviewers may continue surfacing an accepted P2 in subsequent
    rounds (they have no way to know it was accepted); the
    acceptance lives in the final report, and the stop condition
    discounts it. P3/nit findings at exit time get recorded in the
    final report, not fixed in this PR (consumers like `/ship`
    are responsible for surfacing them in the PR body when the PR
    exists).

If the loop hits the round cap:

- stop and summarize unresolved findings
- distinguish true blockers from false positives and accepted non-blockers
- if findings are still surfacing at the cap, that's a signal — either
  the spec is over-detailed (consider simplifying), the reviewer set
  is producing diminishing returns (acceptable to ship with a recorded
  follow-up), or there's a genuine gap (don't ship; raise the cap or
  reassess)
- **special case: a P0/P1/P2 fix landed in the final permitted round**
  — Rule 10 requires the next round MUST run to verify, but the cap
  forbids it. Report status as `partial` (not `clean` and not
  `blocked`): the fix may be correct but no verify round confirmed
  it. Note in the final report that the verify round was blocked by
  the cap and recommend re-running with `rounds=N+1` (or higher) so
  the verify round can complete. Don't report `clean` just because
  the post-fix tree has no surfaced findings — those findings were
  never sought.
- do not push or open PRs from this command unless the user explicitly asks

## Final Report

Return a concise review-cycle report:

```text
## Review Cycle Result
- Status: clean | partial | blocked | findings-only
  (clean = no P0/P1 + all P2 fixed-or-accepted + ALL required reviewers ran
            + validation green;
   partial = otherwise-clean but at least one required reviewer was skipped;
   blocked = unaccepted P0/P1/P2 remaining (whether before or at the
            round cap), or validation failed. A round-cap exit with
            ONLY P3/nit findings remaining is NOT blocked — those
            findings go in the accepted non-blockers field and Status
            stays clean (or partial if a required reviewer was
            skipped). Without this carve-out, the round-cap definition
            would re-block on the exact trivia loop these rules are
            designed to exit;
   findings-only = `no-fix` was passed)
- Repos: <ordered repo list with upstream/downstream roles>
- Worktrees: <paths>
- Branches: <branches>
- Validation: <commands run>
- Reviews: <rounds and tools; e.g. "3 rounds: codex-cli + claude-cli + copilot-cli". List ALL required reviewers that ran — the parent agent's own review does NOT substitute for any subprocess reviewer (the Hard Rules require independent subprocesses; the orchestrator agent's inline opinion does not count as a separate reviewer)>
- Docs: <updated, not needed because..., or findings only>
- Dependency order: <upstream -> downstream edges or none>
- Remaining blockers (P0/P1, or unaccepted P2): <none or concrete blockers>
- Accepted P2 (with rationale): <none, or list with rationale — this is
  the canonical record; `/ship` (or the human creating the PR) copies
  these into the PR body so human reviewers see the deliberate choice>
- Accepted non-blockers (P3/nit): <none, or list with brief rationale —
  also surfaced into the PR body by `/ship` at PR creation time>
- Skipped reviewers: <none, or which + why — never silently drop;
  any skipped required reviewer forces Status to `partial`>
```
