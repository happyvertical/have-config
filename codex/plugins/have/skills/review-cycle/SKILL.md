---
name: review-cycle
description: Use when the user invokes /review-cycle, /have:review-cycle, have:review-cycle, or asks to run HappyVertical's bounded multi-reviewer review, fix, and retest loop before shipping.
metadata:
  short-description: Run HappyVertical's ContextForge review cycle
---

# Have Review Cycle

This Codex skill is only an adapter. The authoritative workflow lives in ContextForge.

Load and follow the Happy Vertical Team prompt:

- Prompt: `have-review-cycle`
- Resource: `have://happyvertical/workflows/review-cycle`

Use ContextForge MCP prompts/resources when available. If prompt invocation is unavailable, read the resource by URI. The resource text contains `encoding: base64` and a `payload_base64:` block; decode that payload as UTF-8 markdown and follow it exactly as the review-cycle workflow.

If ContextForge is unavailable, the prompt is missing, or the resource cannot be read or decoded, stop and report the ContextForge access problem instead of falling back to a stale local workflow.
