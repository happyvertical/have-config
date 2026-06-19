# Hermes Agent Contract

Hermes agents should start from a non-secret contract that defines identity,
role, permissions, project management, and runtime expectations. The contract
is the agent-facing standard; deployed Secrets and Kubernetes resources remain
owned by the GitOps repository that runs the agent.

## Runtime Materialization

Set `HV_AGENT_CONTRACT=<slug>` or `HV_AGENT_CONTRACT_PATH=<file>` before running
`install.sh`. The resolver validates the selected contract and writes:

- `agent-contract.json` in the Hermes home
- `project-brief.md` in the Hermes home
- `generated/contracts/<slug>.json`
- contract metadata in `agent-lock.json`

Agents should read `project-brief.md` during setup and when taking over a
project. If it is missing, stale, or does not match the expected project, run
the have-config sync/materialization flow before starting substantial work.

## Contract Rules

- The contract must not contain tokens, passwords, API keys, cookies, recovery
  codes, private keys, or decrypted secret values.
- The contract may name Warden paths, SOPS profiles, Kubernetes Secret names,
  and expected environment variables.
- `have-config` owns the schema, default contracts, SOPs, and generated agent
  context.
- `iac` owns Kubernetes deployments, RBAC, PVCs, NetworkPolicies, ingress,
  SOPS-encrypted runtime Secrets, Flux rollout, and provisioning preflight.
- Local overrides can replace a contract only when the install report makes the
  override visible.

## Project Hermes Defaults

Project Hermes contracts should declare:

- one primary repository and any related repositories the agent needs to
  understand the project
- the assigned IDP/email identity
- display names should match the account name/email local-part, for example
  `magnateos` for `magnateos@happyvertical.com`
- GitHub permission level per repo
- Kubernetes namespaces and service account
- SOPS profiles and Warden paths
- optional `service_access` details for services that need provider-specific
  runtime env names, Warden paths, buckets, or account notes
- Vikunja project, board, expected buckets, labels, and done criteria
- when to use sub-agents or long-running sessions
- Hindsight bank and have-config drift policy

`services` records whether the agent should have a service at all. Use
`service_access` for the operational contract: provider names, credential
source, required runtime env keys, optional helper or alias env keys,
SOPS-backed secret env keys, Warden item paths, and storage buckets. Contracts
must still contain only references and non-secret names, never token values.
