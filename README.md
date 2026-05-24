# have-config

HappyVertical shared cross-repo configuration for agent-assisted development.

This repo is the umbrella for configuration that ≥2 HappyVertical projects
consume. Today that's Claude Code command adapters and Codex workflow skills. Other
shared config (MCP servers, agent hooks, lint/format/tsconfig bases) will
land here as second consumers appear.

## What lives here

**In scope:**

- Claude Code command adapters and Codex-visible workflow skills (`claude/`, `codex/`)
- Shared lint / format / tsconfig configs as published npm packages
  (`packages/eslint-config`, `packages/prettier-config`,
  `packages/tsconfig-base`)
- MCP server configs consumed by ≥2 projects (planned — `TODO.md`)
- Agent hook scripts (planned — `TODO.md`)
- CLAUDE.md / AGENTS.md template sections that should be identical across
  repos (planned — `TODO.md`)

**Out of scope:**

- Runnable tools — these get their own repos (see
  [`happyvertical/pr-review`](https://github.com/happyvertical/pr-review))
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
├── package.json                     # pnpm workspace root
├── pnpm-workspace.yaml
├── .changeset/                      # versioning + publish manifests
│   └── config.json
├── claude/                          # Claude Code marketplace
│   ├── .claude-plugin/
│   │   └── marketplace.json
│   └── have/                        # the `have` plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── commands/
│           ├── ship.md              # /have:ship adapter
│           └── review-cycle.md      # /have:review-cycle adapter
├── codex/                           # Codex marketplace
│   └── plugins/
│       └── have/                    # the `have` plugin
│           ├── .codex-plugin/
│           │   └── plugin.json
│           ├── commands/
│           │   ├── ship.md          # /have:ship adapter
│           │   └── review-cycle.md  # /have:review-cycle adapter
│           └── skills/              # Codex adapters to ContextForge
│               ├── ship/
│               │   └── SKILL.md     # have:ship
│               └── review-cycle/
│                   └── SKILL.md     # have:review-cycle
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

## Plugin install (agent workflows)

```bash
git clone https://github.com/happyvertical/have-config.git ~/Work/happyvertical/repos/have-config
cd ~/Work/happyvertical/repos/have-config
./install.sh
```

`install.sh` does:

1. Clones [`happyvertical/pr-review`](https://github.com/happyvertical/pr-review)
   if missing, adds `pr-review/bin` to a shell-rc snippet.
2. Registers this repo as a marketplace for both Claude Code and Codex.
3. Installs the `have` plugin in both agents.
4. Optionally symlinks the cached plugin install back to the live repo
   path for in-place editing (`./install.sh --live`).

After install, Claude Code has:

- `/have:ship` — end-to-end shipping pipeline
- `/have:review-cycle` — multi-tool review/fix/retest loop

Codex has equivalent skills:

- `have:ship` — end-to-end shipping pipeline
- `have:review-cycle` — multi-tool review/fix/retest loop

## Editing

ContextForge is the source of truth for workflow bodies:

| Workflow | Prompt | Resource |
|---|---|---|
| Ship | `have-ship` | `have://happyvertical/workflows/ship` |
| Review cycle | `have-review-cycle` | `have://happyvertical/workflows/review-cycle` |

The resources live in the **Happy Vertical** team at
`context.happyvertical.com`. They store the workflow markdown as a base64
payload because ContextForge's default content scanner rejects raw shell-heavy
workflow markdown. The prompt loaders decode that payload and follow it as the
authoritative workflow.

Edits to workflow behavior should happen in ContextForge, not in this repo.
This lets prompt/workflow changes go live without redeploying or reinstalling
the agent plugins.

Edits to the adapter files are picked up:

- **Live mode** (`install.sh --live`): edits are immediately visible to
  running sessions via symlink. May need re-linking after
  `claude plugin update` rewrites the cache.
- **Standard mode**: edits require `claude plugin update have@have-config`
  for Claude, or rerunning `./install.sh` to refresh the Codex plugin cache.

The Claude command files and Codex `skills/` files must remain thin adapters.
Do not put canonical workflow text back into this repo.

## Companion tool

The shipping/review commands generate review prompts via
[`pr-review`](https://github.com/happyvertical/pr-review). pr-review stays
a standalone tool because it has a broader audience (anyone running
pre-PR review with any LLM, regardless of harness). have-config wraps
pr-review in opinionated workflow commands; pr-review itself is unopinionated.

## License

MIT.
