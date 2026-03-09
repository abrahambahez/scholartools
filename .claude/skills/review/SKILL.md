---
name: review
description: Post-implementation review gate. Checks the last commit against
  spec acceptance criteria. Run after every /task before the next one.
disable-model-invocation: true
---

Spawn the reviewer agent for: $ARGUMENTS

If no argument given, review the most recent commit against the active spec.

The reviewer will return PASS or FAIL with specific evidence.

If PASS: confirm to the user, proceed is safe.
If FAIL: list what must be fixed. Do not run /task [next] until fixes are committed and /review passes.

This gate is mandatory. Do not skip it under time pressure.
