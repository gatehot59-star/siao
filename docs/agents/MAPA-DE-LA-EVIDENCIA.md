# MAPA DE LA EVIDENCIA · dónde está cada medición de SIAO

**Última verificación contra el repo:** 2026-09-08 07:25 (America/Buenos_Aires) · `main` = `75ae14c`  
**Versión 3.** La v1 mandaba a las ramas. La v2 agregó la salvedad del arnés inerte. **La v3 es la primera en la que la evidencia está en `main`**, así que las rutas de acá ya no necesitan cambiar de rama.

---

## 0 · Estado: la consolidación está hecha

**177 archivos de texto (14,36 MB)** de `mediciones/` y `tools/` de las cuatro ramas, más **15 workflows**, ahora viven en `main`. Se verificó antes de mover: **cero colisiones de contenido** (185 rutas únicas, ninguna ruta repetida entre ramas con blob distinto; el script abortaba si había una).

**Lo que NO se movió, y es una decisión, no un olvido:** los **8 archivos `.stg`** (89,3 MB). Son **binarios derivados** y `AGENTS.md` prohibe commitearlos. Quedan referenciados por sha256, tamaño, rama y SHA en **`mediciones/MANIFIESTO-BINARIOS-NO-COMMITEADOS.md`**.

> **Por qué eso no rompe la recomputabilidad:** la cadena ya estaba cortada más arriba. El `vmlinux` del que salen los `.stg` pesa 354.673.168 B y **nunca se commiteó en ninguna rama**, así que recomputar un veredicto desde cero siempre exigió rebuildear el kernel. Lo que el manifiesto conserva es la **identidad** del intermedio.

### Lo que sigue pendiente de decisión de Abraham

1. **Las 6 ramas siguen sin protección.** Ahora borrar una **ya no se lleva el trabajo técnico** (está en `main`), pero sí se lleva los 8 `.stg`. El daño pasó de catastrófico a acotado.
2. **`mediciones/INDICE.md` tiene dos filas contradictorias** para F-004d@6.1, una `NO MEDIDO` y otra `VERDE`, y su encabezado lo declara **gate**. Vino tal cual de la rama: **no lo corrijo de paso**, porque borrar una fila de un índice ajeno en medio de una consolidación es mezclar mover con editar.

---

## 1 · El mapa, por falsador · **rutas de `main`**

| Falsador | Veredicto | Archivo que hay que ABRIR (en `main`) |
|---|---|---|
| **FALSADOR-001** userland openKylin arm64 fuera de su ISO | **A VERDE, B VERDE** | `mediciones/falsador-001/arm64/` y `/x64/` |
| **F-001** userland sobre GKI | ver el `.md` | `mediciones/f-001/F-001.md` + `F-001-salida-cruda.txt` |
| **F-002** rootfs `siao-base-s1` (9 versiones) | **CERRADO** en la v9 | `mediciones/f-002/F-002-v9.md` (+ `v3`…`v8` para la serie) |
| **F-001-S1** GKI de Google en QEMU | **VERDE**, arrancó | `mediciones/f-001-s1/f001s1-aarch64-boot.txt` |
| **F-004** el fragmento rompe el KMI | **ROJO**, causa `SYSVIPC` | `mediciones/f-004/` y `mediciones/f-004-v3/` |
| **F-004b** padding KABI | perdí la predicción; apareció el 2º rompedor | `mediciones/f-004b/F-004b-VEREDICTO.txt` |
| **F-004c** nueve símbolos sin `CGROUP_PIDS` | **VERDE** (495 B, 0 offsets, 0 CRC) | `mediciones/f-004c/F-004c-VEREDICTO.txt` |
| **F-004d** ocho símbolos @ android15-6.6 | **VERDE** (68 B) | `mediciones/f-004d/` |
| **F-004d @ android14-6.1** ← *el que ordena el proyecto* | **VERDE en ABI**, sin parche al ACK · **el `Error 126` sigue ABIERTO, ver §2.1** | **`mediciones/f-004d-61/F-004d-61-VEREDICTO.txt`** + `v3-ocho.json` + `v3-ocho-archscripts.txt` |
| **F-007a / F-007b** vendors y `.ko` real de Pixel | ver los recibos | `docs/agents/respuestas/2026-09-06-13-*` y `-14-*` |
| Falsadores de KVM en runners | ver los recibos | `docs/agents/respuestas/2026-09-06-03-*` y `-04-*` |
| **F-007c** · que un `.ko` real CARGUE | **NO MEDIDO** | no existe todavía |

