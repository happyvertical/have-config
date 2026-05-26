# Hermes Dev Team Mode

Hermes Dev Team Mode turns one Hermes agent into the manager for a local
development team. The human communicates with the manager in Zulip, watches
canonical issues move through Vikunja project boards, and QA-tests a live dev
server exposed on the local network.

## Operating Model

- The current Hermes agent is the manager.
- The manager identity is the Hermes/Zulip email address.
- Each manager owns one internal Vikunja project named
  `Hermes Manager - <email>`.
- Main project boards remain the canonical user-visible source of issue state.
- Worker agents only work internal manager-project tasks.
- The manager is the only agent that moves main-board cards and writes to the
  live integration worktree used by the dev server.

## Board Model

Main project boards should use these buckets:

- `To-Do`
- `Blocked`
- `Doing`
- `Review`
- `Done`

Manager projects should use these buckets:

- `Queued`
- `Working`
- `Integrating`
- `Blocked`
- `Closed`

When Dev Team Mode watches a board, missing buckets are provisioned
automatically by the Hermes runtime. Setup checks may report missing buckets,
but should not require a human to create them by hand.

## Zulip Intake

The manager triages Zulip QA messages instead of creating a task for every
message. For each message, it decides whether to:

- create a new canonical main-board issue
- update or deduplicate against an existing issue
- ask for a short clarification
- ignore conversational noise

Status updates should be quiet unless asked. The manager may still acknowledge
new issue creation, ask clarifying questions, or report blockers that require
human action.

## Worker Dispatch

Workers are per-task runs. For each dispatched issue, the manager:

1. Infers the local repository from task text, task description, linked GitHub
   URLs, or repo-like strings.
2. Creates a dedicated git worktree under the configured Hermes worktree root.
3. Creates a linked worker task in the manager project.
4. Runs the configured worker command template with task and worktree context.
5. Reviews the worker diff.
6. Applies accepted changes into the integration worktree.
7. Moves the main-board issue to `Review` for human QA.

The worker command is configured locally with `HV_HERMES_WORKER_COMMAND` or the
equivalent Hermes config value. `hv-hermes-dev-team-worker` is the default
worker wrapper supplied by have-config; it launches a non-interactive Hermes run
inside the sidecar-created worktree and passes the task/worktree context through
the `HERMES_DEV_TEAM_*` environment variables. Workers must not edit the
integration worktree directly.

## Manager Sidecar

`hv-hermes-dev-team-manager` is the first runtime sidecar for this mode. It is
installed as a reusable no-agent script by `have-config/install.sh` and can be
run once from a scheduler or continuously:

```bash
hv-hermes-dev-team-manager --once
hv-hermes-dev-team-manager --loop --interval 30
```

The sidecar reads `~/.hermes/config.yaml` by default and loads
`~/.hermes/.env` for local environment values such as
`HV_HERMES_WORKER_COMMAND`, `HV_VIKUNJA_TOKEN`, and Zulip identity variables.
Use `--config` or `--env-file` to point it at non-default files.

The sidecar performs mechanical coordination only:

- ensures the per-manager project and configured buckets exist
- provisions missing buckets on watched main kanban boards
- finds undispatched tasks in the first main bucket, usually `To-Do`
- creates one internal worker task in the manager project
- creates an isolated git worktree for the worker
- launches `dev_team.worker_command` or `HV_HERMES_WORKER_COMMAND`
- tracks worker exit status and moves worker cards to `Integrating` or
  `Blocked`

The sidecar does not review diffs or apply changes to the integration worktree.
That remains manager-agent work before a main-board card moves to `Review`.

## Suggested Hermes Config

```yaml
platforms:
  zulip:
    enabled: true

dev_team:
  enabled: true
  manager_identity: "${ZULIP_EMAIL}"
  manager_project_name_template: "Hermes Manager - {email}"
  watch_projects: "all"
  repo_search_roots:
    - ~/Work/happyvertical/repos
    - ~/Work/anytown/repos
  worktree_root: ~/.hermes/dev-team/worktrees
  integration_root: ~/.hermes/dev-team/integration
  worker_command: "hv-hermes-dev-team-worker"
  main_buckets: [To-Do, Blocked, Doing, Review, Done]
  manager_buckets: [Queued, Working, Integrating, Blocked, Closed]
  status_updates: on_request
  integration_gate: review_only
  poll_interval_seconds: 30
```

## Blocking Conditions

Move the main-board issue or worker task to `Blocked` when:

- no local repository can be inferred
- the worker command is missing or fails before producing reviewable output
- a required credential or service is unavailable
- the manager cannot apply the worker diff cleanly
- the dev server or integration worktree is not reachable

Blocker comments must name the first concrete blocker and the smallest next
action. Never include secrets, tokens, cookies, passwords, or decrypted values.
