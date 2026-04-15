---
name: research
description: Phase R of RPI. Maps blast radius of a proposed feature or change.
  Spawns the architect agent to read the codebase and produce findings.
disable-model-invocation: true
---

Spawn the architect agent with task: $ARGUMENTS

The architect will:
- Map all files the change will touch
- Identify cross-dependencies
- Flag risks and open decisions
- Write findings to docs/specs/$ARGUMENTS-findings.md

After the architect returns, present the findings to the user.
Ask: "Do these findings look complete? Any missing files or dependencies?"
Do not proceed to /spec until the user confirms the research is complete.