**Instrumentos:** los **15** scripts de Python que produjeron todo esto están en `tools/` **de `main`**.

**Workflows:** los **15** que corrieron las mediciones están en `docs/campo/workflows-de-las-ramas/`, con extensión `.txt` a propósito: como evidencia hay que poder leerlos, no dispararlos. **Son 15 y no 12:** `titan/f-004-kmi` tiene 12 y las otras tres ramas suman 3 más.

**Binarios `.stg`:** `mediciones/MANIFIESTO-BINARIOS-NO-COMMITEADOS.md`. Siguen solo en las ramas.

---

## 2 · El veredicto que más se busca

Verbatim de `mediciones/f-004d-61/F-004d-61-VEREDICTO.txt`:

```
== F-004d en la generacion android14-6.1 ==
  maquina x86_64 | fecha UTC 2026-09-07T14:26:07Z
  R-17: baseline PROPIO de 6.1. No se cita nada de 6.6.
  baseline  .stg 10699061 B | sha256 c91ed3a1963a261b290c624d251f081b
  ocho      .stg 10699333 B | sha256 047141d8822061e9a61a3865f236dae0
=== pasada SIN CRC ===
  rc=4 | 68 B | CRC x0 | added x1 | byte-size x0 | offset x0
  structs tocadas: NINGUNA
  --- reporte ENTERO ---
   | function symbol 'void put_pid_ns(struct pid_namespace*)' was added

================ VEREDICTO ================
    F-004d @ android15-6.6 : SIN CRC     68 B | offsets 0 | CRC 0   (medido ayer)
    F-004d @ android14-6.1 : SIN CRC     68 B | offsets 0 | CRC 0
  VERDE: fragmento de OCHO ABI-compatible en android14-6.1, sin parche al ACK
  R-13: esto dice ABI-compatible. Que un .ko real CARGUE es F-007c.
```

### 2.0 · CUALES son los ocho simbolos del fragmento

El nombre "fragmento de OCHO" no dice cuales. Estaban solo en el JSON de la
evidencia, y por eso un auditor externo propuso correr un falsador (su F-004e:)
"fragmento con POSIX_MQUEUE + IPC_NS y sin SYSVIPC") que **ya es este
fragmento y ya dio verde**. Verbatim de `mediciones/f-004d-61/v3-ocho.json`:

```
CONFIG_DEVTMPFS     y    CONFIG_DEVTMPFS_MOUNT  y    CONFIG_FHANDLE     y
CONFIG_POSIX_MQUEUE y    CONFIG_TMPFS_XATTR     y    CONFIG_AUTOFS_FS   y
CONFIG_PID_NS       y    CONFIG_IPC_NS          y

CONTROL | CONFIG_SYSVIPC     NO esta en =y (correcto)
CONTROL | CONFIG_CGROUP_PIDS NO esta en =y (correcto)
```

**Tres cosas que se leen de esa lista y no estaban escritas en ningun indice:**

1. **El rojo de `IPC_NS` de F-001 esta cerrado por el fragmento**: esta en `y`.
2. **`POSIX_MQUEUE` es lo que habilita `IPC_NS` sin `SYSVIPC`**, porque su
dependencia Kconfig es `SYSVIPC || POSIX_MQUEUE`. Esa es la via por la que
F-004d@6.1 dio verde **sin parche al ACK**: `POSIX_MQUEUE` toca
`struct ipc_namespace`, no `task_struct`.
3. **`DEVTMPFS` y `DEVTMPFS_MOUNT` estan presentes**, asi que systemd va a
tener `/dev`: el baseline los tiene `APAGADO` y `AUSENTE`.

**Lo que esa lista NO dice, y es otro sujeto:** que el userland funcione sin
SysV IPC. UKUI es Qt, y Qt 5.x usa backend SysV para `QSharedMemory`. Eso es
F-009 y sigue **NO MEDIDO**.

### 2.1 · DOS salvedades, y las dos hay que leer antes de citar este verde

**(a) Alcance, declarado por el propio veredicto (R-13):** dice **ABI-compatible**, **no** dice que un módulo real cargue. Eso es **F-007c** y sigue **NO MEDIDO**.

