# MAPA DE LA EVIDENCIA · dónde está cada medición de SIAO

**Última verificación contra el repo:** 2026-09-08 11:05 (America/Buenos_Aires) · `main` = `7ddd416`  
**Versión 4.** La v1 mandaba a las ramas. La v2 agregó la salvedad del arnés inerte. La v3 fue la primera con la evidencia en `main`. **La v4 incorpora la auditoría de los INSTRUMENTOS** que el §5 de la v3 declaraba como el NO MEDIDO más caro del proyecto: FABLE 5.1 la empezó y encontró tres defectos, los tres confirmados con medición (§2.3).

---

## 0 · Estado: la consolidación está hecha

**177 archivos de texto (14,36 MB)** de `mediciones/` y `tools/` de las cuatro ramas, más **15 workflows**, ahora viven en `main`. Se verificó antes de mover: **cero colisiones de contenido** (185 rutas únicas, ninguna ruta repetida entre ramas con blob distinto; el script abortaba si había una).

**Lo que NO se movió, y es una decisión, no un olvido:** los **8 archivos `.stg`** (89,3 MB). Son **binarios derivados** y `AGENTS.md` prohibe commitearlos. Quedan referenciados por sha256, tamaño, rama y SHA en **`mediciones/MANIFIESTO-BINARIOS-NO-COMMITEADOS.md`**.

> **Por qué eso no rompe la recomputabilidad:** la cadena ya estaba cortada más arriba. El `vmlinux` del que salen los `.stg` pesa 354.673.168 B y **nunca se commiteó en ninguna rama**, así que recomputar un veredicto desde cero siempre exigió rebuildear el kernel. Lo que el manifiesto conserva es la **identidad** del intermedio.

**Protección:** `main` y las cuatro ramas de evidencia están bajo el ruleset `no-borrar-ni-forzar-la-evidencia`, falsado borrando de verdad (204 afuera del ruleset, 422 adentro).

### Lo que sigue pendiente de decisión de Abraham

1. **`mediciones/INDICE.md` tiene dos filas contradictorias** para F-004d@6.1, una `NO MEDIDO` y otra `VERDE`, y su encabezado lo declara **gate**. Vino tal cual de la rama.
2. **Rebuildear el brazo `ocho` para obtener el `Image`** (§2.3, H-2). Gasta un run de Actions y es la precondición de F-001-S2.

---

## 1 · El mapa, por falsador · **rutas de `main`**

