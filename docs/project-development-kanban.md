# Project Development Kanban SOP

Project-based Hermes agents are project leaders. They should use Vikunja at
`https://todo.happyvertical.com` as the canonical board for substantial project
work, including development, CI, deploy, incident, and secrets tasks.

## Default Buckets

Use these buckets unless the agent contract names a project-specific exception:

- `Inbox`: untriaged human requests, chat intake, or imported issues
- `Ready`: understood work with repo, acceptance criteria, and no known blocker
- `In Progress`: actively owned by the project Hermes or a worker session
- `Review`: PR opened, fix ready for operator review, or deploy awaiting check
- `Blocked`: waiting on credentials, clarification, upstream service, or failed
  dependency
- `Done`: accepted, merged, deployed/verified when required, and documented

## Intake And Triage

- When a human gives development work through Zulip, Telegram, or direct chat,
  find or create a Vikunja task before doing substantial implementation.
- Add a concise summary, acceptance criteria, primary repo, related repos,
  suspected deploy target, and priority if known.
- Add labels such as `bug`, `feature`, `ops`, `ci`, `deploy`, `secrets`, or
  `blocked`.
- Move the task to `Ready` only when the next action is clear.

## Execution

- Move the task to `In Progress` when starting work.
- Comment with the agent identity, intended next action, branch or worktree, and
  expected next checkpoint.
- Use sub-agents or long-running sessions for large development, CI debugging,
  deploy monitoring, cross-repo work, and long-running investigations.
- Link worker tasks or comments back to the main task. The manager/project
  Hermes owns integration, PR state, and final board movement.

## Status And Done

- Comment when work starts, blocks, opens a PR, CI fails, CI passes, deploy
  starts, deploy completes, or follow-up work is created.
- Do not put secrets, decrypted values, tokens, cookies, passwords, or recovery
  codes in Vikunja comments.
- Move work to `Done` only after the PR is merged and deployment is verified
  when deployment is relevant, or after the human accepts a non-code outcome.

