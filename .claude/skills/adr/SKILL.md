---
name: adr
description: Scaffold a new Architecture Decision Record in docs/adr/.
  Run when a spec flags an architecture decision is required.
disable-model-invocation: true
---

Create docs/adr/[next-number]-$ARGUMENTS.md with this structure:

# ADR-[NNN]: [title from $ARGUMENTS]

## status
Proposed

## context
[FILL IN: what situation or problem motivated this decision?]
[what constraints, requirements, or forces are in play?]

## decision
[FILL IN: what was decided?]
[be specific: name the approach, library, pattern, or rule]

## alternatives considered
[FILL IN: what other options were evaluated?]
[why were they rejected?]

## consequences
Positive:
- [what this decision enables or improves]

Negative:
- [what this decision costs or constrains]

Neutral:
- [what changes without being clearly good or bad]

---

After writing, link it in docs/tech.md under the ADRs section.
Ask the user to review and change status from "Proposed" to "Accepted" when ready.