| Falsador | Veredicto | Archivo que hay que ABRIR (en `main`) |
|---|---|---|
| **FALSADOR-001** userland openKylin arm64 fuera de su ISO | **A VERDE, B VERDE** | `mediciones/falsador-001/arm64/` y `/x64/` |
| **F-001** userland sobre GKI | ver el `.md` | `mediciones/f-001/F-001.md` + `F-001-salida-cruda.txt` |
| **F-002** rootfs `siao-base-s1` (9 versiones) | **CERRADO** en la v9 | `mediciones/f-002/F-002-v9.md` (+ `v3`…`v8` para la serie) |
| **F-001-S1** GKI de Google en QEMU | **VERDE como ARNÉS** (banner + control discrimina). **CAVEAT H-1, ver §2.3:** la consola está truncada por `head -200` a t=0,458 s y el campo `llego_a_init: false` de los dos JSON **no midió eso**: es **NO MEDIDO** | `mediciones/f-001-s1/f001s1-aarch64-boot.txt` + **`mediciones/f-001-s1/CORRECCION-H1-el-campo-llego_a_init-nunca-midio-eso.md`** |
| **F-004** el fragmento rompe el KMI | **ROJO**, causa `SYSVIPC` | `mediciones/f-004/` y `mediciones/f-004-v3/` |
| **F-004b** padding KABI | perdí la predicción; apareció el 2º rompedor | `mediciones/f-004b/F-004b-VEREDICTO.txt` |
| **F-004c** nueve símbolos sin `CGROUP_PIDS` | **VERDE** (495 B, 0 offsets, 0 CRC) | `mediciones/f-004c/F-004c-VEREDICTO.txt` |
| **F-004d** ocho símbolos @ android15-6.6 | **VERDE** (68 B) | `mediciones/f-004d/` |
| **F-004d @ android14-6.1** ← *el que ordena el proyecto* | **VERDE en ABI**, sin parche al ACK · **el `Error 126` sigue ABIERTO, ver §2.1** · **y el kernel NO existe como artefacto arrancable, ver §2.3 H-2** | **`mediciones/f-004d-61/F-004d-61-VEREDICTO.txt`** + `v3-ocho.json` + `v3-config-ocho.txt` + `v3-ocho-archscripts.txt` |
| **F-007a / F-007b** vendors y `.ko` real de Pixel | ver los recibos | `docs/agents/respuestas/2026-09-06-13-*` y `-14-*` |
| Falsadores de KVM en runners | ver los recibos | `docs/agents/respuestas/2026-09-06-03-*` y `-04-*` |
| **F-001-S2** · systemd de `siao-base-s1` sobre el kernel de OCHO | **NO MEDIDO** · diseño de FABLE aceptado con correcciones | `docs/adr/2026-09-08-08-ADR-008-resolucion-del-diseno-de-F-001-S2-de-FABLE.md` |
| **F-007c** · que un `.ko` real CARGUE | **NO MEDIDO** | no existe todavía |

**Instrumentos:** los **15** scripts de Python que produjeron todo esto están en `tools/` **de `main`**. **Tres ya fueron auditados** (§2.3); doce no.

**Workflows:** los **15** que corrieron las mediciones están en `docs/campo/workflows-de-las-ramas/`, con extensión `.txt` a propósito: como evidencia hay que poder leerlos, no dispararlos.

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
evidencia, y por eso un auditor externo propuso correr un falsador (su F-004e:
"fragmento con POSIX_MQUEUE + IPC_NS y sin SYSVIPC") que **ya es este
fragmento y ya dio verde**. Verbatim de `mediciones/f-004d-61/v3-ocho.json`:

```
CONFIG_DEVTMPFS     y    CONFIG_DEVTMPFS_MOUNT  y    CONFIG_FHANDLE     y
CONFIG_POSIX_MQUEUE y    CONFIG_TMPFS_XATTR     y    CONFIG_AUTOFS_FS   y
CONFIG_PID_NS       y    CONFIG_IPC_NS          y

CONTROL | CONFIG_SYSVIPC     NO esta en =y (correcto)
CONTROL | CONFIG_CGROUP_PIDS NO esta en =y (correcto)
```

**FABLE retiró su F-004e** al leer esta sección: *"Tenés razón: `POSIX_MQUEUE` + `IPC_NS` sin `SYSVIPC` es exactamente el fragmento de OCHO, y ya dio verde."*

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

El falsador declarado **antes** de correr decía: *"si vuelve a dar 0,0 s, el arreglo no se aplicó y no hay que interpretar nada más"*. **Dio 0,02 s.** Es **una carrera ganada, no cerrada**.

### 2.2 · Un defecto de MI instrumento, encontrado al consolidar

El `VEREDICTO.txt` imprime `sha256 c91ed3a1963a261b290c624d251f081b`: **32 caracteres hex**, o sea el largo de un **md5**. Un sha256 tiene 64. El valor real es `c91ed3a1963a261b290c624d251f081b`**`7ecd698cb06013d5012af8ae69ee1e32`**. **El instrumento trunca el hash y lo rotula `sha256`.** A corregir en `tools/f004d61_stg.py`. **NO corregido todavía.**

### 2.3 · La auditoría de los INSTRUMENTOS (FABLE 5.1) · tres defectos confirmados

