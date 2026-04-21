---
name: structural-reading
description: "Use this skill when a user wants an initial structural map of an academic or non-fiction text — understanding its argument, organization, and key concepts without reading it cover to cover. This is the 'first contact' phase: the user might ask 'what is this book about', want to create a @citekey.md note from scratch, fill an empty reference note with a book's structure, understand how chapters connect before deciding to read it fully, or get a quick map from a PDF or EPUB. Invoke when the user says 'structural reading', 'inspectional reading', 'give me a map of this text', 'scan this book', or asks what a text is about before committing to read it. Output: @citekey.md in wiki/refs/ with Context, Structure, and Author's Terms sections. Do not use for close reading, conceptual analysis, defining terms, or updating specific sections of existing notes."
---

# structural-reading

Structural reading is about *information*: knowing what a text is about, how it is organized, and where everything is. It is the first level of reading before going deep.

## prerequisites

Run both checks before doing anything else. Stop if either fails.

```sh
lore refs get <citekey>
# Must return a record. If not found, ask the user to add the reference first.

lore files get <citekey>
# Must return a file path. If not linked, ask the user to attach a source file first.
```

## preparing the source

Convert the source to readable text:

```sh
lore read <citekey>
# Outputs a JSON result with output_path (the extracted text file) and format ("md" or "txt").
# If format is "txt", the file is flat (OCR fallback) — page markers [page N] are present.
# If the command errors, report it to the user and stop.
```

Read the extracted file at `output_path`. For PDFs, check that the main text begins where the user expects — academic PDFs often have front matter that shifts pagination. Show the first page markers and ask whether the offset is correct before proceeding.

For **EPUBs, DOCX, HTML clips**: `lore read` handles them via the same command — no special preparation needed.

For **external notebooks** (NotebookLM or similar): use directed queries instead of converting the file. Locators arrive automatically in those cases.

For **URLs**: do not process directly. Suggest the user convert the URL to a local file first, then attach it with `lore files attach <citekey> <path>`.

If the extracted file is empty or garbled, report `quality_score` and `format` from `lore read` output to the user and stop.

## process

1. Read the table of contents, abstract/introduction, and conclusions from the extracted file.
2. Skim chapters or sections looking for the central thesis and argumentative turning points.
3. Identify 5–7 terms the author uses with a specific or idiosyncratic meaning (the text's technical vocabulary). List only the term name and the locator where it is defined — do not explain them yet; that is analytical reading's work.

## output

Check whether the note already exists:

```sh
lore wiki get <citekey>
```

- If it **does not exist**, show the user the full draft and ask for confirmation before creating:

```sh
lore wiki create <citekey>
# Scaffolds wiki/refs/@citekey.md from library metadata. Errors if citekey not in library.
```

- If it **already exists**, propose improvements to the existing sections before editing.

Then write each section:

```sh
lore wiki update <citekey> Context '<content>'
lore wiki update <citekey> Structure '<content>'
lore wiki update <citekey> "Author's Terms" '<content>'
```

The note structure is:

**Context** — Who the author is, when they wrote this, from what intellectual tradition, what problem they were trying to solve at that historical moment. Not a biography: the context that makes the text readable.

**Structure** — How the text is organized and *why* it is organized that way. Do not copy the table of contents: explain the argumentative function of each part. How do the chapters chain together the central thesis? Where do the key concepts concentrate? Is there a point where the author shifts register or level of abstraction?

**Author's Terms** — The list of 5–7 identified terms with their locators. No definitions yet.

## locators

Use citeproc format:
- Chapter + section: `[chap. 1, sect. "Section Title"]`
- Page only: `[p. 45]`
- Chapter only: `[chap. 3]`

For PDFs, validate that the locator page matches the `[page N]` marker in the extracted file before recording it.

## completion

The structural reading is complete when Context and Structure have real content — not summaries of the table of contents, but interpretation of the text's purpose and argumentative architecture.

If the text has no explicit table of contents (short article, essay), adapt: find the thesis in the introduction and trace how it develops section by section.
