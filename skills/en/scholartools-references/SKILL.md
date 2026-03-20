---
name: scholartools-references
description: scholartools reference management — discover references from external APIs, fetch by DOI/arXiv/ISBN, extract metadata from local PDFs, stage candidates, merge into the library, and perform full CRUD on library records. Use this for any scholartools task involving finding references, adding them to the library, filtering or searching the library, updating or deleting records, or the full staging→merge workflow. If the user is doing anything research-related with scholartools that isn't purely about files or sync, use this skill.
---

## Concepts

- **Staging**: exploration scratchpad. References live here until promoted.
- **Library**: production store. Every record has a citekey assigned at merge.
- **Typical flow**: discover/fetch/extract → `scht staging stage` → review → `scht staging merge`

## Discovery

```sh
scht discover "<query>" [--sources crossref,semantic_scholar,...] [--limit N]
# sources: crossref, semantic_scholar, arxiv, openalex, doaj, google_books

scht fetch <identifier>
# identifier: DOI, arXiv ID, or ISBN

scht extract <file_path>
# Requires ANTHROPIC_API_KEY for LLM fallback on scanned PDFs
```

## Staging

```sh
scht staging stage '<json>' [--file <path>]
echo '<json>' | scht staging stage              # from stdin

scht staging list-staged [--page N]

scht staging delete-staged <citekey>

scht staging merge [--omit key1,key2,...] [--allow-semantic]
# --allow-semantic: also promote records with uid_confidence=="semantic"
```

## Library CRUD

```sh
scht refs add '<json>'
echo '<json>' | scht refs add                   # from stdin

scht refs get <citekey> [--uid <uid>]

scht refs update <citekey> '<json>'
echo '<json>' | scht refs update <citekey>      # from stdin

scht refs rename <old_key> <new_key>

scht refs delete <citekey>

scht refs list [--page N]

scht refs filter [--query "<text>"] [--author "<surname>"] [--year YYYY] \
                 [--type <csl-type>] [--has-file] [--staging] [--page N]
# --type examples: article-journal, book, chapter
# --staging: filter staged records instead of library
```

## Key model fields

**ReferenceRow** (list/filter results): `citekey, title, authors, year, doi, uid, has_file, has_warnings`

**Reference** (full record): `id` (=citekey), `type` (CSL), `title`, `author: [{family, given}]`,
`issued: {date-parts: [[YYYY]]}`, `DOI`, `URL`, `uid`, `uid_confidence` ("authoritative"|"semantic")
