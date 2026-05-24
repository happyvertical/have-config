# HappyVertical Infrastructure

This document is the organization-level map of services that agents and humans
should expect when working in HappyVertical environments. Account credentials are
per user or per agent and must stay out of git.

## Services

| Service | URL | Purpose | CLI status |
| --- | --- | --- | --- |
| Email | per-account | Human and agent identity | Account-specific |
| HappyVertical IDP | `https://idp.happyvertical.com` | Identity provider and SSO | Verify through browser/session or available connector |
| Warden | `https://warden.happyvertical.com` | Password and shared secret access | Credential source; never print secret values |
| OxiCloud | `https://drive.happyvertical.com` | File sharing | Use WebDAV-capable tooling such as `rclone` |
| Vikunja | `https://todo.happyvertical.com` | Project management | Official CLI is server/container admin only; have-config provides a reusable Hermes notification watcher |
| Stoat | `https://stoat.happyvertical.com` | Chat and collaboration | No standard CLI selected yet |
| Bifrost | `https://bifrost.happyvertical.com` | Gateway | No standard CLI selected yet |
| Context Forge | `https://context.happyvertical.com` | Prompts, resources, and memory | Export install-time snapshots |

## Secrets And Accounts

- Every workstation and Hermes agent has its own account identity.
- Passwords and shared credentials should be distributed through Warden.
- SOPS may be used for machine-local encrypted environment files, but committed
  repos should only contain templates and non-secret policy.
- Installers may hard-fail missing environment variables only for capabilities
  explicitly enabled with `HV_ENABLED_CAPABILITIES`.

## Context Forge Snapshot Policy

Context Forge is the dynamic source for organization prompt and resource policy.
Installers should materialize snapshots into local generated files and record
the selected content hash in `agent-lock.json`. Runtime agent behavior should
not require live Context Forge access.

## Reusable Operational Scripts

have-config can materialize reusable operational scripts declared in
`hv/manifest.json`. Current Hermes no-agent scripts poll Vikunja task updates
and GitHub open issues labeled `cricket`; credentials must come from local
environment variables or approved secret tooling.