**(b) El `Error 126` NO está eliminado.** El guard serial salió **inerte en los dos brazos**. El JSON tiene **ocho** campos relevantes y hay que citarlos completos:

```json
"rc_archscripts": 0,
"segundos_archscripts": 0.02,          <-- decisivo
"archscripts_hizo_trabajo": false,     <-- decisivo
"error_126_serial": false,
"error_126_paralelo": false,
"rc_build": 0,
"pahole": "/usr/bin/pahole",
"parche_al_ack": false
```

Y `v3-ocho-archscripts.txt` muestra el arreglo **presente en el comando** y el paso sin trabajo: `make ... HOSTCFLAGS='-DUSE_PKCS11_ENGINE' -j1 archscripts` → `rc = 0 | segundos = 0.02` → `make[1]: Nothing to be done for 'archscripts'.`

El falsador declarado **antes** de correr decía: *"si vuelve a dar 0,0 s, el arreglo no se aplicó y no hay que interpretar nada más"*. **Dio 0,02 s.** Es **una carrera ganada, no cerrada**, y el 126 está medido como intermitente. Cerrarlo necesita una **matriz de N corridas** del mismo brazo contando fallos: es `needs-runtime`.

### 2.2 · Un defecto de MI instrumento, encontrado al consolidar

El `VEREDICTO.txt` imprime:

```
baseline  .stg 10699061 B | sha256 c91ed3a1963a261b290c624d251f081b
```

Eso son **32 caracteres hexadecimales**, o sea el largo de un **md5**. Un sha256 tiene 64. El valor real, calculado al armar el manifiesto, es `c91ed3a1963a261b290c624d251f081b`**`7ecd698cb06013d5012af8ae69ee1e32`**.

**El instrumento trunca el hash a la mitad y lo rotula `sha256`.** No invalida nada —el prefijo coincide, es el mismo archivo— pero **un hash truncado sin decir que está truncado es un identificador que parece más fuerte de lo que es**, y este proyecto usa hashes para decidir si dos artefactos son el mismo. A corregir en `tools/f004d61_stg.py`. **NO corregido todavía.**

---

## 3 · Archivos que hoy mienten

**Corregidos el 2026-09-08:** `CONTEXTO-SIAO.md` (las dos afirmaciones falsas del §3) y `README.md` ("nada corrió en ninguna máquina" y la promesa del banco contra el ADR-001 §8).

**Siguen abiertos:**

| Archivo | Dice | Es |
|---|---|---|
| `mediciones/INDICE.md` | **dos** filas para F-004d@6.1: una `NO MEDIDO` y otra `VERDE` | la vieja no se borró. Su encabezado lo declara **gate** del falsador siguiente: un gate que se contradice no gatea |
| `ADR-001` §7 Fase 1 | pide *"(16K aligned) sobre GKI recompilado"* | FALSADOR-001 lo mató (H-006 del cementerio): los 146 ELF ya vienen con `p_align 65536` |
| `docs/auditorias/` y `docs/audits/` | dos carpetas para lo mismo | sin unificar |

---

## 4 · Dos advertencias con su error ya cometido

1. **Listar un directorio devuelve nombres y tamaños, no contenido.** Un `ls` de `mediciones/f-004d-61/` muestra 46 archivos y no dice qué dice ninguno. El veredicto está **adentro** del archivo que se llama `VEREDICTO`. *(Costado: un auditor concluyó `NO MEDIDO` sobre un verde.)*
2. **Citar un subconjunto de campos es recorte de evidencia.** Se citaron seis de los ocho campos de `v3-ocho.json`, omitiendo justo los dos que el falsador vuelve decisivos. *(Costado: el `Error 126` quedó leído como resuelto cuando sigue abierto.)*

Son el mismo defecto con distinto radio: **no leer el archivo, y leerlo y recortarlo.**

---

## 5 · Mantenimiento

Se actualiza **en el mismo turno** en que una medición cierra. Si su fecha de verificación es anterior al último archivo de `docs/agents/respuestas/`, **está desactualizado por definición**.

**NO MEDIDO en esta versión:** el **contenido** de los 15 instrumentos de `tools/` —ahora están en `main` y se pueden leer, pero **nadie verificó que midan lo que sus nombres dicen medir**, y esa es la auditoría más cara y sigue sin hacerse—; los ADR 002, 003 y 004; y si los 8 `.stg` referenciados en el manifiesto siguen existiendo dentro de un mes.
