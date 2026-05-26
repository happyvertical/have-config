# Hermes Zulip Gateway

HappyVertical's current team chat is Zulip at `https://chat.happyvertical.com`.
Hermes agents that need immediate chat response should use a dedicated per-agent
Zulip account through the Hermes gateway using Zulip's long-poll event queue
API. Do not require a Zulip bot account unless a specific deployment has chosen
one; cricket currently uses a normal Zulip account with API credentials.

## Required local secrets

Do not commit these values. Store them in the local Hermes `.env`, Warden, or the
approved machine-local secret source:

- `ZULIP_SITE_URL=https://chat.happyvertical.com`
- `ZULIP_EMAIL` — Zulip account email for the agent identity
- `ZULIP_API_KEY` — Zulip API key for that agent account

Optional routing and authorization:

- `ZULIP_ALLOWED_USERS` — comma-separated Zulip user IDs or emails allowed to DM the agent
- `ZULIP_ALLOW_ALL_USERS=true` — only for trusted/dev environments
- `ZULIP_HOME_CHANNEL` — default delivery target, e.g. `dm:12345` or `stream:general:ops`
- `ZULIP_REQUIRE_MENTION=false` — answer all visible stream messages; default is to answer stream mentions and all DMs

Authorization readiness requires either `ZULIP_ALLOWED_USERS` or explicit
`ZULIP_ALLOW_ALL_USERS=true`; otherwise a default-deny adapter may authenticate
successfully but refuse to respond to users.

## Runtime expectation

Before starting the gateway, the local Hermes config must enable the Zulip
platform. Environment variables alone only make credentials available; they do
not opt the gateway into running the Zulip adapter.

```yaml
platforms:
  zulip:
    enabled: true
```

Bundled Hermes platform plugins such as Zulip are auto-discovered by Hermes.
Do not require agents to add `platforms/zulip` or `zulip-platform` to
`plugins.enabled` unless a local Hermes build explicitly changes bundled plugin
loading. The canonical setup knob is `platforms.zulip.enabled: true` plus the
credential env vars above and routing/authorization env vars.

A Hermes Zulip adapter should:

1. Authenticate with Zulip Basic auth using `ZULIP_EMAIL:ZULIP_API_KEY`.
2. Register a message event queue with `POST /api/v1/register`.
3. Long-poll `GET /api/v1/events` with the queue ID and last event ID. Register
   only message events when possible (for example, `event_types=["message"]`) to
   avoid unnecessary gateway wakeups.
4. Ignore messages sent by the configured agent identity itself.
5. Respond to DMs from allowed users immediately and to stream messages only when mentioned unless
   `ZULIP_REQUIRE_MENTION=false` is explicitly configured.
6. Use default-deny authorization unless `ZULIP_ALLOWED_USERS` is configured or
   `ZULIP_ALLOW_ALL_USERS=true` is explicitly set for a trusted/dev environment.
7. Re-register the queue when Zulip returns an expired or invalid queue ID.
8. Show responsiveness while the agent is working by sending Zulip typing
   notifications through `POST /api/v1/typing`:
   - DMs use `type=direct`, `op=start|stop`, and `to` as the JSON-encoded
     recipient user ID list (for example, `[8]`).
   - Stream topics use `type=stream`, `op=start|stop`, numeric `stream_id`, and
     `topic`.
   - Skip typing notifications when only a stream name is available and no
     numeric `stream_id` has been resolved.
9. Send responses through `POST /api/v1/messages` without logging token values.

## Setup verification

A non-secret verification pass should report:

- whether Hermes config has `platforms.zulip.enabled: true`
- whether `ZULIP_SITE_URL`, `ZULIP_EMAIL`, and `ZULIP_API_KEY` are present
- whether `GET /api/v1/users/me` succeeds for the configured account
- whether a register/events long-poll loop starts without auth errors
- whether typing start/stop payload construction covers both `dm:<user_id>` and
  `stream:<stream_id>` targets without exposing secrets
- the configured home channel identifier, if any, without exposing message content

If credentials are missing, report Zulip as `Blocked` with the missing variable
names rather than asking for or printing secret values.
