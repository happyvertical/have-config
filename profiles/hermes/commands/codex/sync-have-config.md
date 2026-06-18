---
description: "Refresh have-config and rematerialize this Hermes runtime context."
---

# /sync-have-config

Refresh the local have-config checkout, run the installer for the active Hermes
profile, and report drift without printing secrets.

1. Identify `HERMES_HOME`, defaulting to `~/.hermes`.
2. Identify the have-config checkout from `HERMES_HAVE_CONFIG_DIR`,
   `HAVE_CONFIG_DIR`, or `$HERMES_HOME/have-config`.
3. If the checkout exists, run `git fetch` and fast-forward the configured
   branch. If it cannot fast-forward, report the blocker and do not force-reset.
4. Run `install.sh --skip-dotfiles` with:
   - `HV_AGENT_PROFILE=hermes`
   - `HV_CONFIG_DIR=$HERMES_HOME`
   - `HV_GENERATED_DIR=$HERMES_HOME/generated`
   - `HV_AGENT_LOCK=$HERMES_HOME/agent-lock.json`
   - `HV_INSTALL_REPORT=$HERMES_HOME/install-report.md`
   - existing `HV_AGENT_CONTRACT` or `HV_AGENT_CONTRACT_PATH`
5. Confirm `agent-lock.json`, `install-report.md`, generated commands/skills,
   and any selected `agent-contract.json` and `project-brief.md` exist.
6. Run or summarize `check-setup` next when the sync changed the lockfile,
   contract, project brief, SOPs, or service requirements.

Do not decrypt SOPS files or print token/password values during this command.
