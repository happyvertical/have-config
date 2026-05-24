---
description: "Run the HappyVertical ship workflow."
---

# /have:ship

Prepare the current branch for a ready-to-review pull request using
HappyVertical standards.

1. Inspect the working tree, branch, upstream state, project instructions, and
   documented validation commands.
2. Remove accidental noise, generated clutter, debug instrumentation, and
   unrelated changes from the proposed diff.
3. Confirm docs are updated when behavior, interfaces, config, ops, or
   developer workflow changed.
4. Run the narrowest meaningful validation first, then broader validation before
   opening or updating the PR.
5. Review the final diff for secrets, unrelated files, and avoidable churn.
6. Create or update a ready-for-review PR with a concise description, validation
   results, and any known risks.
7. Watch CI and fix simple failures until the branch is reviewable.

If a Context Forge snapshot or local override replaced this command during
install, follow the generated installed command instead of this org fallback.
