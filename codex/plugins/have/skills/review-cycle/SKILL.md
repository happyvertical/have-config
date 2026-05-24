---
name: review-cycle
description: Use when the user invokes /review-cycle, /have:review-cycle, have:review-cycle, or asks to run HappyVertical's bounded multi-reviewer review, fix, and retest loop before shipping.
metadata:
  short-description: Run HappyVertical's review cycle
---

# Have Review Cycle

Run a bounded review, fix, and retest loop before shipping.

1. Identify the target branch, base branch, changed files, CI state, and project
   validation commands.
2. Review the diff from multiple angles: correctness, maintainability, security,
   product behavior, test coverage, and docs.
3. Convert actionable findings into a short fix list. Ignore preference-only
   churn unless it blocks maintainability or consistency.
4. Implement the fixes, preserving unrelated user changes.
5. Re-run the relevant validation and update docs if behavior or workflow
   changed.
6. Repeat the review once after fixes. Stop when no material findings remain or
   a blocker requires human input.
7. Report what changed, what was validated, and any residual risk.

If a Context Forge snapshot or local override replaced this skill during
install, follow the generated installed skill instead of this org fallback.
