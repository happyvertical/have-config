---
description: "Run the HappyVertical review-cycle workflow from ContextForge."
---

# /have:review-cycle

This local command is only an adapter. The authoritative workflow lives in ContextForge.

Load and follow the Happy Vertical Team prompt:

- Prompt: `have-review-cycle`
- Resource: `have://happyvertical/workflows/review-cycle`

Use ContextForge MCP prompts/resources when available. If prompt invocation is unavailable, read the resource by URI. The resource text contains `encoding: base64` and a `payload_base64:` block; decode that payload as UTF-8 markdown and follow it exactly as the review-cycle workflow.

If ContextForge is unavailable, the prompt is missing, or the resource cannot be read or decoded, stop and report the ContextForge access problem instead of falling back to a stale local workflow.
