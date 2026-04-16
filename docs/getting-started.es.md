# Primeros pasos con loretools

Esta guía es para investigadores que usan **Claude Co-Work** (Proyectos de Claude con acceso a archivos). No se requiere experiencia con la terminal — tu agente de IA gestiona todas las operaciones de shell.

---

## ¿Qué es una colección?

Una **colección** es una única carpeta que contiene todo lo que loretools necesita:

- `lore` — el binario que ejecuta el agente
- `.lore/config.json` — tus preferencias y configuración
- `library.json` — tu biblioteca de referencias
- `files/` — archivos PDF y documentos vinculados a referencias
- `staging/` — referencias en espera de revisión y fusión

Puedes crear una colección por proyecto de investigación (o una colección compartida entre proyectos — tú decides).

---

## Primera sesión: configurar tu colección

### 1. Descarga el binario

Ve a la [página de Releases](https://github.com/abrahambahez/loretools/releases) y descarga el binario para tu plataforma:

- **macOS (Apple Silicon):** `lore-macos-arm64`
- **Linux:** `lore-linux-x86_64`
- **Windows:** `lore-windows-x86_64.exe`

Renombra el archivo a `lore` y colócalo dentro de tu carpeta de colección.

### 2. Copia el prompt de instalación

Ve a la [página principal de loretools](https://github.com/abrahambahez/loretools) y copia el prompt de instalación.

### 3. Abre Claude Co-Work y monta tu carpeta de colección

Abre Claude Projects y conecta tu carpeta de colección para que el agente pueda leer y escribir archivos allí.

### 4. Sube el binario y pega el prompt de instalación

Sube el binario `lore` a tu sesión de Co-Work y pega el prompt de instalación. El agente:

1. Hará el binario ejecutable
2. Lo ejecutará una vez para crear automáticamente `.lore/config.json`
3. Escribirá un `CLAUDE.md` en tu carpeta de colección para que las sesiones futuras arranquen automáticamente
4. Verificará que la colección esté operativa

### 5. Verifica que todo funciona

El agente confirmará la configuración ejecutando:

```
./lore refs list
./lore staging list-staged
```

Ambos deben retornar `{"ok": true, ...}`. Tu colección está lista.

---

## Sesiones posteriores

Cada vez que abras una nueva sesión de Co-Work:

1. Monta tu carpeta de colección
2. El agente lee `CLAUDE.md` y ejecuta la verificación automáticamente — sin necesidad de indicárselo

---

## Estructura del directorio de colección

Tras la configuración, tu carpeta de colección tiene este aspecto:

```
<tu-colección>/
  lore                          # el binario de loretools
  CLAUDE.md                     # instrucciones para el agente (creado durante la instalación)
  .lore/
    config.json                 # configuración (creada automáticamente en el primer uso)
  library.json                  # tu biblioteca de referencias
  files/                        # PDFs y documentos archivados
  staging.json                  # referencias en staging
  staging/                      # archivos en staging
```

---

## Referencia de configuración

`.lore/config.json` se crea automáticamente con valores predeterminados. Solo necesitas editarlo si quieres cambiar algo.

| Campo | Predeterminado | Qué controla |
|-------|----------------|--------------|
| `local.library_dir` | Carpeta de colección (CWD) | Dónde se almacenan `library.json`, `files/` y `staging/`. |
| `citekey.pattern` | `"{author[2]}{year}"` | Patrón para los citekeys generados. Tokens: `{author[N]}` (primeros N apellidos), `{year}`. |
| `citekey.separator` | `"_"` | Separador entre tokens de autor. |
| `citekey.etal` | `"_etal"` | Sufijo cuando los autores superan el límite del patrón. |
| `citekey.disambiguation_suffix` | `"letters"` | Cómo desambiguar claves duplicadas: `"letters"` (a/b/c) o `"title[1-9]"` (primeras N palabras del título). |

---

## Skills

Para flujos de trabajo complejos — operaciones en masa, gestión de archivos, desambiguación de referencias — instala la skill `loretools-references`. Descarga el zip de la skill desde la página de Releases y pídele al agente que la instale.

---

## Resolución de problemas

**`lore` no se encuentra**
Confirma que la carpeta de colección está montada y que `lore` está presente. Dile al agente: "Lista los archivos en la carpeta de colección."

**Permiso denegado al ejecutar `lore`**
Dile al agente: "Haz lore ejecutable con chmod +x."

**Configuración no encontrada**
Ejecuta `./lore refs list` una vez — esto crea automáticamente `.lore/config.json` si no existe.

**Biblioteca vacía en el primer uso**
`library.json` y `staging.json` se crean en la primera escritura. Es normal obtener resultados vacíos antes de eso.
