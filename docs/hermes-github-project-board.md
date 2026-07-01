# Hermes GitHub Project Board SOP

This is the standard operating procedure for Hermes agents that work from the
HappyVertical GitHub Projects board
[#7 "Development Workflow"](https://github.com/orgs/happyvertical/projects/7). The
board is the single org-wide overview of work in flight across repositories. On
each Hermes-managed cycle, an agent picks up issues that are (a) in an actionable
lane and (b) labelled with its own Hermes name, then drives those cards through
the board lanes, commenting as it works.

Scheduling is owned by the Hermes runtime. This document defines *what* an agent
does each cycle, not *when* it runs. The executable form of this procedure is the
`hermes-board` skill (`profiles/hermes/skills/hermes-board`).

## Operating Model

- Board #7 is the canonical, user-visible overview. Each card is a GitHub issue or
  pull request from a member repository.
- Routing is per agent: a card "belongs to" the Hermes agent whose slug matches a
  label on the card. There is no manager/worker split — each agent works its own
  labelled cards directly.
- An agent only acts on cards in an **actionable lane** (default `Ready`) that
  carry its slug label. Everything else is ignored.
- The agent moves its own cards forward and comments at each transition. The
  board is the source of truth for lane state.
- Never print, store, or comment secrets, tokens, cookies, passwords, or
  decrypted values (same rule as `hermes-ops`).

## Board Model

Board #7 uses a single-select `Status` field with these lanes, in order:

- `New` — just landed on the board, untriaged.
- `Backlog` — accepted but not scheduled.
- `Planning` — being scoped / needs a plan.
- `Ready` — scoped and ready for pickup. **Actionable lane.**
- `In Progress` — an agent has claimed it and is working.
- `Review` — a PR is open and awaiting human review.
- `Done` — merged or the accepted non-code outcome is documented.

The board has no `Blocked` lane. Represent a blocker with a comment plus the
`status: blocked` label, and leave the card in `In Progress`.

## Routing Labels

The routing label is the agent's **bare Hermes slug**, with no prefix:

`happyvertical`, `anytown`, `ergot`, `smrt`, `magnateos`, `willgriffin`

A card labelled `smrt` in the `Ready` lane is owned by the `smrt` Hermes. Labels
are per-repository in GitHub, so each slug label must exist and be applied in the
repository the issue lives in; board #7 then surfaces it. Creating the slug labels
across member repositories and moving cards `New → Ready` with a slug label is
**triage**, which is upstream of this SOP (a human or a future `agent: triage`
step). This procedure only handles pickup and execution.

## The Per-Cycle Procedure

For the running agent's own slug (from its contract `board.label`, which defaults
to `slug`):

1. **Read the board.** List board #7 items and keep only those where
   `Status` is an actionable lane (`Ready`), the card carries the agent's slug
   label, and the underlying issue is `OPEN`.
2. **Check idempotency.** Skip a card already past `Ready` (`In Progress` /
   `Review`) or already carrying a `hermes-board: claimed by <slug>` marker
   comment. The lane itself is the primary guard — once claimed, a card leaves
   `Ready` and is not re-picked.
3. **Claim.** Move `Status` `Ready → In Progress` and post a marker comment:
   the slug, a one-line plan, and the expected next checkpoint.
4. **Work.** Do the task in the card's repository (branch → PR), commenting at
   meaningful checkpoints. On a blocker, comment `BLOCKED:` with the first
   concrete blocker and the smallest next action, and add the `status: blocked`
   label. Leave the card in `In Progress`.
5. **Open a PR.** Move `Status → Review` and comment the PR link.
6. **Finish.** When the PR merges (or an accepted non-code outcome is documented),
   move `Status → Done` and comment a short summary against the done criteria.

Optionally, an agent may reconcile its own stalled `In Progress` cards (its marker
comment present, no open PR) by resuming or re-blocking them.

### Done Criteria (default)

- The relevant PR is merged or the accepted non-code outcome is documented.
- Required tests, typechecks, lint, or package checks have passed, or the card
  explains why they were skipped.
- Board #7 has final lane state, PR/deploy links, and any follow-up work noted.

## Reference Commands