El §5 de la v3 declaraba: *"nadie verificó que los instrumentos midan lo que sus nombres dicen medir, y esa es la auditoría más cara y sigue sin hacerse"*. FABLE la empezó sobre tres archivos. **Los tres hallazgos están confirmados midiendo**, y el detalle completo con la evidencia cruda está en el ADR-008.

**H-1 · `llego_a_init: false` no es una medición.** Dos capas de defecto:

```
comando registrado:  ... -kernel /tmp/f001s1/Image -append '...'  2>&1 | head -200
lineas con timestamp de kernel en el archivo guardado:  200   <-- el head corto
ultimo timestamp:  [    0.458069]  watchdog: Hard watchdog permanently disabled
lineas con 'init process' / 'unpack rootfs' / 'VFS: Unable to mount':  0
```

Y el código, `tools/f001s1_arnes.py` línea 163:

```python
"llego_a_init": ("No working init found" in todo or "Kernel panic" in todo
                 or "Failed to execute" in todo),
```

**El campo se pone en `True` cuando ve un mensaje de FALLO de init.** O sea: el nombre es la negación de lo que calcula, un pánico daría `llego_a_init: true`, y encima opera sobre texto truncado. El `false` significa **"no vi un error de init en los primeros 0,458 s"**, no *"no llegó a init"*. **Estado correcto: NO MEDIDO.** El veredicto "arnés verde" sobrevive intacto (banner + control discriminante).

**H-2 · El kernel F-004d@6.1 no existe como artefacto arrancable.** `tools/f004d61_build.py` línea 270 compila `Image modules`, y la línea 311 empaqueta:

```python
tar -c --zstd -f <tarball> vmlinux $(find . -name '*.ko' | head -400)
```

**`arch/arm64/boot/Image` no está en el tar.** Hay dos salidas: recuperarlo con `llvm-objcopy -O binary -R .note -R .note.gnu.build-id -R .comment -S vmlinux Image` (los `OBJCOPYFLAGS_Image` de arm64), o corregir el instrumento y rebuildear. Se hacen **las dos**, y el cruce `sha256(objcopy(vmlinux)) == sha256(Image)` es un KAT gratis.

*Refutación parcial:* el `.config` **ya se commitea** (línea 303 → `mediciones/f-004d-61/v3-config-ocho.txt`, 205.550 B). Y el `head -400` **no cortó nada en esta corrida**: el veredicto registra `modulos 60` en los dos brazos. Es un riesgo latente, no un defecto materializado.

**H-3 · El instrumento de `main` no es el que produjo la evidencia.** `QEMU_BASE` (línea 38) lleva `-nic none`; el comando registrado en `f001s1-aarch64-boot.txt` **no** lo lleva, y la línea 174 del log muestra `pci 0000:00:01.0: [1af4:1000]`. Uno de los dos se editó después del otro. **R-15: el índice debe apuntar al SHA del instrumento que corrió.**

**Consecuencia medida de H-3, y decide el diseño de S2.** Sobre `v3-config-ocho.txt`:

```
1898:# CONFIG_VIRTIO_BLK is not set
5485:# CONFIG_VIRTIO_PCI is not set
5490:# CONFIG_VIRTIO_MMIO is not set
2140:# CONFIG_VIRTIO_NET is not set
2900:# CONFIG_VIRTIO_CONSOLE is not set
```

FABLE predijo *"vacío o `=m`"*. Salió más fuerte: **explícitamente `is not set`**, ni siquiera módulo (control positivo del grep: el archivo usa 3.832 veces la forma `is not set`, así que la ausencia es ausencia real). **`virtio-blk`, `virtiofs` y `9p` no son opciones sin tocar el fragmento medido: el initramfs es la única vía KMI-neutral.** `CONFIG_VIRTIO_FS=y` está, pero su transporte no.

