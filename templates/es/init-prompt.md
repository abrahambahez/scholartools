# Prompt de instalación de loretools

Copia todo lo que está debajo de la línea y pégalo en tu sesión de Claude Co-Work después de subir el binario `lore`.

---

Configura loretools en esta carpeta de colección. El binario ha sido subido a esta sesión.

**Paso 1 — Instalar el binario**

```bash
chmod +x lore
./lore --version
```

**Paso 2 — Inicializar la colección**

```bash
./lore refs list
```

Esto crea `.lore/config.json` con la configuración predeterminada. El comando debe retornar `{"ok": true, "references": []}`.

**Paso 3 — Escribir CLAUDE.md**

Crea un archivo llamado `CLAUDE.md` en esta carpeta con el siguiente contenido exacto:

```
# colección loretools

Esta carpeta es una colección de loretools. `lore` es el binario CLI — ejecútalo siempre como `./lore` desde este directorio. No lo instales en el PATH.

## Inicio de sesión

Ejecuta esto automáticamente al inicio de cada sesión, antes de que el investigador pregunte cualquier cosa:

./lore --version
./lore refs list

Si no se encuentra `lore`, la carpeta de colección no está montada. Pide al investigador que verifique que la carpeta esté conectada a esta sesión.

## Estructura de la colección

<colección>/
  lore                    # binario — ejecutar como ./lore
  .lore/config.json       # configuración (creada automáticamente en el primer uso)
  library.json            # biblioteca de referencias en producción
  files/                  # PDFs y documentos archivados
  staging.json            # referencias en staging
  staging/                # archivos en staging

## Flujo de trabajo principal

# Extraer metadatos de un PDF
./lore extract <ruta/al/archivo.pdf>

# Poner en staging una referencia (JSON de extract o manual)
./lore staging stage '<json>' [--file <ruta>]

# Revisar referencias en staging
./lore staging list-staged

# Fusionar staging con la biblioteca
./lore staging merge

# Buscar en la biblioteca
./lore refs filter --query "<texto>" [--author "<apellido>"] [--year AAAA]

# Obtener un registro completo
./lore refs get <citekey>

## Skills

Si el investigador pide un flujo de trabajo complejo (operaciones en masa, gestión de archivos, desambiguación), carga la skill `loretools-references` — contiene la referencia completa del CLI, todos los flags y los detalles de los campos del modelo.
```

**Paso 4 — Verificar**

```bash
./lore refs list
./lore staging list-staged
```

Ambos deben retornar `{"ok": true, ...}`. Avísame cuando la configuración esté completa o si algún paso falla.
