---
name: hermes-board
description: Use when a Hermes agent works the GitHub Projects board #7, picking up its own slug-labelled cards from the Ready lane and driving them through In Progress, Review, and Done.
metadata:
  short-description: Hermes GitHub project board procedure
---

# Hermes GitHub Project Board Procedure

Use this procedure for a Hermes agent that works from the org GitHub Projects board
[#7 "Development Workflow"](https://github.com/orgs/happyvertical/projects/7). Full
reference (lanes, IDs, contract config, boundary vs Vikunja) is in
`docs/hermes-github-project-board.md`. Do not print, store, or comment tokens,
cookies, passwords, or decrypted secret values.

Your slug is your board label. It comes from your contract `board.label` (defaults
to `slug`). You only act on cards labelled with your slug — never another agent's.

## Preconditions

- Your contract has `board.enabled: true`.
- `gh` is authenticated with a token carrying `read:project` + `project` scope.
- Triage (moving a card `New → Ready` and applying your slug label) is upstream and
  not your job here. If nothing is in `Ready` with your label, there is no work.

## Each Cycle

1. **Resolve IDs** for project #7 (id, Status field id, option ids) by name so the
   procedure survives board edits.
2. **Read** the board for your actionable cards: `Status == Ready`, labels contain
   your slug, issue `state == OPEN`.
3. For each card, in order:
   a. **Idempotency** — skip if it already left `Ready`, or already has a
      `hermes-board: claimed by <slug>` marker comment. The lane is the primary
      guard: a claimed card is no longer in `Ready`.
   b. **Claim** — move `Ready → In Progress`, then comment the marker with a
      one-line plan and the next checkpoint.
   c. **Work** — do the task in the card's repo on a branch. Comment at meaningful
      checkpoints. On a blocker: comment `BLOCKED:` with the first concrete blocker
      and smallest next action, add the `status: blocked` label, and leave the card
      in `In Progress`.
   d. **Review** — when the PR is open, move `In Progress → Review` and comment the
      PR link.
   e. **Done** — when the PR merges (or an accepted non-code outcome is documented),
      move `Review → Done` and comment a short summary against the done criteria.

Keep comments short. The board is the source of truth for lane state; do not
duplicate a running log into it.

## Commands

Resolve IDs:

```bash
gh api graphql -f query='
query($org:String!,$num:Int!){ organization(login:$org){ projectV2(number:$num){
  id field(name:"Status"){ ... on ProjectV2SingleSelectField{ id options{ id name } } } }}}' \
  -F org=happyvertical -F num=7
```

Read your actionable cards (substitute your slug for `smrt`):

```bash
gh api graphql --paginate -f query='
query($org:String!,$num:Int!,$endCursor:String){ organization(login:$org){ projectV2(number:$num){
  items(first:100,after:$endCursor){ pageInfo{ hasNextPage endCursor }
    nodes{ id
      content{ ... on Issue{ number url state repository{ nameWithOwner } labels(first:30){ nodes{ name } } } }
      fieldValues(first:20){ nodes{ ... on ProjectV2ItemFieldSingleSelectValue{ name field{ ... on ProjectV2FieldCommon{ name } } } } } } } }}}' \
  -F org=happyvertical -F num=7 \
| jq -c --arg slug "smrt" '
    .data.organization.projectV2.items.nodes[]
    | { item:.id,
        status:( [.fieldValues.nodes[]? | select(.field.name=="Status") | .name][0] // "" ),
        state:(.content.state // ""), repo:(.content.repository.nameWithOwner // ""),
        number:(.content.number // null), url:(.content.url // ""),
        labels:[.content.labels.nodes[]?.name] }
    | select(.status=="Ready" and .state=="OPEN" and (.labels|index($slug)))'
```

Move a card to a lane (`$OPTION_ID` from the resolve step — e.g. `In Progress`,
`Review`, `Done`):

```bash
gh api graphql -f query='
mutation($project:ID!,$item:ID!,$field:ID!,$option:String!){
  updateProjectV2ItemFieldValue(input:{ projectId:$project, itemId:$item, fieldId:$field,
    value:{ singleSelectOptionId:$option } }){ projectV2Item { id } } }' \
  -F project=$PROJECT_ID -F item=$ITEM_ID -F field=$STATUS_FIELD_ID -F option=$OPTION_ID
```

Comment (attaches to the underlying issue):

```bash
gh issue comment "$ISSUE_URL" --body "hermes-board: claimed by smrt — <plan>. Next checkpoint: <when>."
```

## Guardrails

- One agent per card; act only on your own slug label.
- The board is the source of truth. If local notes disagree with the board, trust
  the board.
- Never expose secrets. If a blocker is a missing credential, name the missing
  variable or the Warden/SOPS reference, never the value.
