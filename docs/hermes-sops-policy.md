# Hermes SOPS Policy

SOPS protects deployed runtime Secrets. `have-config` defines the standard and
verification checklist; the repository that deploys the workload owns the
encrypted files and rotations.

## Source Of Truth

- Warden is the human/operator credential sharing source.
- SOPS-encrypted Kubernetes Secret files in `iac` are the Flux source for
  cluster runtime credentials.
- `have-config` stores only schemas, templates, expected key names, SOPS profile
  names, and verification instructions.
- Agent contracts may reference Warden paths and SOPS profiles, but must not
  include decrypted values.

## Expected Project Hermes Secret Classes

- runtime Secret: model/provider keys, GitHub token, service credentials,
  Zulip/Vikunja credentials, optional Telegram token, and project cloud access
- web UI Secret: dashboard/API password
- mail account Secret or profile field: per-agent mailbox password
- SOPS age material: only for agents explicitly allowed to decrypt repo-managed
  secrets for their project role

## Verification

Agents and provisioning tools should verify secret readiness by checking names
and key presence only. Reports may include missing variable names, Secret names,
Warden item paths, SOPS profile names, and file paths. Reports must not include
decrypted values or token substrings.

When SOPS policy changes in `have-config`, project Hermes agents should sync
have-config, rerun `check-setup`, and report any runtime Secret or Warden item
drift on their Vikunja project board.
