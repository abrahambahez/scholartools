---
name: scholartools-references
description: gestión de referencias en scholartools — descubrir referencias en APIs externas, obtener metadatos por DOI/arXiv/ISBN, extraer metadatos de PDFs locales, poner referencias en staging, fusionarlas con la biblioteca y realizar CRUD completo sobre los registros. Usa esto para cualquier tarea con scholartools que implique encontrar referencias, agregarlas a la biblioteca, filtrar o buscar, actualizar o eliminar registros, o el flujo staging→merge. Si el usuario hace algo con scholartools relacionado con referencias que no sea exclusivamente archivos o sincronización, usa esta skill.
---

## Conceptos

- **Staging**: área de exploración temporal. Las referencias viven aquí hasta que se promueven.
- **Biblioteca**: almacén de producción. Cada registro recibe un citekey asignado al hacer merge.
- **Flujo típico**: discover/fetch/extract → `stage_reference` → revisar → `merge`

## Descubrimiento

```python
discover_references(query: str, sources: list[str] | None = None, limit: int = 10) -> SearchResult
# SearchResult: references: list[Reference], sources_queried: list[str], total_found: int, errors: list[str]
# sources: subconjunto de ["crossref","semantic_scholar","arxiv","openalex","doaj","google_books"]

fetch_reference(identifier: str) -> FetchResult
# identifier: DOI, ID de arXiv o ISBN
# FetchResult: reference: Reference | None, source: str | None, error: str | None

extract_from_file(file_path: str) -> ExtractResult
# ExtractResult: reference: Reference | None, method_used: "pdfplumber"|"llm"|None, confidence: float | None, error: str | None
# Requiere ANTHROPIC_API_KEY para el fallback LLM en PDFs escaneados
```

## Staging

```python
stage_reference(ref: dict, file_path: str | None = None) -> StageResult
# StageResult: citekey: str | None, error: str | None

list_staged(page: int = 1) -> ListStagedResult
# ListStagedResult: references: list[ReferenceRow], total: int, page: int, pages: int

delete_staged(citekey: str) -> DeleteStagedResult
# DeleteStagedResult: deleted: bool, error: str | None

merge(omit: list[str] | None = None, allow_semantic: bool = False) -> MergeResult
# Promueve todos los registros en staging: valida esquema, deduplica, archiva archivos, asigna citekeys
# omit: citekeys en staging que se omiten en esta ejecución
# allow_semantic: también promueve registros con uid_confidence=="semantic" (por defecto: solo "authoritative")
# MergeResult: promoted: list[str], errors: dict[str, str], skipped: list[str]
```

## CRUD de biblioteca

```python
add_reference(ref: dict) -> AddResult
# AddResult: citekey: str | None, error: str | None

get_reference(citekey: str | None = None, uid: str | None = None) -> GetResult
# GetResult: reference: Reference | None, error: str | None

update_reference(citekey: str, fields: dict) -> UpdateResult
# fields: dict parcial de campos de Reference a sobreescribir
# UpdateResult: citekey: str | None, error: str | None

rename_reference(old_key: str, new_key: str) -> RenameResult
# RenameResult: old_key, new_key, error

delete_reference(citekey: str) -> DeleteResult
# DeleteResult: deleted: bool, error: str | None

list_references(page: int = 1) -> ListResult
# ListResult: references: list[ReferenceRow], total: int, page: int, pages: int

filter_references(
    query: str | None = None,    # texto completo en título/resumen
    author: str | None = None,   # coincidencia parcial de apellido
    year: int | None = None,
    ref_type: str | None = None, # tipo CSL: "article-journal", "book", etc.
    has_file: bool | None = None,
    staging: bool = False,       # True para filtrar registros en staging
    page: int = 1,
) -> ListResult
```

## Campos clave de los modelos

**ReferenceRow** (resultados de list/filter): `citekey, title, authors, year, doi, uid, has_file, has_warnings`

**Reference** (registro completo): `id` (=citekey), `type` (CSL), `title`, `author: [{family, given}]`,
`issued: {date-parts: [[YYYY]]}`, `DOI`, `URL`, `uid`, `uid_confidence` ("authoritative"|"semantic")
