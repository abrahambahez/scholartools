# feat 004: local filter

version: 0.2
status: current

## problem

Agents operating on the local library had no way to search or filter it without iterating all paginated results or knowing the citekey in advance.

An earlier version of this feat also renamed `search_references` → `discover_references` to clarify the external-API/local-filter boundary. That rename is now moot: `discover_references` and the entire external search stack were removed in v0.13.0 (spec 027) as part of enforcing the portability invariant. External discovery belongs in a future `loretools-search` plugin.

## filter design

`filter_references` scans the local library and returns matching rows. It is a pure in-process operation with no network calls.

Four orthogonal predicates, all optional, all ANDed:

| param | matches on | match type |
|---|---|---|
| `query` | `title` | case-insensitive substring |
| `author` | any `author[].family` or `author[].literal` | case-insensitive substring |
| `year` | `issued.date_parts[0][0]` | exact int |
| `ref_type` | `type` | exact string (CSL type) |
| `has_file` | presence of `_file` record | bool |

No params → returns full library (equivalent to `list_references`).

`filter_references(staging=True)` routes all predicates to `ctx.staging_read_all` instead of `ctx.read_all`, returning staged candidates.

Returns `ListResult` (paginated `ReferenceRow`). No new models.

## performance

The local adapter loads the entire library into memory on every call (`read_all`). Filter is O(n) Python over the loaded list. For any realistic library size (< 50k records), this is instantaneous. No indexing required.

## proposed: external discovery

> **status: proposed** — External discovery (Crossref, Semantic Scholar, arXiv, OpenAlex, DOAJ, Google Books) was removed from core in v0.13.0. It will be re-introduced as a `loretools-search` plugin that imports `httpx` and does not ship with the core package.

The planned public function was:

```python
discover_references(query: str, sources: list[str] | None = None, limit: int = 10) -> SearchResult
```

And by identifier:

```python
fetch_reference(identifier: str) -> FetchResult
```

`identifier` would accept DOI, arXiv ID, ISBN, ISSN — the service auto-detects type. See `docs/feats/001-core-library.md` for the original `SearchResult` and `FetchResult` model shapes.

## non-goals (current)

- Full-text search across abstract, keywords, or notes (semantic search)
- Field projection / include / exclude
- Publisher / ISSN / DOI filter (viable but not in confirmed use cases)
