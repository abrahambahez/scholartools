---
name: spec
description: Phase P of RPI. Produces the spec file for a feature.
  Reads docs/feats/, agent research, writes docs/specs/[NNN-feature].md.
  Both feats and specs are numbered like ADRs — always pass the full
  numbered name (e.g. /spec 003-mcp-server).
disable-model-invocation: true
---

Invoke the spec-writer skill for: $ARGUMENTS

Context for spec-writer:
- docs/feats/$ARGUMENTS.md (your canonical design thinking)
- docs/specs/$ARGUMENTS-findings.md (agent research, if it exists)
- docs/product.md (project scope)
- docs/tech.md (constraints)

If docs/feats/$ARGUMENTS.md does not exist, ask the user:
  "I don't see docs/feats/$ARGUMENTS.md. Have you written the feature design yet?
   Create docs/feats/NNN-$ARGUMENTS.md (next number after existing feats), then run /design NNN-$ARGUMENTS."

After the spec is written, present it to the user.
Ask for explicit approval before any /task commands run.
Do not proceed without "approved" or equivalent confirmation.
