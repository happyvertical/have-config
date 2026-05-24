---
description: "Run the HappyVertical ship workflow from ContextForge."
---

# /have:ship

This local command is only an adapter. The authoritative workflow lives in ContextForge.

Load and follow the Happy Vertical Team prompt:

- Prompt: `have-ship`
- Resource: `have://happyvertical/workflows/ship`

Use ContextForge MCP prompts/resources when available. If prompt invocation is unavailable, read the resource by URI. The resource text contains `encoding: base64` and a `payload_base64:` block; decode that payload as UTF-8 markdown and follow it exactly as the ship workflow.

If ContextForge is unavailable, the prompt is missing, or the resource cannot be read or decoded, stop and report the ContextForge access problem instead of falling back to a stale local workflow.
