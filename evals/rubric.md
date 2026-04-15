# eval rubric
# FILL IN: define grading criteria for each feature area.
# The eval-judge skill uses this to grade outputs pass/fail/partial.
#
# HOW TO USE WITH CLAUDE CODE:
# After implementing your first feature, say:
#   "Help me write eval criteria for [feature] in evals/rubric.md.
#    Base it on the acceptance criteria in docs/specs/[feature].md"
#
# Format per criterion:
#   ## [criterion name]
#   weight: 1.0 (hard fail) | 0.5 (soft, degrades score) | 0.25 (nice to have)
#   description: what pass looks like
#   fail signals: concrete examples of what failure looks like

## correctness
weight: 1.0
description: output matches the expected structure and content from the golden example
fail signals: missing required fields, wrong data types, truncated output

## no data corruption
weight: 1.0
description: .bib file content is unchanged except for intended modifications
fail signals: any unintended field change, record deletion, key modification

## error handling
weight: 0.5
description: errors surface as typed exceptions with actionable messages
fail signals: bare Exception, cryptic messages, silent failures

## convention compliance
weight: 0.5
description: code follows patterns in docs/tech.md and docs/structure.md
fail signals: direct bibtexparser calls outside bib/parser.py, hardcoded paths
