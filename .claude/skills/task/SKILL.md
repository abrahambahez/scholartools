---
name: task
description: Phase I of RPI. Implements one task from the current spec.
  Spawns a developer subagent with scoped context. Commits on completion.
disable-model-invocation: true
---

Implement task $ARGUMENTS.

Before spawning the developer agent, confirm:
1. The relevant spec file exists in docs/specs/
2. The task ID exists in the spec's task list
3. All blocking tasks are marked complete

Spawn the developer agent with task ID: $ARGUMENTS

After the agent returns:
- If done: run /review automatically before marking the task complete
- If blocked: surface the blocker to the user, do not proceed

One task = one subagent = one commit. Do not batch tasks.
