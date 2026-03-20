---
name: scholartools-config
description: referencia de configuración de scholartools — ubicación del archivo, estructura de ajustes, variables de entorno, tokens de patrón de citekey y rutas de datos. Usa esto cuando el usuario pregunte cómo configurar scholartools, cambiar cualquier opción, habilitar o deshabilitar una fuente de API (Crossref, Google Books, Semantic Scholar, etc.), configurar la extracción de PDFs con LLM, personalizar la generación de citekeys, o cuando alguna función falle por configuración faltante o incorrecta.
---

Ruta del archivo de configuración:

| SO | Ruta |
|----|------|
| Linux / macOS | `~/.config/scholartools/config.json` |
| Windows | `C:\Users\<usuario>\.config\scholartools\config.json` |

Se crea automáticamente con valores por defecto en el primer uso. Edítalo manualmente; llama a `reset()` después de hacer cambios en tiempo de ejecución.

## Estructura de ajustes

```json
{
  "backend": "local",
  "local": { "library_dir": "~/.local/share/scholartools" },
  "apis": {
    "email": "tu@email.com",
    "sources": [
      {"name": "crossref", "enabled": true},
      {"name": "semantic_scholar", "enabled": true},
      {"name": "arxiv", "enabled": true},
      {"name": "openalex", "enabled": true},
      {"name": "doaj", "enabled": true},
      {"name": "google_books", "enabled": true}
    ]
  },
  "llm": { "model": "claude-sonnet-4-6" },
  "citekey": {
    "pattern": "{author[2]}{year}",
    "separator": "_",
    "etal": "_etal",
    "disambiguation_suffix": "letters"
  }
}
```

## Variables de entorno

| Variable | Propósito |
|----------|-----------|
| `ANTHROPIC_API_KEY` | Extracción LLM de PDFs escaneados |
| `GBOOKS_API_KEY` | Fuente Google Books |
| `SEMANTIC_SCHOLAR_API_KEY` | Límites de tasa más altos en Semantic Scholar |

## Tokens de citekey

- `{author[N]}` — primeros N apellidos de autores unidos por `separator`
- `{year}` — año de 4 dígitos
- `etal` — se añade cuando los autores superan N
- `disambiguation_suffix`: `"letters"` (a/b/c) o `"title[1-9]"` (primeras N palabras del título)

## Función

```python
reset() -> None
# Limpia la config y el contexto en caché. Obligatorio después de editar config.json en tiempo de ejecución.
```

## Rutas calculadas (relativas a library_dir)

| Ruta | Propósito |
|------|-----------|
| `library.json` | Biblioteca de producción |
| `files/` | Archivos almacenados |
| `staging.json` | Referencias en staging |
| `staging/` | Archivos en staging |
| `peers/` | Registro de peers |
