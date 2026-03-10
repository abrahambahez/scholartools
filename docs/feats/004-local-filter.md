# feat 004: local filter and discover rename

version: 0.1
status: current

## problem

Agents operating on the local library have no way to search or filter it. Every use case that involves "find X in my library" today requires either iterating all paginated results or knowing the citekey in advance. There is also a naming ambiguity: `search_references` sounds like it searches the local library, but it fans out to external APIs. This confuses agents.

## two distinct operations

**Discover** (external): query Crossref, Semantic Scholar, arXiv, etc. Returns candidate `Reference` objects not yet in the library.

**Filter** (local): scan the library file and return matching rows. Pure in-process operation. No network.

Renaming `search_references` → `discover_references` makes the boundary explicit in the public API.

## filter design

Four orthogonal predicates, all optional, all ANDed:

| param | matches on | match type |
|---|---|---|
| `query` | `title` | case-insensitive substring |
| `author` | any `author[].family` or `author[].literal` | case-insensitive substring |
| `year` | `issued.date_parts[0][0]` | exact int |
| `ref_type` | `type` | exact string (CSL type) |
| `has_file` | presence of `_file` record | bool |

No params → returns full library (equivalent to `list_references`).

Returns `ListResult` (paginated `ReferenceRow`). No new models.

## why not projection / include / exclude

Projection adds a variable-schema result that cannot be expressed in the existing `ListResult` / `ReferenceRow` types without a union or `dict` return. The token-saving use case is already largely covered: `ListResult` returns slim `ReferenceRow` rows; agents that need full fields call `get_reference` per citekey. Projection is deferred to a future feature or handled externally with jq.

## performance

The local adapter loads the entire library into memory on every call (`read_all`). Filter is O(n) Python over the loaded list. For any realistic library size (< 50k records), this is instantaneous. No indexing required.

## cloud backend contract

`filter_references` in `__init__.py` calls a service function that receives a `FilterQuery` typed dict through `LibraryCtx`. Each backend adapter translates it to its own query syntax (MongoDB `$regex`, DynamoDB scan + filter, etc.). The local adapter implements it as pure Python predicates.

This is out of scope for this feature — cloud backends don't exist yet. The service layer is written so the local implementation is the authoritative reference for what cloud adapters must replicate.

## what changes

1. `services/search.py` → rename function `search_references` to `discover_references`
2. `__init__.py` → rename public function `search_references` → `discover_references`
3. `services/store.py` → add `filter_references(query, author, year, ref_type, has_file, page, ctx)`
4. `__init__.py` → add `filter_references(...)` sync wrapper
5. `models.py` → no changes (reuse `ListResult`)

## non-goals

- Full-text search across abstract, keywords, or notes (→ semantic-search feature)
- Field projection / include / exclude (→ future, or jq)
- Publisher / ISSN / DOI filter (viable but not in confirmed use cases yet)
- Staged library filter (trivial extension once local filter works; deferred)
