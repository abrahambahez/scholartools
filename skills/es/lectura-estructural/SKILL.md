---
name: lectura-estructural
description: "Use this skill when a user wants an initial structural map of an academic text — understanding its argument, organization, and key concepts without reading it cover to cover. This is the 'first contact' phase: the user might say 'inspecciona', 'lectura estructural', 'lectura inspeccional', ask 'de qué va este texto', want to create a @citekey.md note from scratch, fill an empty reference note with a book's structure, understand how chapters connect before deciding to read it fully, or get a quick map from a PDF or EPUB. Invoke also when the user says 'dame un mapa del texto', 'llénala con la estructura', or asks what a text is about before committing to read it. Output: @citekey.md in wiki/refs/ with Context, Structure, and Author's Terms sections. Do not use for close reading, conceptual analysis, term definitions, or updating specific sections of existing notes."
---

# lectura-estructural

La lectura estructural es para la *información*: saber de qué trata un texto, cómo está organizado y dónde está cada cosa. Es el primer nivel de lectura antes de entrar en profundidad.

## prerrequisitos

Ejecutar ambas verificaciones antes de cualquier otra cosa. Detener si alguna falla.

```sh
lore refs get <citekey>
# Debe devolver un registro. Si no se encuentra, pedir al usuario que agregue la referencia primero.

lore files get <citekey>
# Debe devolver una ruta de archivo. Si no hay archivo vinculado, pedir al usuario que adjunte una fuente primero.
```

## preparar la fuente

Convertir la fuente a texto legible:

```sh
lore read <citekey>
# Devuelve un resultado JSON con output_path (el archivo de texto extraído) y format ("md" o "txt").
# Si format es "txt", el archivo es plano (respaldo OCR) — los marcadores [page N] están presentes.
# Si el comando falla, reportarlo al usuario y detener.
```

Leer el archivo extraído en `output_path`. Para PDFs, verificar que el texto principal comienza donde el usuario espera — los PDFs académicos suelen tener páginas de portada que desplazan la numeración. Mostrar los primeros marcadores de página y preguntar si el offset es correcto antes de continuar.

Para **EPUBs, DOCX, clips HTML**: `lore read` los gestiona con el mismo comando — no se necesita preparación especial.

Para **notebooks externos** (NotebookLM u otros): usar consultas dirigidas al notebook en lugar de convertir el archivo. Los locators llegan automáticamente en esos casos.

Para **URLs**: no procesar directamente. Sugerir al usuario que convierta la URL a un archivo local y luego lo adjunte con `lore files attach <citekey> <path>`.

Si el archivo extraído está vacío o ilegible, reportar `quality_score` y `format` del resultado de `lore read` al usuario y detener.

## proceso

1. Leer el índice, abstract/introducción, y conclusiones del archivo extraído.
2. Hojear capítulos o secciones buscando la tesis central y los puntos de inflexión argumentativa.
3. Identificar 5–7 términos que el autor usa con un significado específico o propio (el vocabulario técnico del texto). Listar solo el nombre del término y la locación donde aparece definido — no explicarlos todavía, eso es trabajo de la lectura conceptual.

## output

Verificar si la nota ya existe:

```sh
lore wiki get <citekey>
```

- Si **no existe**, mostrar el borrador completo al usuario y pedir confirmación antes de crear:

```sh
lore wiki create <citekey>
# Crea el esqueleto wiki/refs/@citekey.md con los metadatos de la biblioteca. Error si el citekey no está en la biblioteca.
```

- Si **ya existe**, proponer mejoras a las secciones existentes antes de editar.

Luego escribir cada sección:

```sh
lore wiki update <citekey> Context '<contenido>'
lore wiki update <citekey> Structure '<contenido>'
lore wiki update <citekey> "Author's Terms" '<contenido>'
```

La estructura de la nota es:

**Context** — Quién es el autor, cuándo escribió esto, desde qué tradición intelectual, qué problema estaba intentando resolver en ese momento histórico. No es una biografía: es el contexto que hace legible el texto.

**Structure** — Cómo está organizado el texto y *por qué* está organizado así. No copiar el índice: explicar la función argumentativa de cada parte. ¿Cómo encadenan los capítulos la tesis central? ¿Dónde se concentran los conceptos clave? ¿Hay una parte donde el autor cambia de registro o de nivel de abstracción?

**Author's Terms** — La lista de 5–7 términos identificados, con su locator. Sin definiciones aún.

## locators

Usar formato citeproc:
- Capítulo + sección: `[chap. 1, sect. "Título de sección"]`
- Solo página: `[p. 45]`
- Solo capítulo: `[chap. 3]`

Para PDFs, validar que la página del locator coincide con el marcador `[page N]` en el archivo extraído antes de registrarla.

## finalización

La lectura estructural está completa cuando Context y Structure tienen contenido real — no resúmenes del índice, sino interpretación del propósito y la arquitectura argumentativa del texto.

Si el texto no tiene índice explícito (artículo corto, ensayo), adaptar: buscar la tesis en la introducción y rastrear cómo la desarrolla sección a sección.
