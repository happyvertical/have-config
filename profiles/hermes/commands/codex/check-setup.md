---
description: "Verify this agent's HappyVertical service access."
---

# /check-setup

Verify that this workstation or agent container is correctly connected to
HappyVertical services. Do not print secrets, tokens, cookies, passwords, or
decrypted values.

Produce a concise setup report with columns:

| Service | Check | Result | Evidence | Next action |
| --- | --- | --- | --- | --- |

Use `OK`, `Blocked`, or `Skipped` for each result. `Skipped` is only valid when
the service is intentionally not enabled for this agent.

Run these checks:

1. Email identity
   - Confirm `HV_AGENT_EMAIL` or an equivalent local account identity is set.
   - If a mail connector or CLI is available, verify the account can list or
     read its own mailbox metadata without exposing message contents.
2. HappyVertical IDP
   - Confirm `https://idp.happyvertical.com` is reachable.
   - If authenticated browser/session/CLI access is available, verify the
     assigned account can authenticate.
3. Vikunja project management
   - Confirm `https://todo.happyvertical.com` is reachable.
   - If `agent-contract.json` or `project-brief.md` exists, confirm the
     configured project, board, buckets, and labels match the selected contract.
   - If `HV_VIKUNJA_URL` and `HV_VIKUNJA_TOKEN` are set, make a read-only API
     request that proves access to the configured project board.
4. Warden
   - Confirm `https://warden.happyvertical.com` is reachable.
   - Verify the agent can access its approved credential source without
     printing any secret value.
5. OxiCloud file sharing
   - Confirm `https://drive.happyvertical.com` is reachable.
   - If `rclone` and an OxiCloud/WebDAV remote are configured, run a read-only
     listing or config check.
6. Context Forge memory and prompts
   - Confirm `https://context.happyvertical.com` is reachable.
   - Verify the agent is configured to use Context Forge for prompts,
     resources, and memory. If Hindsight or Context Forge MCP tools are
     available, perform a harmless recall/list/read check against the expected
     HappyVertical memory bank.
   - Verify `HV_CONTEXTFORGE_SNAPSHOT_DIR` exists when Context Forge snapshots
     are expected for install-time materialization.
7. Zulip chat gateway
   - Confirm `https://chat.happyvertical.com` is reachable.
   - Confirm `hermes config path` resolves to a local config file and that it
     has `platforms.zulip.enabled: true` when Zulip chat response is expected.
     If credentials are present but the config is not enabled after bootstrap,
     mark gateway readiness as `Blocked`.
   - Confirm `ZULIP_SITE`, `ZULIP_EMAIL`, and `ZULIP_API_KEY` are present
     when Zulip chat response is expected; do not print their values.
   - Report whether authorization is configured with `ZULIP_ALLOWED_USERS` or
     explicit `ZULIP_ALLOW_ALL_USERS=true`; otherwise mark response readiness as
     `Blocked` even if authentication succeeds.
   - If a Hermes Zulip gateway adapter is configured, verify `GET /api/v1/users/me`
     succeeds for the configured account and that the `/api/v1/register` + `/api/v1/events`
     long-poll listener can start without auth errors.
   - Report missing Zulip account API credentials as `Blocked` with the variable names.
8. Hermes Dev Team Mode
   - If Dev Team Mode is expected, confirm the local Hermes config has
     `dev_team.enabled: true`; otherwise mark it `Skipped`.
   - Confirm the manager identity resolves from `dev_team.manager_identity`,
     `ZULIP_EMAIL`, or `HV_AGENT_EMAIL`.
   - Confirm Vikunja access is available because main project boards and the
     per-manager project are the source of truth.
   - Confirm the configured manager project name follows
     `Hermes Manager - <email>`.
   - Confirm missing main-board buckets can be provisioned by the Hermes
     runtime. Setup checks should report missing buckets but not require manual
     creation.
   - Confirm `hv-hermes-dev-team-manager` is installed and executable when the
     sidecar dispatcher is expected to run on this machine.
   - Confirm `~/.hermes/.env` or the configured sidecar env file can supply
     local-only values that should not be committed.
   - Confirm `HV_HERMES_WORKER_COMMAND` or an equivalent
     `dev_team.worker_command` is configured before worker dispatch is marked
     ready.
   - Confirm repo search roots, worktree root, and integration root are
     configured and point outside repo-tracked source directories unless the
     local task explicitly requires otherwise.
   - If a dev server URL is configured for the active project or task, verify it
     is reachable from the local network.
9. Agent contract and permissions
   - Confirm `agent-contract.json`, `project-brief.md`, and `agent-lock.json`
     exist when `HV_AGENT_CONTRACT` is set.
   - Confirm the lockfile records the selected contract slug, identity, primary
     repo, and Hindsight bank.
   - Confirm repo access matches the contract permission summary without
     broadening scope.
   - Confirm Kubernetes namespace access is limited to the contract namespaces
     and the Hermes runtime namespace.
   - Confirm SOPS readiness by checking expected profile names, encrypted file
     presence, and key names only. Do not decrypt or print secret values unless
     the user explicitly requests a safe secret operation.
   - Confirm have-config freshness by comparing the installed source revision
     in `agent-lock.json` with the local `have-config` checkout when available.
10. Project leader operating mode
   - Confirm substantial development work is represented on Vikunja before
     implementation starts.
   - Confirm the task uses the contract buckets: `Inbox`, `Ready`,
     `In Progress`, `Review`, `Blocked`, and `Done`, unless the contract names
     a project-specific exception.
   - Confirm long-running, cross-repo, CI, deploy, or large development work
     uses sub-agents/sessions and records worker state on the main task.

If a check cannot be performed noninteractively, mark it `Blocked` and state
the missing credential, connector, environment variable, CLI, or local config.

If a Context Forge snapshot or local override replaced this command during
install, follow the generated installed command instead of this org fallback.
