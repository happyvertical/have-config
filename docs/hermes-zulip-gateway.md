# Hermes Zulip Gateway

HappyVertical's current team chat is Zulip at `https://chat.happyvertical.com`.
Hermes agents that need immediate chat response should run a Zulip bot through
the Hermes gateway using Zulip's long-poll event queue API.

## Required local secrets

Do not commit these values. Store them in the local Hermes `.env`, Warden, or the
approved machine-local secret source:

- `ZULIP_SITE_URL=https://chat.happyvertical.com`
- `ZULIP_EMAIL` — Zulip bot email address
- `ZULIP_API_KEY` — Zulip bot API key

Optional routing and authorization:

- `ZULIP_ALLOWED_USERS` — comma-separated Zulip user IDs or emails allowed to DM the bot
- `ZULIP_ALLOW_ALL_USERS=true` — only for trusted/dev environments
- `ZULIP_HOME_CHANNEL` — default delivery target, e.g. `dm:12345` or `stream:general:ops`
- `ZULIP_REQUIRE_MENTION=false` — answer all visible stream messages; default is to answer stream mentions and all DMs

Authorization readiness requires either `ZULIP_ALLOWED_USERS` or explicit
`ZULIP_ALLOW_ALL_USERS=true`; otherwise a default-deny adapter may authenticate
successfully but refuse to respond to users.

## Runtime expectation

A Hermes Zulip adapter should:

1. Authenticate with Zulip Basic auth using `ZULIP_EMAIL:ZULIP_API_KEY`.
2. Register a message event queue with `POST /api/v1/register`.
3. Long-poll `GET /api/v1/events` with the queue ID and last event ID. Register
   only message events when possible (for example, `event_types=["message"]`) to
   avoid unnecessary gateway wakeups.
4. Ignore messages sent by the bot itself.
5. Respond to DMs from allowed users immediately and to stream messages only when mentioned unless
   `ZULIP_REQUIRE_MENTION=false` is explicitly configured.
6. Use default-deny authorization unless `ZULIP_ALLOWED_USERS` is configured or
   `ZULIP_ALLOW_ALL_USERS=true` is explicitly set for a trusted/dev environment.
7. Re-register the queue when Zulip returns an expired or invalid queue ID.
8. Send responses through `POST /api/v1/messages` without logging token values.

## Setup verification

A non-secret verification pass should report:

- whether `ZULIP_SITE_URL`, `ZULIP_EMAIL`, and `ZULIP_API_KEY` are present
- whether `GET /api/v1/users/me` succeeds for the bot
- whether a register/events long-poll loop starts without auth errors
- the configured home channel identifier, if any, without exposing message content

If credentials are missing, report Zulip as `Blocked` with the missing variable
names rather than asking for or printing secret values.
