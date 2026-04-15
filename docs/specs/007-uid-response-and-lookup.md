# spec: 007-uid-response-and-lookup

## goal
Expose `uid` in list/filter rows; allow `get_reference` to resolve by uid.

## acceptance criteria

- AC1: `ReferenceRow` includes `uid: str | None`
- AC2: `to_reference_row` populates `uid` from the underlying record
- AC3: `get_reference(uid=<uid>)` returns the matching reference
- AC4: `get_reference(citekey=<key>)` still works unchanged
- AC5: calling `get_reference` with both or neither argument returns an error in `GetResult.error`
- AC6: uid lookup returns the first match (uids are assumed unique by uid.py invariants)

## out of scope
- uid indexing / caching
- multi-uid batch lookup

## tasks

- [ ] T1: add `uid` field to `ReferenceRow` in `models.py`
- [ ] T2: populate `uid` in `to_reference_row` in `list_helpers.py`
- [ ] T3: update `store.get_reference` to accept optional `citekey` and `uid`, scan by uid when provided
- [ ] T4: update public wrapper in `__init__.py` to match new signature
- [ ] T5: unit tests for T3 (both lookup paths, error cases)