**Precondición de S2, corrida gratis sobre el `.config` ya commiteado:** los 16 símbolos que systemd exige están **todos en `=y`** (`BLK_DEV_INITRD`, `RD_GZIP`, `TMPFS`, `DEVTMPFS`, `DEVTMPFS_MOUNT`, `CGROUPS`, `UNIX`, `INOTIFY_USER`, `SIGNALFD`, `TIMERFD`, `EPOLL`, `FHANDLE`, `AUTOFS_FS`, `POSIX_MQUEUE`, `PID_NS`, `IPC_NS`). **16/16.**

---

## 3 · Archivos que hoy mienten

**Corregidos el 2026-09-08:** `CONTEXTO-SIAO.md` (las dos afirmaciones falsas del §3), `README.md` ("nada corrió en ninguna máquina" y la promesa del banco) y **la fila de F-001-S1 de este mapa** (decía "VERDE, arrancó" sin el caveat del truncamiento).

**Siguen abiertos:**

| Archivo | Dice | Es |
|---|---|---|
| `mediciones/f-001-s1/f001s1-aarch64.json` y `-x86_64.json` | `"llego_a_init": false` | **NO MEDIDO**. Se dejan **intactos** porque son la salida cruda del instrumento (W-01); la corrección va al lado, en `CORRECCION-H1-*.md` |
| `tools/f001s1_arnes.py` | el campo `llego_a_init` y el `head -200` | a corregir **junto con** `f001s2_arnes.py`, no antes: ningún script se commitea sin ejecutarlo y este necesita QEMU + el GKI |
| `tools/f004d61_build.py` | empaqueta el kernel | no empaqueta `Image` (§2.3 H-2) |
| `tools/f004d61_stg.py` | rotula `sha256` | es un md5 (§2.2) |
| `mediciones/INDICE.md` | **dos** filas para F-004d@6.1 | la vieja no se borró. Un gate que se contradice no gatea |
| `ADR-001` §7 Fase 1 | pide *"(16K aligned) sobre GKI recompilado"* | FALSADOR-001 lo mató: los 146 ELF ya vienen con `p_align 65536` |
| `docs/auditorias/` y `docs/audits/` | dos carpetas para lo mismo | sin unificar |

---

## 4 · Tres advertencias con su error ya cometido

1. **Listar un directorio devuelve nombres y tamaños, no contenido.** Un `ls` de `mediciones/f-004d-61/` muestra 46 archivos y no dice qué dice ninguno. *(Costado: un auditor concluyó `NO MEDIDO` sobre un verde.)*
2. **Citar un subconjunto de campos es recorte de evidencia.** Se citaron seis de los ocho campos de `v3-ocho.json`, omitiendo justo los dos decisivos. *(Costado: el `Error 126` quedó leído como resuelto.)*
3. **Un campo con nombre afirmativo puede estar calculando su negación, sobre datos truncados.** *(Costado: `llego_a_init: false` viajó a un informe técnico, a un briefing y a un pedido formal antes de que alguien abriera la línea 163.)*

Son el mismo defecto con distinto radio: **no leer el archivo, leerlo y recortarlo, y leer el nombre en vez del cuerpo.**

---

## 5 · Mantenimiento

Se actualiza **en el mismo turno** en que una medición cierra. Si su fecha de verificación es anterior al último archivo de `docs/agents/respuestas/`, **está desactualizado por definición**.

**NO MEDIDO en esta versión:** el contenido de **12 de los 15 instrumentos** de `tools/` (FABLE auditó tres: `f001s1_arnes.py`, `f004d61_build.py` y el `boot.txt` que produjeron; los otros doce siguen sin que nadie verifique que miden lo que sus nombres dicen); los ADR 002, 003 y 004; si los artifacts de Actions con el `vmlinux` del brazo `ocho` siguen vivos (retención por defecto 90 días, **sin verificar**); y si los 8 `.stg` referenciados en el manifiesto siguen existiendo dentro de un mes.
