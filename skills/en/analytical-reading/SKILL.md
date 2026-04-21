---
name: analytical-reading
description: "Use this skill when the user wants to understand the conceptual substance of a specific text: what the author means by their own terms, how their argument is built and justified, what problems the text resolves vs. leaves open, or whether the argument holds up under scrutiny. Also use when the user wants to fill or update the 'Terms and Arguments' section of an existing @citekey.md, reconstruct an author's argument with locators, or produce critical notes from a source. Trigger phrases include: 'analytical reading', 'close reading', 'what does the author mean by X', 'reconstruct the argument', 'what problems does this text solve', 'give me the terms and arguments', or any request to work through an author's concepts or add analytical entries to a note. This is post-orientation, depth-first work — the user already has a structural map and now wants understanding. Do not use for first contact with a text, structural overviews, or multi-text comparisons."
---

# analytical-reading

Analytical reading is about *understanding*. Starting from the map that structural reading provided, the goal is to reconstruct the author's thinking: what they mean by each term, how they build their arguments, what problems they solve and which ones they leave open.

## prerequisites

Run both checks before doing anything else. Stop if either fails.

```sh
lore wiki section-ready <citekey> Structure
# Exit 0 means the Structure section has content. If exit 1, do the structural reading first.

lore files get <citekey>
# Must return a file path. If not linked, convert and attach the source before continuing.
```

Then get the extracted text:

```sh
lore read <citekey>
# Returns output_path to the readable text file. Use this file throughout the analysis.
```

## workflow

Follow this order strictly — do not move to arguments before fixing the terms, because arguments depend on the exact meaning the author gives to their words.

### 1. X-ray

Return to the structural reading and complete or correct what is missing. Answer:
- What type of text is this (argumentative, descriptive, narrative, technical)?
- What is the central thesis in one sentence?
- What problem is the author trying to solve?
- Was the structure the structural reading described accurate, or does it need adjustment?

If the Structure section needs correction:

```sh
lore wiki update <citekey> Structure '<corrected content>'
```

### 2. Terms

Identify words the author gives a specific or non-standard meaning to. For each term:
- Exact definition in this text (not the standard dictionary definition).
- Locator where it is defined.
- Suggested permanent note title (the most abstract, reusable name for the concept).

Before drafting each entry, search for an existing permanent note:

```sh
lore wiki search '<concept name>'
# Returns absolute paths to matching notes in wiki/notes/. Empty output means no match.
```

If a match exists, reference it with `[[existing note title]]` instead of writing a new synthesis.

### 3. Propositions

The central claims where the author takes a position — not the facts they describe, but what they assert. For each proposition:
- Locator.
- Title of a possible permanent note that captures the claim.

### 4. Arguments

Reconstruct the chain of reasoning that supports each proposition: what premises it uses, how they connect, what evidence is provided, where there are gaps or implicit assumptions.

## output

Write the full Terms and Arguments section:

```sh
lore wiki update <citekey> "Terms and Arguments" '<content>'
```

**Entry format:**
```
- permanent note title: author's content, mentioning the original term if it differs from the title [@citekey, locator]. One-sentence synthesis.
```

If a permanent note already exists in the wiki:
```
- [[existing note title]]: author's content [@citekey, locator]. One-sentence synthesis.
```

If the concept is already covered by an existing note, replace the synthesis with `(see [[note]] for more)`.

**Format conventions:**
- No blank lines between items in the same list; blank lines between distinct sections.
- Each entry title is the most abstract, reusable name for the concept — think of it as a note any future text could cite.
- When using model training knowledge to contextualize (not from the text), mark it with `(AI note)`.

**Final step:** write the summary to frontmatter:

```sh
lore wiki update <citekey> summary '<one paragraph synthesizing thesis and central argument>'
```

Only do this if the `summary` frontmatter field is empty. Do not summarize what structural reading already covers — elevate, deepen, or correct it.

## rules

- If there is a contradiction between `@citekey.md` and the source text, flag it explicitly before editing. The primary source wins.
- Do not infer arguments the author does not make explicit. If something is implicit, mark it as such.
- Depth scales with the text: a 20-page article does not need the same level of decomposition as a 400-page book.
