---
name: eval
description: Quality gate. Runs test suite and LLM judge against golden examples.
  Run after every feature is complete and before any production deploy.
disable-model-invocation: true
---

Invoke the eval-judge skill for: $ARGUMENTS

The judge will:
1. Run the full test suite
2. Grade outputs against evals/rubric.md
3. Write results to evals/results/
4. Commit the results

Surface the score and any failed criteria to the user.
If overall verdict is FAIL: do not proceed to production deploy.
