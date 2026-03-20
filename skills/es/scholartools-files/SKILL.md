---
name: scholartools-files
description: gestión de archivos en scholartools — vincular PDFs o EPUBs a referencias de la biblioteca, desvincular, leer bytes de archivo, renombrar archivos almacenados, listar todos los archivos y precargar blobs desde S3. Usa esto cuando el usuario pregunte sobre adjuntar un archivo a una referencia, acceder o descargar un PDF del archivo, auditar qué referencias tienen archivos, renombrar un archivo almacenado, o hacer precarga masiva de blobs antes de procesar.
---

Los archivos se vinculan a referencias de la **biblioteca** (no a las que están en staging). Cada referencia puede tener como máximo un archivo.

## Funciones

```python
link_file(citekey: str, file_path: str) -> LinkResult
# Copia file_path al archivo y lo vincula a la referencia.
# LinkResult: citekey: str | None, file_record: FileRecord | None, error: str | None

unlink_file(citekey: str) -> UnlinkResult
# Elimina la copia del archivo y limpia el vínculo en la referencia.
# UnlinkResult: unlinked: bool, error: str | None

get_file(citekey: str) -> bytes | None
# Devuelve los bytes del archivo. Si blob sync está activo y no está en caché local, lo descarga de S3.

prefetch_blobs(citekeys: list[str] | None = None) -> PrefetchResult
# Descarga blobs desde S3 para los citekeys dados (todos si es None).
# PrefetchResult: fetched: int, already_cached: int, errors: list[str]

move_file(citekey: str, dest_name: str) -> MoveResult
# Renombra el archivo almacenado. dest_name es solo el nombre de archivo, sin ruta.
# MoveResult: new_path: str | None, error: str | None

list_files(page: int = 1) -> FilesListResult
# FilesListResult: files: list[FileRow], total: int, page: int, pages: int
```

## Campos clave de los modelos

**FileRow**: `citekey, path, mime_type, size_bytes`

**FileRecord** (en Reference como `_file`): `path, mime_type, size_bytes, added_at`

## Notas

- Para adjuntar un archivo al ingresar una referencia: `stage_reference(ref, file_path=...)` — `merge` lo mueve al archivo definitivo.
- Usa siempre `get_file` para leer bytes; no leas `path` directamente si blob sync está activo.
- Llama a `prefetch_blobs` antes de procesar en masa para evitar múltiples viajes a S3.
