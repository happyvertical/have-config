---
name: hermes-ops
description: Use when setting up or recovering Hermes operational watchers, Vikunja pickup state, or blocked task handling.
metadata:
  short-description: Hermes operational watcher procedure
---

# Hermes Operations Procedure

Use this procedure for Hermes agents that pick up scheduled Vikunja work,
recover blocked tasks, or run no-agent watcher scripts. Do not print or store
tokens, cookies, passwords, or decrypted secret values.

## Scheduled Vikunja Pickup State

1. Check the current task state in Vikunja before starting work.
   - Confirm the task is still assigned to this Hermes identity or explicitly
     available for pickup.
   - Read the latest task comments and activity before changing status.
2. Record pickup in Vikunja with a short comment:
   - agent identity or hostname
   - intended next action
   - expected next checkpoint time
3. Keep state in Vikunja as the source of truth.
   - Local state files are only watcher cursors.
   - If local state disagrees with Vikunja, trust Vikunja and refresh the
     watcher cursor.

## Blocked Task Recovery

1. Re-read the task, linked issue, and latest comments.
2. Identify the first concrete blocker:
   - missing credential or environment variable
   - unavailable service
   - ambiguous task scope
   - failing dependency or upstream issue
3. Add a Vikunja comment that names the blocker and the smallest next action.
4. If a no-agent watcher is configured, verify it still reports updates after
   the recovery comment.
5. Do not mark a task unblocked until the required credential, service,
   clarification, or dependency is actually available.

## Watcher Setup

The base have-config manifest provides these reusable no-agent scripts when
the resolver runs:

- `hv-hermes-vikunja-task-updates`
- `hv-hermes-github-cricket-issues`

The resolver links executable scripts into `~/.local/bin` when that location is
managed by have-config. Use cron, systemd user timers, or the local scheduler
already present on the host.

Required local environment:

- `HV_VIKUNJA_TOKEN` for Vikunja polling
- `HV_VIKUNJA_URL` when not using `https://todo.happyvertical.com`
- `GITHUB_TOKEN` or `GH_TOKEN` for GitHub polling when rate limits or private
  repository access matter
- `HV_HERMES_STATE_DIR` when watcher cursor files should live somewhere other
  than `$XDG_STATE_HOME/hv` or `~/.local/state/hv`
- `ZULIP_SITE_URL`, `ZULIP_EMAIL`, and `ZULIP_API_KEY` when the Hermes gateway
  should join HappyVertical Zulip and long-poll for immediate chat responses

Recommended cadence:

- Vikunja task updates: every 5 to 15 minutes
- GitHub cricket-labeled issues: every 10 to 30 minutes

Watcher state files are cursors, not task records. If a cursor is stale or
corrupt, move it aside and run the watcher once to initialize from the current
remote state.

## Zulip Gateway Setup

HappyVertical's primary chat is Zulip at `https://chat.happyvertical.com`.
When a Hermes agent is expected to respond there immediately, configure a
per-agent Zulip account in the local Hermes `.env` or approved secret source.
Do not require a Zulip bot account; cricket currently uses a normal Zulip
account with API credentials.

- `ZULIP_SITE_URL=https://chat.happyvertical.com`
- `ZULIP_EMAIL`
- `ZULIP_API_KEY`
- optional `ZULIP_ALLOWED_USERS`, `ZULIP_ALLOW_ALL_USERS`, `ZULIP_HOME_CHANNEL`,
  and `ZULIP_REQUIRE_MENTION`

Enable the platform in the local Hermes config as well:

```yaml
platforms:
  zulip:
    enabled: true
```

For bundled Hermes platform plugins, this config flag is the canonical activation
step. Do not make agents troubleshoot `plugins.enabled` first; the bundled Zulip
platform is auto-discovered unless a local Hermes build has explicitly diverged.

The Hermes gateway adapter should use Zulip's `/api/v1/register` and
`/api/v1/events` long-poll loop. If credentials are missing, mark Zulip setup as
blocked with the missing variable names; never ask the user to paste the secret
into task comments or logs.
