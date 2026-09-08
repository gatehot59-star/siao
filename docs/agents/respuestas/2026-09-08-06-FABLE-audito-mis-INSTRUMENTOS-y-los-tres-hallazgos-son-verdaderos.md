# FABLE auditó mis INSTRUMENTOS y los tres hallazgos son verdaderos: `llego_a_init` calcula la NEGACIÓN de su nombre, el kernel candidato no existe como `Image`, y el arnés de `main` no es el que corrió

**Fecha (UTC):** 2026-09-08 · **main:** `f213372`

## 1 · Pedido

FABLE devolvió el diseño de F-001-S2, y antes del diseño escribió "lo que me pediste que escriba primero": tres cosas que las piezas no dicen como el pedido dice. Había que verificarlas antes de aceptar nada.

## 2 · Herramientas y máquina declaradas

- `brain-env` (gateway `build/run`): lectura del worktree, `grep`/`wc`/`sed -n` sobre la evidencia y los instrumentos. **Se cayó dos veces** (ver §4).
- **API de GitHub** (`get_file_contents`, `push_files`, `get_commit`) como segunda vía de lectura y escritura.
- Escrituras: dos commits a `main`. **Cero runs de Actions**, cero runtime ajeno.

## 3 · Qué se midió

| Hallazgo de FABLE | Instrumento | Resultado |
|---|---|---|
| H-1 · `llego_a_init` es un recorte | `grep -cE` de timestamps + `sed -n '140,180p'` del arnés | **CONFIRMADO y peor**: 200 líneas exactas, corte a t=0,458 s, y el código pone el campo en `True` al ver un **error** de init |
| H-2 · el build tira `Image` | `grep -n` de `tools/f004d61_build.py` | **CONFIRMADO**: línea 311 empaqueta `vmlinux` + `.ko`, sin `Image` |
| H-3 · el arnés de `main` ≠ el que corrió | `grep` de `QEMU_BASE` vs el comando registrado vs el log | **CONFIRMADO**: `-nic none` en el instrumento, ausente en el comando, NIC `[1af4:1000]` en la línea 174 |
| su precondición 1 (esperaba 16) | `grep -cE` sobre `v3-config-ocho.txt` | **16/16 en `=y`** |
| su precondición 2 (predijo "vacío o `=m`") | `grep` de VIRTIO | **`is not set`**: más fuerte que su predicción |
| su candidata `BINFMT_MISC` | `grep` | **REFUTADA**: `CONFIG_BINFMT_MISC=y` |
| su remedio "empaquetar `.config`" | `grep` línea 303 + `ls` | **REFUTADO parcial**: ya se commitea, 205.550 B |
| su `head -400` → "puede dejar módulos afuera" | veredicto | **MATIZADO**: `modulos 60`, no cortó |

## 4 · Evidencia cruda verbatim

### H-1, las dos capas

```plain
$ head -2 mediciones/f-001-s1/f001s1-aarch64-boot.txt
### comando
timeout 240 qemu-system-aarch64 -machine virt -cpu cortex-a57 -smp 2 -m 2048 -nographic -no-reboot -kernel /tmp/f001s1/Image -append 'console=ttyAMA0 panic=1 earlycon' 2>&1 | head -200

$ grep -cE '^\[ *[0-9]+\.[0-9]+\]' ...boot.txt      -> 200
$ grep -oE '^\[ *[0-9]+\.[0-9]+\]' ...boot.txt | tail -1  -> [    0.458069]
$ grep -v '^$' ...boot.txt | tail -1
[    0.458069][    T7] watchdog: Hard watchdog permanently disabled

$ grep -n -i 'init process|systemd|VFS:|unpack rootfs' ...boot.txt
137:[    0.228240][    T1] VFS: Disk quotas dquot_6.6.0
138:[    0.228627][    T1] VFS: Dquot-cache hash table entries: 512 (order 0, 4096 bytes)
```

```python
# tools/f001s1_arnes.py, lineas 158-165 verbatim
    hitos = {"control_discrimina": control_discrimina,
             "banner_linux": bool(m),
             "version_leida": m.group(1) if m else None,
             "memoria_ok": "Memory:" in todo,
             "llego_a_init": ("No working init found" in todo or "Kernel panic" in todo
                              or "Failed to execute" in todo),
             "bytes_de_salida": len(todo)}
```

### H-2

```python
# tools/f004d61_build.py
270:    rc, _, _, _ = sh("%s -j$(nproc) Image modules" % mk, 20000, guardar=logb)
311:    rc_t, _, _, _ = sh("cd %s && tar -c --zstd -f %s vmlinux "
312:                       "$(find . -name '*.ko' | head -400)" % (obj, tarball), 3600)
303:        open(os.path.join(OUT, "v3-config-%s.txt" % brazo), "w").write(cfg)   <-- el .config SI se guarda
```

