---
name: lectura-conceptual
description: "Use this skill when the user wants to understand the conceptual substance of a specific text: what the author means by their own terms, how their argument is built and justified, what problems the text resolves vs. leaves open, or whether the argument holds up under scrutiny. Also use when the user wants to fill or update the 'Terms and Arguments' section of an existing @citekey.md, reconstruct an author's argument with locators, or produce critical notes from a source. Trigger phrases include: 'lectura conceptual', 'lectura analítica', 'dame los argumentos', 'reconstruye los argumentos', 'qué términos define el autor', 'quiero entender a fondo', or any request to work through an author's concepts or add analytical entries to a note. This is post-orientation, depth-first work — the user already has a structural map and now wants understanding. Do not use for first contact with a text, structural overviews, or multi-text comparisons."
---

# lectura-conceptual

La lectura conceptual es para la *comprensión*. Partiendo del mapa que dio la lectura estructural, el objetivo es reconstruir el pensamiento del autor: qué quiere decir con cada término, cómo arma sus argumentos, qué problemas resuelve y cuáles deja abiertos.

## prerrequisitos

Ejecutar ambas verificaciones antes de cualquier otra cosa. Detener si alguna falla.

```sh
lore wiki section-ready <citekey> Structure
# Exit 0 significa que la sección Structure tiene contenido. Si exit 1, hacer la lectura estructural primero.

lore files get <citekey>
# Debe devolver una ruta de archivo. Si no hay archivo vinculado, convertir y adjuntar la fuente antes de continuar.
```

Luego obtener el texto extraído:

```sh
lore read <citekey>
# Devuelve output_path al archivo de texto legible. Usar este archivo durante todo el análisis.
```

## flujo

Seguir este orden estrictamente — no pasar a los argumentos sin antes fijar los términos, porque los argumentos dependen del sentido exacto que el autor da a sus palabras.

### 1. Radiografía

Retomar la lectura estructural y completar o corregir lo que haga falta. Responder:
- ¿De qué tipo de texto se trata (argumentativo, descriptivo, narrativo, técnico)?
- ¿Cuál es la tesis central en una oración?
- ¿Cuál es el problema que el autor intenta resolver?
- ¿La estructura que describió la lectura estructural era correcta, o hay que ajustarla?

Si la sección Structure necesita corrección:

```sh
lore wiki update <citekey> Structure '<contenido corregido>'
```

### 2. Términos

Identificar las palabras a las que el autor da un significado específico o distinto al uso común. Para cada término:
- Definición exacta en este texto (no la definición estándar del diccionario).
- Locator donde aparece definida.
- Nota permanente sugerida (el nombre más abstracto y reutilizable del concepto).

Antes de redactar cada entrada, buscar si ya existe una nota permanente:

```sh
lore wiki search '<nombre del concepto>'
# Devuelve rutas absolutas a notas coincidentes en wiki/notes/. Sin output significa que no hay coincidencias.
```

Si existe una coincidencia, referenciarla con `[[título de nota existente]]` en lugar de escribir una síntesis nueva.

### 3. Proposiciones

Las afirmaciones centrales donde el autor toma posición — no los hechos que describe, sino lo que sostiene. Para cada proposición:
- Locator.
- Título de una posible nota permanente que capture la afirmación.

### 4. Argumentos

Reconstruir la cadena de razonamiento que sostiene cada proposición: qué premisas usa, cómo las conecta, qué evidencia aporta, dónde hay saltos o supuestos implícitos.

## output

Escribir la sección completa de Términos y Argumentos:

```sh
lore wiki update <citekey> "Terms and Arguments" '<contenido>'
```

**Formato de cada entrada:**
```
- título de nota permanente: contenido del autor, mencionando el término original si difiere del título [@citekey, locator]. Síntesis propia en una oración.
```

Si la nota permanente ya existe en el wiki:
```
- [[título de nota existente]]: contenido del autor [@citekey, locator]. Síntesis propia en una oración.
```

Si el concepto ya está cubierto por una nota existente, reemplazar la síntesis por `(para ampliar [[nota]])`.

**Convenciones de formato:**
- Sin saltos de línea entre ítems de la misma lista; sí entre secciones distintas.
- El título de cada entrada es el nombre más abstracto y reutilizable del concepto — pensarlo como si fuera a ser una nota que cualquier texto futuro pudiera citar.
- Cuando se usa conocimiento del modelo de entrenamiento para contextualizar (no del texto), marcarlo con `(nota IA)`.

**Último paso:** escribir el resumen en el frontmatter:

```sh
lore wiki update <citekey> summary '<párrafo que sintetiza la tesis y el argumento central>'
```

Hacerlo solo si el campo `summary` del frontmatter está vacío. No resumir lo que ya está en la lectura estructural — elevar, profundizar o corregir.

## reglas

- Si hay contradicción entre lo que dice `@citekey.md` y lo que dice el texto fuente, señalarlo explícitamente antes de editar. La fuente primaria gana.
- No inferir argumentos que el autor no hace explícitos. Si algo es implícito, marcarlo como tal.
- La profundidad depende del texto: un artículo de 20 páginas no necesita el mismo nivel de desagregación que un libro de 400.
