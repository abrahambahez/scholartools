---
name: scholartools-sync-peers
description: sincronización distribuida y gestión de peers en scholartools — guía paso a paso para configurar sync respaldado en S3, agregar dispositivos y colaboradores, flujo de sincronización diaria, resolución de conflictos y ciclo de vida de peers. Usa esto cuando el usuario pregunte sobre sincronizar su biblioteca entre dispositivos, configurar un nuevo dispositivo o colaborador, registrar o revocar peers, manejar conflictos de sincronización, o cualquier tarea relacionada con el registro de cambios en S3. Guía al usuario por todo el recorrido aunque solo mencione un paso.
---

La sincronización funciona escribiendo un registro de cambios firmado criptográficamente en un bucket compatible con S3. Cada dispositivo lee los cambios de los demás y verifica las firmas — sin servidor central, sin necesidad de confianza ciega.

## Resumen del recorrido

1. [Obtener un bucket](#1-obtener-un-bucket)
2. [Configurar este dispositivo](#2-configurar-este-dispositivo)
3. [Inicializar la identidad de este dispositivo](#3-inicializar-la-identidad-de-este-dispositivo)
4. [Subir el primer snapshot](#4-subir-el-primer-snapshot)
5. [Flujo de sincronización diaria](#5-flujo-de-sincronizacion-diaria)
6. [Agregar un segundo dispositivo (mismo investigador)](#6-agregar-un-segundo-dispositivo-mismo-investigador)
7. [Agregar un colaborador (investigador diferente)](#7-agregar-un-colaborador-investigador-diferente)
8. [Revocar acceso](#8-revocar-acceso)

---

## 1. Obtener un bucket

Necesitas un bucket de almacenamiento de objetos compatible con S3. Cualquiera de estos funciona:

| Proveedor | Notas |
|-----------|-------|
| **AWS S3** | Estándar. Pon `endpoint` en `null`. |
| **Cloudflare R2** | Sin costo de egreso. Pon `endpoint` con tu URL de R2. |
| **Backblaze B2** | Económico. Pon `endpoint` con la URL S3-compatible de B2. |
| **MinIO** | Auto-hospedado. Pon `endpoint` con tu URL de MinIO. |

De tu proveedor, obtén: **nombre del bucket**, **access key**, **secret key** y **URL del endpoint** (null para AWS).

---

## 2. Configurar este dispositivo

Edita `~/.config/scholartools/config.json` (Windows: `C:\Users\<usuario>\.config\scholartools\config.json`).

Agrega un bloque `sync` y un bloque `peer`. Elige cualquier nombre para `peer_id` (quién eres, p.ej. `"alice"`) y `device_id` (esta máquina, p.ej. `"laptop"`):

```json
{
  "sync": {
    "bucket": "mi-bucket-scholartools",
    "access_key": "TU_ACCESS_KEY",
    "secret_key": "TU_SECRET_KEY",
    "endpoint": null
  },
  "peer": {
    "peer_id": "alice",
    "device_id": "laptop"
  }
}
```

Luego recarga:

```python
reset()
```

---

## 3. Inicializar la identidad de este dispositivo

Ejecuta una sola vez por dispositivo. Genera un par de claves Ed25519 para que tus cambios puedan ser firmados y verificados por otros dispositivos.

```python
result = peer_init("alice", "laptop")
# result.identity -> PeerIdentity(peer_id, device_id, public_key)

peer_register_self()
# Escribe tu clave pública en el registro local de peers.
```

`peer_id` y `device_id` deben coincidir con lo que pusiste en config.json.

---

## 4. Subir el primer snapshot

Sube una copia completa de tu biblioteca al bucket. Los demás dispositivos se inicializarán desde aquí.

```python
create_snapshot()
```

Ejecútalo una vez después de la configuración inicial y de nuevo tras importaciones masivas.

---

## 5. Flujo de sincronización diaria

Siempre haz pull antes de push para aplicar los cambios remotos primero.

```python
pull()   # aplica cambios remotos; devuelve applied_count, rejected_count, conflicted_count
# ... haz ediciones locales (agregar/actualizar/eliminar referencias) ...
push()   # sube las entradas del registro de cambios al bucket
```

Después del pull, revisa los conflictos:

```python
conflicts = list_conflicts()
# ConflictRecord: uid, field, local_value, local_timestamp_hlc,
#                 remote_value, remote_timestamp_hlc, remote_peer_id

for c in conflicts:
    # Compara c.local_value con c.remote_value y elige el ganador:
    resolve_conflict(c.uid, c.field, c.local_value)   # conservar local
    # o
    resolve_conflict(c.uid, c.field, c.remote_value)  # conservar remoto
```

Para recuperar una referencia eliminada por un peer remoto:

```python
restore_reference(citekey)
```

---

## 6. Agregar un segundo dispositivo (mismo investigador)

Usa esto cuando quieras sincronizar la biblioteca de `alice` a una nueva máquina (p.ej. `"desktop"`).

**En el nuevo dispositivo:**

1. Edita config.json — mismo `peer_id`, nuevo `device_id`:
   ```json
   { "peer": { "peer_id": "alice", "device_id": "desktop" } }
   ```
2. Genera un par de claves para este dispositivo:
   ```python
   result = peer_init("alice", "desktop")
   identity = result.identity   # comparte esto con el primer dispositivo
   ```

**En el primer dispositivo (como admin):**

```python
peer_add_device("alice", identity)
# identity es el PeerIdentity del nuevo dispositivo: {peer_id, device_id, public_key}
push()   # publica el registro de peer actualizado en el bucket
```

**De vuelta en el nuevo dispositivo:**

```python
peer_register_self()
pull()   # inicializa la biblioteca desde el snapshot + registro de cambios
```

---

## 7. Agregar un colaborador (investigador diferente)

Usa esto para darle acceso al bucket a otra persona (`"bob"`).

**Bob, en su dispositivo:**

```python
result = peer_init("bob", "bob-laptop")
identity = result.identity   # comparte esto con alice
peer_register_self()
```

**Alice (admin), en su dispositivo:**

```python
peer_register(identity)    # registra el dispositivo de bob localmente
push()                     # publica el registro de peer de bob en el bucket
```

**Bob:**

```python
pull()   # inicializa desde la biblioteca compartida
```

Los dispositivos tienen rol `"contributor"` por defecto. Para hacer a Bob admin, establece `role="admin"` en el `DeviceIdentity` pasado a `peer_add_device`.

---

## 8. Revocar acceso

Revocar un único dispositivo (p.ej. una laptop perdida):

```python
peer_revoke_device("alice", "laptop")
push()
```

Revocar un peer completo (elimina todos sus dispositivos):

```python
peer_revoke("bob")
push()
```

Los dispositivos revocados son rechazados en el pull por todos los demás peers.

---

## Referencia de API

```python
# Identidad
peer_init(peer_id: str, device_id: str) -> PeerInitResult
peer_register_self() -> Result
peer_register(identity: PeerIdentity) -> PeerRegisterResult
peer_add_device(peer_id: str, device_identity: PeerIdentity) -> PeerAddDeviceResult
peer_revoke_device(peer_id: str, device_id: str) -> PeerRevokeDeviceResult
peer_revoke(peer_id: str) -> PeerRevokeResult

# Sincronización
push() -> PushResult              # entries_pushed: int, errors: list[str]
pull() -> PullResult              # applied_count, rejected_count, conflicted_count, errors
create_snapshot() -> None

# Conflictos
list_conflicts() -> list[ConflictRecord]
resolve_conflict(uid: str, field: str, winning_value) -> Result
restore_reference(citekey: str) -> Result
```
