---
name: init
description: First-run project initialization. Generates feature_list.json
  from docs/product.md. Run once per project after filling in product.md.
disable-model-invocation: true
---

Run the initializer agent to generate feature_list.json from docs/product.md.

Before running, confirm:
1. docs/product.md is filled in (not just the template comments)
2. The user has reviewed it and is ready to commit the feature list

Spawn the initializer agent with the project name as context.
After it completes, show the user the generated feature_list.json and ask them to confirm it before the commit lands.
