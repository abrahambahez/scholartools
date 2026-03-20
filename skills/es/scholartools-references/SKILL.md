---
name: scholartools-references
description: gestión de referencias en scholartools — descubrir referencias en APIs externas, obtener metadatos por DOI/arXiv/ISBN, extraer metadatos de PDFs locales, poner referencias en staging, fusionarlas con la biblioteca y realizar CRUD completo sobre los registros. Usa esto para cualquier tarea con scholartools que implique encontrar referencias, agregarlas a la biblioteca, filtrar o buscar, actualizar o eliminar registros, o el flujo staging→merge. Si el usuario hace algo con scholartools relacionado con referencias que no sea exclusivamente archivos o sincronización, usa esta skill.
---

## Conceptos

- **Staging**: área de exploración temporal. Las referencias viven aquí hasta que se promueven.
- **Biblioteca**: almacén de producción. Cada registro recibe un citekey asignado al hacer merge.
- **Flujo típico**: discover/fetch/extract → `scht staging stage` → revisar → `scht staging merge`

## Descubrimiento

```sh
scht discover "<consulta>" [--sources crossref,semantic_scholar,...] [--limit N]
# sources: crossref, semantic_scholar, arxiv, openalex, doaj, google_books

scht fetch <identificador>
# identificador: DOI, ID de arXiv o ISBN

scht extract <ruta_archivo>
# Requiere ANTHROPIC_API_KEY para el fallback LLM en PDFs escaneados
```

## Staging

```sh
scht staging stage '<json>' [--file <ruta>]
echo '<json>' | scht staging stage              # desde stdin

scht staging list-staged [--page N]

scht staging delete-staged <citekey>

scht staging merge [--omit clave1,clave2,...] [--allow-semantic]
# --allow-semantic: también promueve registros con uid_confidence=="semantic"
```

## CRUD de biblioteca

```sh
scht refs add '<json>'
echo '<json>' | scht refs add                   # desde stdin

scht refs get <citekey> [--uid <uid>]

scht refs update <citekey> '<json>'
echo '<json>' | scht refs update <citekey>      # desde stdin

scht refs rename <clave_antigua> <clave_nueva>

scht refs delete <citekey>

scht refs list [--page N]

scht refs filter [--query "<texto>"] [--author "<apellido>"] [--year AAAA] \
                 [--type <tipo-csl>] [--has-file] [--staging] [--page N]
# --type ejemplos: article-journal, book, chapter
# --staging: filtra registros en staging en lugar de la biblioteca
```

## Campos clave de los modelos

**ReferenceRow** (resultados de list/filter): `citekey, title, authors, year, doi, uid, has_file, has_warnings`

**Reference** (registro completo): `id` (=citekey), `type` (CSL), `title`, `author: [{family, given}]`,
`issued: {date-parts: [[AAAA]]}`, `DOI`, `URL`, `uid`, `uid_confidence` ("authoritative"|"semantic")
