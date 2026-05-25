---
name: check-setup
description: Use when the user invokes /check-setup, check-setup, or asks to verify this Hermes agent's HappyVertical service access.
metadata:
  short-description: Verify HappyVertical agent setup
---

# Have Check Setup

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
   - If `HV_VIKUNJA_URL` and `HV_VIKUNJA_TOKEN` are set, make a read-only API
     request that proves access.
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
     If only env vars are present, mark gateway readiness as `Blocked` until the
     platform is enabled.
   - Confirm `ZULIP_SITE_URL`, `ZULIP_EMAIL`, and `ZULIP_API_KEY` are present
     when Zulip chat response is expected; do not print their values.
   - Report whether authorization is configured with `ZULIP_ALLOWED_USERS` or
     explicit `ZULIP_ALLOW_ALL_USERS=true`; otherwise mark response readiness as
     `Blocked` even if authentication succeeds.
   - If a Hermes Zulip gateway adapter is configured, verify `GET /api/v1/users/me`
     succeeds for the configured account and that the `/api/v1/register` + `/api/v1/events`
     long-poll path starts without auth errors.
   - Report missing Zulip account API credentials as `Blocked` with the variable names.

If a check cannot be performed noninteractively, mark it `Blocked` and state
the missing credential, connector, environment variable, CLI, or local config.

If a Context Forge snapshot or local override replaced this skill during
install, follow the generated installed skill instead of this org fallback.
