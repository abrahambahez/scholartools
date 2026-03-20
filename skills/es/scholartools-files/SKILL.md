---
name: scholartools-files
description: gestión de archivos en scholartools — vincular PDFs o EPUBs a referencias de la biblioteca, desvincular, leer bytes de archivo, renombrar archivos almacenados, listar todos los archivos y precargar blobs desde S3. Usa esto cuando el usuario pregunte sobre adjuntar un archivo a una referencia, acceder o descargar un PDF del archivo, auditar qué referencias tienen archivos, renombrar un archivo almacenado, o hacer precarga masiva de blobs antes de procesar.
---

Los archivos se vinculan a referencias de la **biblioteca** (no a las que están en staging). Cada referencia puede tener como máximo un archivo.

## Comandos

```sh
scht files link <citekey> <ruta>
# Copia <ruta> al archivo y lo vincula a la referencia.

scht files unlink <citekey>
# Elimina la copia del archivo y limpia el vínculo en la referencia.

scht files get <citekey>
# Devuelve los bytes del archivo. Si blob sync está activo y no está en caché local, lo descarga de S3.

scht files move <citekey> <nombre_destino>
# Renombra el archivo almacenado. nombre_destino es solo el nombre de archivo, sin ruta.

scht files list [--page N]

scht files prefetch [--citekeys clave1,clave2,...]
# Descarga blobs desde S3 para los citekeys dados (todos si se omite).
```

## Campos clave de los modelos

**FileRow** (resultados de list): `citekey, path, mime_type, size_bytes`

**FileRecord** (en Reference como `_file`): `path, mime_type, size_bytes, added_at`

## Notas

- Para adjuntar un archivo al ingresar una referencia: `scht staging stage '<json>' --file <ruta>` — `merge` lo mueve al archivo definitivo.
- Ejecuta `scht files prefetch` antes de procesar en masa para evitar múltiples viajes a S3.
