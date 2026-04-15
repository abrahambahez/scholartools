# spec: [feature name]
# Copy this file to docs/specs/[feature-name].md
# Read from docs/feats/[feature-name].md before writing this spec

## findings
[populated from docs/feats/[feature-name].md and agent research]
[or: "pending /research"]

## objective
[one paragraph: what changes, why it matters, what success looks like for the user]

## acceptance criteria (EARS format)
# "when [condition], the system must [behavior]"
# each criterion should be independently testable
- when [condition], the system must [behavior]
- when [condition], the system must [behavior]

## tasks
# each task = one atomic commit = one developer subagent context
# list blockers explicitly — the agent will enforce the dependency order
- [ ] task-01: [description] (blocks: none)
- [ ] task-02: [description] (blocks: task-01)

## ADR required?
[yes — run /adr [decision-name] before /task | no]

## risks
[what could go wrong, what's uncertain, what could affect adjacent features]
