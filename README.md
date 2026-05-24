# have-config

HappyVertical shared cross-repo configuration for agent-assisted development.

This repo is the umbrella for configuration that ≥2 HappyVertical projects
consume. Today that's organization standards, service registry docs, agent
instruction snippets, profile-specific commands/skills, and shared
lint/format/tsconfig bases. Runtime agent behavior is installed as local files;
Context Forge is consumed as an install-time snapshot by the have-config
resolver.

## What lives here

**In scope:**

- HappyVertical service registry and infrastructure docs (`docs/`, `services/`)
- Organization agent instruction snippets (`agent-doc-snippets/`)
- Profile-specific commands and skills, such as Hermes `check-setup`
  (`profiles/`)
- Agent manifests consumed by the have-config resolver (`hv/manifest.json`,
  `profiles/*/manifest.json`)
- Shared lint / format / tsconfig configs as published npm packages
  (`packages/eslint-config`, `packages/prettier-config`,
  `packages/tsconfig-base`)
- MCP server configs consumed by ≥2 projects (planned — `TODO.md`)
- Agent hook scripts (planned — `TODO.md`)
- CLAUDE.md / AGENTS.md template sections that should be identical across
  repos

**Out of scope:**

- Runnable tools — these get their own repos (see
  [`happyvertical/pr-review`](https://github.com/happyvertical/pr-review))
- Generic personal workflows such as `ship` and `review-cycle`; those live in
  dotfiles and are consumed here as the lowest-priority baseline
- Per-repo specifics (e.g. anytown's
  `apps/dashboard/docs/ad-network.md`)
- Anything used by exactly one project
- Project source code

The scope rule exists to prevent kitchen-sink rot. If you're tempted to
add something used by only one repo, put it in that repo.

## Layout

```
have-config/
├── README.md
├── LICENSE
├── install.sh                       # one-line setup (agents)
├── TODO.md                          # planned additions, with consumer count
├── hv/
│   └── manifest.json                # organization source manifest
├── profiles/
│   └── hermes/
│       ├── manifest.json            # Hermes-only commands and skills
│       ├── commands/
│       │   ├── claude/check-setup.md
│       │   └── codex/check-setup.md
│       └── skills/check-setup/
│           └── SKILL.md
├── agent-doc-snippets/              # cumulative AGENTS / CLAUDE sections
├── docs/
│   ├── agent-playbook.md            # what agents use each service for
│   └── infrastructure.md            # HappyVertical service map
├── services/
│   └── services.json                # machine-readable service registry
├── package.json                     # pnpm workspace root
├── pnpm-workspace.yaml
├── .changeset/                      # versioning + publish manifests
│   └── config.json
└── packages/                        # published npm configs
    ├── eslint-config/               # @happyvertical/eslint-config
    ├── prettier-config/             # @happyvertical/prettier-config
    └── tsconfig-base/               # @happyvertical/tsconfig-base
```

## Published packages

The `@happyvertical/*` scope publishes to **GitHub Packages**, not
npmjs.org (matching the org standard used by smrt, sdk, etc.). To install
from a consuming repo, you need an `.npmrc` that routes the scope to GH
Packages and provides auth:

```ini
# .npmrc in the consuming repo (and/or ~/.npmrc for local dev)
@happyvertical:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${NODE_AUTH_TOKEN}
```

Set `NODE_AUTH_TOKEN` to:
- **In CI**: `${{ secrets.GITHUB_TOKEN }}` (or a token from the
  `HAVE_RELEASE` GitHub App for cross-repo installs)
- **Locally**: a personal access token with `read:packages` scope

Then install:

```bash
pnpm add -D \
  @happyvertical/eslint-config \
  @happyvertical/prettier-config \
  @happyvertical/tsconfig-base \
  eslint prettier typescript
```

See each package's README for usage details:

| Package | Purpose |
|---|---|
| [`@happyvertical/eslint-config`](packages/eslint-config) | Type-aware ESLint flat config with optional Svelte 5 preset |
| [`@happyvertical/prettier-config`](packages/prettier-config) | Org-wide Prettier rules |
| [`@happyvertical/tsconfig-base`](packages/tsconfig-base) | Strict TypeScript baselines (app, lib, test variants) |

Configs are versioned via Changesets and published on merge to `main`.

## Agent Bootstrap

```bash
git clone https://github.com/happyvertical/have-config.git ~/Work/happyvertical/repos/have-config
cd ~/Work/happyvertical/repos/have-config
./install.sh
```

`install.sh` does:

1. Clones or updates the configured dotfiles repo and runs its `install.sh`
   unless `--skip-dotfiles` or `HAVE_CONFIG_SKIP_DOTFILES=1` is set.
2. Clones [`happyvertical/pr-review`](https://github.com/happyvertical/pr-review)
   if missing, adds `pr-review/bin` to the current install PATH.
3. Resolves dotfiles, have-config, active profile, Context Forge snapshot, and
   local overrides into local generated agent files.

By default, have-config caches dotfiles under `~/.config/hv/dotfiles` for
workstations and `~/.hermes/dotfiles` for Hermes agents. Set `DOTFILES_DIR` to
use a personal checkout instead.

Dotfiles contributes generic baseline workflows such as `ship` and
`review-cycle` through its `agent/manifest.json`. have-config contributes
HappyVertical organization standards, service playbooks, service registry data,
and profile-specific additions.

Hermes agents additionally get local generated commands/skills:

- `/check-setup` / `check-setup` — verifies agent access to HappyVertical
  services

## Agent resolution model

The have-config installer composes agent behavior in this order:

1. dotfiles baseline workflows
2. have-config organization standard
3. active profile defaults, such as Hermes
4. Context Forge install-time snapshot
5. machine-local overrides

For command and skill conflicts, later layers win. For AGENTS and CLAUDE
behavior, sections are cumulative and assembled in layer order.

Context Forge remains the dynamic organization policy source, but it is not a
runtime dependency for normal agent behavior. Export it into
`HV_CONTEXTFORGE_SNAPSHOT_DIR` and rerun `./install.sh` to materialize new
local command/skill files and update `agent-lock.json`.

Hermes profile detection uses explicit environment first:

- `HV_AGENT_PROFILE=hermes` or `AGENT_PROFILE=hermes`
- `HERMES`, `HERMES_AGENT`, `HERMES_AGENT_ID`, or `HERMES_HOME`
- `~/.hermes/profile.json` or `~/.hermes/.profile-hermes`

When Hermes is active, generated files and reports default under `~/.hermes`.
Local overrides default to `~/.config/hv/overrides` for workstations and
`~/.hermes/overrides` for Hermes agents. The installer creates templates there
but never deletes or rewrites existing override files. On first install,
existing unmanaged global `AGENTS.md` / `CLAUDE.md` files are adopted into that
override directory before generated docs are linked.

Edits to dotfiles, have-config, profile files, Context Forge snapshots, or
local overrides are picked up by rerunning `./install.sh`.

## Companion tool

The baseline shipping/review workflows can generate review prompts via
[`pr-review`](https://github.com/happyvertical/pr-review). pr-review stays
a standalone tool because it has a broader audience (anyone running
pre-PR review with any LLM, regardless of harness). have-config ensures the
tool is available while organization standards remain in this repo.

## License

MIT.
