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

Los cambios se aplican en el siguiente comando `scht`.

---

## 3. Inicializar la identidad de este dispositivo

Ejecuta una sola vez por dispositivo. Genera un par de claves Ed25519 para que tus cambios puedan ser firmados y verificados.

```sh
scht peers init alice laptop
# imprime el JSON de PeerIdentity: {peer_id, device_id, public_key}

scht peers register-self
# Escribe tu clave pública en el registro local de peers.
```

`peer_id` y `device_id` deben coincidir con lo que pusiste en config.json.

---

## 4. Subir el primer snapshot

Sube una copia completa de tu biblioteca al bucket. Los demás dispositivos se inicializarán desde aquí.

```sh
scht sync snapshot
```

Ejecútalo una vez después de la configuración inicial y de nuevo tras importaciones masivas.

---

## 5. Flujo de sincronización diaria

Siempre haz pull antes de push para aplicar los cambios remotos primero.

```sh
scht sync pull    # aplica cambios remotos
# ... haz ediciones locales (agregar/actualizar/eliminar referencias) ...
scht sync push    # sube las entradas del registro de cambios al bucket
```

Después del pull, revisa los conflictos:

```sh
scht sync list-conflicts
# imprime lista de ConflictRecord: uid, field, local_value, local_timestamp_hlc,
#                                  remote_value, remote_timestamp_hlc, remote_peer_id

# Elige el ganador para cada conflicto:
scht sync resolve-conflict <uid> <field> <valor_local>    # conservar local
scht sync resolve-conflict <uid> <field> <valor_remoto>   # conservar remoto
```

Para recuperar una referencia eliminada por un peer remoto:

```sh
scht sync restore <citekey>
```

---

## 6. Agregar un segundo dispositivo (mismo investigador)

Usa esto cuando quieras sincronizar la biblioteca de `alice` a una nueva máquina (p.ej. `"desktop"`).

**En el nuevo dispositivo:**

1. Edita config.json — mismo `peer_id`, nuevo `device_id`:
   ```json
   { "peer": { "peer_id": "alice", "device_id": "desktop" } }
   ```
2. Genera un par de claves y comparte el JSON de identidad con el primer dispositivo:
   ```sh
   scht peers init alice desktop
   # copia el JSON de identidad impreso
   ```

**En el primer dispositivo (como admin):**

```sh
scht peers add-device alice '<json-identidad>'
# o: echo '<json-identidad>' | scht peers add-device alice
scht sync push    # publica el registro de peer actualizado en el bucket
```

**De vuelta en el nuevo dispositivo:**

```sh
scht peers register-self
scht sync pull    # inicializa la biblioteca desde el snapshot + registro de cambios
```

---

## 7. Agregar un colaborador (investigador diferente)

Usa esto para darle acceso al bucket a otra persona (`"bob"`).

**Bob, en su dispositivo:**

```sh
scht peers init bob bob-laptop
# copia el JSON de identidad impreso
scht peers register-self
```

**Alice (admin), en su dispositivo:**

```sh
scht peers register '<json-identidad-bob>'
# o: echo '<json-identidad-bob>' | scht peers register
scht sync push    # publica el registro de peer de bob en el bucket
```

**Bob:**

```sh
scht sync pull    # inicializa desde la biblioteca compartida
```

---

## 8. Revocar acceso

Revocar un único dispositivo (p.ej. una laptop perdida):

```sh
scht peers revoke-device alice laptop
scht sync push
```

Revocar un peer completo (elimina todos sus dispositivos):

```sh
scht peers revoke bob
scht sync push
```

Los dispositivos revocados son rechazados en el pull por todos los demás peers.

---

## Referencia de CLI

```sh
# Identidad
scht peers init <peer_id> <device_id>
scht peers register-self
scht peers register [<identity_json>|-]
scht peers add-device <peer_id> [<identity_json>|-]
scht peers revoke-device <peer_id> <device_id>
scht peers revoke <peer_id>

# Sincronización
scht sync push
scht sync pull
scht sync snapshot
scht sync list-conflicts
scht sync resolve-conflict <uid> <field> <valor>
scht sync restore <citekey>
```
