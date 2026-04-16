# 005 — Configurable Citekey Generation

version: 0.1
status: current

## Problem

Citekey format is hardcoded. Researchers have existing conventions — in Zotero, JabRef, or their own vaults — that differ from the scholartools default. There is no way to adapt generation without touching source code.

## Goal

Let researchers configure how citekeys are composed and how collisions are resolved, via `config.json`. The vault convention (`autor2024`, `autor1_autor22024`, `autor_etal2024`) must remain expressible as the default.

## Design

Citekey construction is split into two independent phases:

**Phase 1 — Composition**: builds the base key from reference metadata.
**Phase 2 — Disambiguation**: resolves collisions by appending a suffix.

These phases are configured separately because they answer different questions: composition is about identity, disambiguation is about uniqueness.

### Config shape

```json
"citekey": {
  "pattern": "{author[2]}{year}",
  "separator": "_",
  "etal": "_etal",
  "disambiguation_suffix": "letters"
}
```

### Pattern tokens

The `pattern` field is a template composed of flat tokens:

| Token | Description |
|---|---|
| `{author[N]}` | Author family names, up to N authors before etal kicks in |
| `{year}` | 4-digit publication year |
| `{title[N]}` | First N significant words from title (future, not in this feat) |

Tokens are positional and order matters. No nesting, no embedded formatting — those are separate fields.

### Formatting fields

| Field | Constraint | Default | Purpose |
|---|---|---|---|
| `separator` | `^[a-z0-9_-]{1,3}$` | `_` | Joins author names within `{author[N]}` |
| `etal` | `^[a-z0-9_-]{1,8}$` | `_etal` | Replaces excess authors when count > N |

Character constraints are export-safe: valid in BibTeX keys, file names, and common library formats.

### Disambiguation suffix

| Value | Behavior |
|---|---|
| `"letters"` | Appends `a`, `b`, ... `z`, `aa`, `ab`, ... on collision |
| `"title[1-9]"` | Appends N significant words from title on collision |

This is a closed enum. The current collision resolution logic maps directly to `"letters"`.

### Defaults reproduce current behavior

```json
"citekey": {
  "pattern": "{author[2]}{year}",
  "separator": "_",
  "etal": "_etal",
  "disambiguation_suffix": "letters"
}
```

Produces: `smith2020`, `star_griesemer1989`, `anand_etal2018`, `smith2020a`.

## Scope

- Configurable composition and disambiguation as described above
- Validation at config load time (bad pattern or invalid field values raise early)
- `{title[N]}` token in pattern is **out of scope** for this feat (disambiguation via title words is in scope)
- Per-reference citekey override is out of scope
- Existing `ref{uuid6}` fallback for missing author/year is unchanged

## Impact on existing code

| Module | Change |
|---|---|
| `models.py` | Add `CitekeySettings` model, embed in `Settings` |
| `config.py` | `_REQUIRED_KEYS` unchanged (citekey block is optional with defaults) |
| `citekeys.py` | `generate(ref, settings)` replaces hardcoded logic; `resolve_collision` dispatches on `disambiguation_suffix` |
| `citekeys.py` tests | Extend with pattern/config variants; existing cases become default-config tests |

Net code change is roughly neutral — hardcoded logic (~30 lines) is replaced by a small token evaluator of similar size, plus config model and validation.
