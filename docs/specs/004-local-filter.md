# spec 004: local filter and discover rename

## findings

From docs/feats/004-local-filter.md:
- `search_references` (external fan-out) is misnamed — agents confuse it with local search
- No filter/search exists for the local library; agents must page through all records
- Four confirmed use cases: keyword/theme search, field lookup, citekey-less find, token-efficient bulk listing
- Returns `ListResult` (existing model) — no new Pydantic types required
- Local backend: pure Python predicates over in-memory list from `read_all()`
- Cloud backend contract is out of scope; local is the reference implementation

## objective

Rename `search_references` → `discover_references` to clarify that it queries external APIs, not the local library. Add `filter_references` as a fast, local-only search over the library file using up to five optional predicates (text, author, year, type, has_file). Both changes are purely additive or rename-only; no schema changes, no new dependencies.

## acceptance criteria (EARS format)

- when `discover_references(query)` is called, the system must fan out to configured external API sources and return a `SearchResult`, identical in behavior to the previous `search_references`
- when `filter_references()` is called with no arguments, the system must return a paginated `ListResult` equivalent to `list_references(page=1)`
- when `filter_references(query="foo")` is called, the system must return only rows whose title contains "foo" (case-insensitive substring)
- when `filter_references(author="garcia")` is called, the system must return only rows where at least one author's `family` or `literal` field contains "garcia" (case-insensitive substring)
- when `filter_references(year=2021)` is called, the system must return only rows issued in 2021
- when `filter_references(ref_type="book")` is called, the system must return only rows with `type == "book"`
- when `filter_references(has_file=True)` is called, the system must return only rows that have a linked file record
- when `filter_references(has_file=False)` is called, the system must return only rows without a linked file record
- when `filter_references(staging=True)` is called, the system must apply all predicates against the staging store instead of the library store
- when `filter_references(staging=False)` (default) is called, the system must apply predicates against the library store
- when multiple predicates are provided, the system must AND them (all must match)
- when `filter_references` returns results, the system must paginate them with the same `_PAGE_SIZE` and return `total`, `page`, `pages`
- when no records match all predicates, the system must return an empty `ListResult` with `total=0`
- when `search_references` is called (old name), the system must raise `AttributeError` (removed, not aliased)

## tasks

- [ ] task-01: rename `search_references` → `discover_references` in `services/search.py` and `__init__.py`; update all tests referencing the old name (blocks: none)
- [ ] task-02: add `filter_references` service function in `services/store.py` with five optional predicates + `staging: bool`; add sync wrapper in `__init__.py` (blocks: task-01)
- [ ] task-03: write unit tests for `filter_references` covering each predicate, AND combination, `staging=True`, empty result, and no-args full-list case (blocks: task-02)

## ADR required?

no

## risks

- Renaming `search_references` is a breaking change for any external code calling the old name. Mitigated by not providing a compatibility alias — fail loudly.
- `query` only searches `title`. References with no title field will never match a query filter; this is intentional but could surprise agents. Mitigated by clear docstring.
- `filter_references` with no args duplicates `list_references`. Acceptable — agents can use either; consistency is better than restriction.