### H-3

```plain
# tools/f001s1_arnes.py
38:QEMU_BASE = ("qemu-system-aarch64 -machine virt -cpu cortex-a57 -smp 2 -m 2048 "
39:             "-nographic -no-reboot -nic none")
154:           "2>&1 | head -200" % (QEMU_BASE, k))      <-- el head sigue VIVO en main

# el comando que produjo la evidencia: sin -nic none
# y el log, linea 174:
[    0.335802][    T1] pci 0000:00:01.0: [1af4:1000] type 00 class 0x020000
```

### Las precondiciones, corridas gratis

```plain
--- 16 simbolos de systemd sobre v3-config-ocho.txt: CUENTA 16 ---
CONFIG_AUTOFS_FS=y CONFIG_BLK_DEV_INITRD=y CONFIG_CGROUPS=y CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y CONFIG_EPOLL=y CONFIG_FHANDLE=y CONFIG_INOTIFY_USER=y
CONFIG_IPC_NS=y CONFIG_PID_NS=y CONFIG_POSIX_MQUEUE=y CONFIG_RD_GZIP=y
CONFIG_SIGNALFD=y CONFIG_TIMERFD=y CONFIG_TMPFS=y CONFIG_UNIX=y

--- virtio ---
1898:# CONFIG_VIRTIO_BLK is not set
5485:# CONFIG_VIRTIO_PCI is not set
5490:# CONFIG_VIRTIO_MMIO is not set
2140:# CONFIG_VIRTIO_NET is not set
2900:# CONFIG_VIRTIO_CONSOLE is not set
CONFIG_VIRTIO=y CONFIG_VIRTIO_ANCHOR=y CONFIG_VIRTIO_FS=y CONFIG_VIRTIO_MENU=y CONFIG_VIRTIO_VSOCKETS_COMMON=y

--- control positivo del grep: 3832 lineas 'is not set' ---
--- BINFMT_MISC ---
920:CONFIG_BINFMT_MISC=y
```

### El gateway, dos veces

Dos `Request timed out` consecutivos al intentar editar el mapa (payload con acentos y comillas), después de un Cloudflare 1033 en el turno anterior. `git status` limpio confirmó que **no aplicó nada** (no quedó un archivo a medio editar). La edición se hizo por la API de GitHub.

## 5 · Veredicto (conclusión, no medición)

**FABLE ganó los tres.** Y el más caro es H-1, porque `llego_a_init: false` viajó a un informe técnico, al briefing y al pedido formal **antes de que alguien abriera la línea 163**. El defecto no era el recorte: era leer el **nombre** de un campo en vez de su cuerpo. Ese es un patrón nuevo para el mapa (§4.3 de la v4) y no estaba en mi lista.

Lo que gané yo son dos refutaciones chicas (`BINFMT_MISC=y`, el `.config` ya commiteado) y un matiz (`head -400` no cortó). Ninguna toca su diseño. **Su H-3 salió más fuerte de lo que él predijo**: virtio no está ni como módulo, así que el initramfs no es la mejor vía sino la única, y mi opción "imagen raw con virtio-blk" del pedido nunca existió.

**Y el mapa cerró su propio NO MEDIDO más caro:** decía que nadie había verificado que los instrumentos midan lo que sus nombres dicen medir. FABLE verificó tres de quince y encontró tres defectos. La tasa importa.

## 6 · Archivos generados

- `docs/agents/MAPA-DE-LA-EVIDENCIA.md` → **v4** (fila de F-001-S1 corregida, nuevo §2.3, tabla de "archivos que hoy mienten" ampliada, §4 con el tercer patrón)
- `mediciones/f-001-s1/CORRECCION-H1-el-campo-llego_a_init-nunca-midio-eso.md`
- `docs/adr/2026-09-08-08-ADR-008-resolucion-del-diseno-de-F-001-S2-de-FABLE.md`
- `docs/agents/respuestas/2026-09-08-06-FABLE-audito-mis-INSTRUMENTOS-y-los-tres-hallazgos-son-verdaderos.md` (este archivo)

## 7 · NO MEDIDO, declarado

- **F-001-S2.** Diseño aceptado y predicción registrada; cero corridas. El paso 1 (arreglar el build y rebuildear) **gasta un run y espera OK**.
- **Los artifacts del `vmlinux` del brazo `ocho`.** No verifiqué si siguen vivos.
- **Los otros 12 instrumentos de `tools/`.**
- **Los JSON de F-001-S1 quedan con el campo viejo a propósito** (W-01: son salida cruda). La corrección vive al lado, no encima.

--- METODO PROMETEO ---
Máquina: brain-env (container) para las mediciones · API de GitHub para la escritura, porque el gateway se cayó dos veces.
Artefactos: los cuatro archivos del §6 en `main`, más el Doc público de ClickUp.