All commands use the `gh` CLI with a token carrying `read:project` + `project`
scope (see the SOPS/Warden policy for how that token is sourced). Resolve IDs by
name at runtime so the procedure survives board edits.

**Resolve project + Status field/option IDs:**

```bash
gh api graphql -f query='
query($org:String!,$num:Int!){
  organization(login:$org){ projectV2(number:$num){
    id
    field(name:"Status"){ ... on ProjectV2SingleSelectField { id options { id name } } }
  }}
}' -F org=happyvertical -F num=7
```

**Read actionable cards for a slug** (filter client-side; paginate for the full
board):

```bash
gh api graphql --paginate -f query='
query($org:String!,$num:Int!,$endCursor:String){
  organization(login:$org){ projectV2(number:$num){
    items(first:100,after:$endCursor){
      pageInfo{ hasNextPage endCursor }
      nodes{
        id
        content{
          ... on Issue{ number url state repository{ nameWithOwner }
                        labels(first:30){ nodes{ name } } }
        }
        fieldValues(first:20){ nodes{
          ... on ProjectV2ItemFieldSingleSelectValue{ name field{ ... on ProjectV2FieldCommon{ name } } }
        }}
      }
    }
  }}
}' -F org=happyvertical -F num=7 \
| jq -c --arg slug "smrt" '
    .data.organization.projectV2.items.nodes[]
    | { item:.id,
        status:( [.fieldValues.nodes[]? | select(.field.name=="Status") | .name][0] // "" ),
        state:(.content.state // ""),
        repo:(.content.repository.nameWithOwner // ""),
        number:(.content.number // null),
        url:(.content.url // ""),
        labels:[.content.labels.nodes[]?.name] }
    | select(.status=="Ready" and .state=="OPEN" and (.labels|index($slug)))'
```

The `item` field is the **ProjectV2Item id** required by the move mutation; `url`
is the issue URL used for comments.

**Move a card to a lane:**

```bash
gh api graphql -f query='
mutation($project:ID!,$item:ID!,$field:ID!,$option:String!){
  updateProjectV2ItemFieldValue(input:{
    projectId:$project, itemId:$item, fieldId:$field,
    value:{ singleSelectOptionId:$option }
  }){ projectV2Item { id } }
}' -F project=$PROJECT_ID -F item=$ITEM_ID -F field=$STATUS_FIELD_ID -F option=$OPTION_ID
```

**Comment on the card** (comments attach to the underlying issue):

```bash
gh issue comment "$ISSUE_URL" --body "hermes-board: claimed by smrt — <plan>. Next checkpoint: <when>."
```

## Contract Configuration

Board participation is declared per agent in
`profiles/hermes/contracts/<slug>.json`:

```json
"board": {
  "enabled": true,
  "project": "happyvertical/7",
  "label": "smrt"
}
```

`label` defaults to the contract `slug`. The shared board mechanics (lanes,
actionable lane, lane flow, done criteria) live in this SOP and the `hermes-board`
skill; a contract may override them via the optional `actionable_lanes`,
`lane_flow`, and `done_criteria` fields defined in the contract schema.

## Relationship to Vikunja Dev Team Mode

GitHub Projects board #7 and Vikunja Dev Team Mode
(`docs/hermes-dev-team-mode.md`) are complementary surfaces:

- **Board #7** is the GitHub-native, org-wide overview. Use it for work that lives
  as GitHub issues/PRs and should be visible across the whole organisation. Each
  agent drives its own labelled cards.
- **Vikunja Dev Team Mode** is the local manager/worker execution model, with a
  per-manager internal project and a live integration worktree.

An agent should treat one surface as canonical for a given piece of work and
mirror status rather than split it. When a card on board #7 is executed via a
local dev-team worker, keep board #7's lane as the user-visible truth.

## Blocking and Secret Handling

- Move behaviour on a blocker: comment `BLOCKED:` with the first concrete blocker
  and the smallest next action, add `status: blocked`, keep the card in
  `In Progress`.
- Never include secrets, tokens, cookies, passwords, or decrypted values in
  comments, logs, or PRs. If a blocker is a missing credential, name the missing
  variable or Warden/SOPS reference, never the value.
