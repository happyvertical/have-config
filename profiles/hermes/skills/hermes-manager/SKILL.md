---
name: hermes-manager
description: Use when operating Hermes Dev Team Mode, coordinating worker agents, managing Vikunja board state, or integrating fixes into a live dev-server worktree.
metadata:
  short-description: Manage local Hermes developer workers
---

# Hermes Manager Procedure

Use this procedure when the current Hermes agent is acting as the manager for
local developer workers. The human talks to this manager in Zulip and watches
canonical issue cards on Vikunja main project boards. Do not print or store
tokens, cookies, passwords, or decrypted secret values.

## Manager Responsibilities

1. Own communication with the human.
   - Respond in Zulip as the single point of contact.
   - Keep status quiet unless asked, except for clarifying questions,
     acknowledgements of created issues, and blockers requiring human action.
2. Own main-board state.
   - Main project cards are canonical user-visible issues.
   - Move main cards through `To-Do`, `Blocked`, `Doing`, `Review`, and `Done`.
   - Auto-provision missing expected buckets through the Hermes runtime.
3. Own worker dispatch.
   - Use one manager project named `Hermes Manager - <email>`.
   - Use manager-project buckets `Queued`, `Working`, `Integrating`,
     `Blocked`, and `Closed`.
   - Create one internal worker task per dispatched main-board issue.
4. Own live integration.
   - Workers must use isolated git worktrees.
   - Only the manager may apply accepted worker output to the integration
     worktree used by the local-network dev server.
   - Integration is gated by manager review of the diff; local tests are
     optional unless the task or repo instructions require them.

## Zulip Intake

For each QA message, decide whether to create a new issue, update an existing
issue, ask for clarification, or ignore conversational noise. Do not create a
Vikunja task for every Zulip message. Prefer actionable main-board issues with
clear repro context.

## Repository Inference

Infer the target repository from task text, descriptions, linked GitHub URLs,
and repo-like strings. Search configured repo roots such as
`~/Work/happyvertical/repos` and `~/Work/anytown/repos`, matching task GitHub
URLs to local git remotes. If inference is ambiguous or missing, block the task
and ask the human for the repo.

## Worker Run Contract

For each per-task worker run, provide these values through the configured worker
command template or environment:

- main Vikunja task ID and URL
- worker Vikunja task ID and URL
- repository path
- worker worktree path
- branch name
- integration worktree path
- dev server URL when known
- manager identity

The worker should return reviewable output in its worktree and exit `0` when it
is ready for manager review. Non-zero exits, dirty state that cannot be
understood, or missing output are blockers.

`hv-hermes-dev-team-manager` may perform the mechanical sidecar work: provision
Vikunja buckets, create worker tasks, create worker worktrees, launch the
configured worker command, and move finished worker runs to `Integrating` or
`Blocked`. Treat `Integrating` as a manager-review queue, not as approval to
apply changes automatically.

## Integration Gate

Before applying worker output:

1. Read the worker task, comments, and diff.
2. Confirm the diff is scoped to the main-board issue.
3. Apply accepted changes into the integration worktree.
4. Move the main-board issue to `Review`.
5. Leave the worker task `Closed` or `Blocked` with a concise status comment.

If the patch does not apply cleanly, move both the worker task and main-board
issue to `Blocked` with the smallest next action.
